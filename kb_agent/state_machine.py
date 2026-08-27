from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


TurnClosedPublisher = Callable[[int | None, str], Any]


DEBOUNCE_MS = 1000
TOOL_TIMEOUT_MS = int(os.getenv("TOOL_TIMEOUT_MS", "15000"))


class RouterNode(str, Enum):
    IDLE = "idle"
    BUFFERING = "buffering"
    EVALUATING_CONTEXT = "evaluating_context"
    DRAFTING_RESPONSE = "drafting_response"
    WAITING_TOOL = "waiting_tool"
    BREAKPOINT_MISS = "breakpoint_miss"


@dataclass
class SessionState:
    current_node: RouterNode = RouterNode.IDLE
    buffer: dict[str, list[str]] = field(default_factory=lambda: {"debounce": []})


@dataclass(frozen=True)
class CronTriggerPayload:
    scenario: str
    user_id: int


@dataclass
class RouterTurnResult:
    compiled_context: dict[str, Any]
    response: Any
    state_trace: list[RouterNode]


@dataclass
class RouterStateMachine:
    compile_context: Callable[..., dict[str, Any]]
    draft_response: Callable[[dict[str, Any]], Any]
    turn_closed_publisher: TurnClosedPublisher | None = None
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))
    current_node: RouterNode = RouterNode.IDLE
    state_trace: list[RouterNode] = field(default_factory=lambda: [RouterNode.IDLE])
    pending_events: list[dict[str, Any]] = field(default_factory=list)
    debounce_enabled: bool = False
    #: Timeout de una tool en ms. Default = ``TOOL_TIMEOUT_MS`` (env/legacy),
    #: pero el runtime lo setea desde ``ProjectConfig.tuning.tool_timeout_ms``.
    tool_timeout_ms: int = TOOL_TIMEOUT_MS
    now_ms: Callable[[], int] = field(default_factory=lambda: (lambda: 0))
    session_state: SessionState = field(default_factory=SessionState)
    _debounce_deadline_ms: int | None = field(default=None, init=False, repr=False)
    _debounce_user_id: int | None = field(default=None, init=False, repr=False)
    _debounce_scenario: str | None = field(default=None, init=False, repr=False)
    _tool_deadline_ms: int | None = field(default=None, init=False, repr=False)
    _paused_compiled_context: dict[str, Any] | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.session_state.current_node = self.current_node
        self.session_state.buffer.setdefault("debounce", [])
        self.session_state.buffer.setdefault("tool_wait", [])

    def handle_user_message(self, message: str, *, user_id: int | None = None, scenario: str | None = None) -> RouterTurnResult | None:
        if self.current_node is RouterNode.WAITING_TOOL:
            self.session_state.buffer["tool_wait"].append(message)
            return None

        if not self.debounce_enabled:
            return self._run_turn(
                question=message,
                user_id=user_id,
                scenario=scenario,
                trigger="user",
            )

        if self.current_node is RouterNode.IDLE:
            self._debounce_user_id = user_id
            self._debounce_scenario = scenario
            self.session_state.buffer["debounce"] = [message]
            self._transition_to(RouterNode.BUFFERING)
            self._arm_debounce_timer()
            return None

        if self.current_node is RouterNode.BUFFERING:
            self._debounce_user_id = user_id
            self._debounce_scenario = scenario
            self.session_state.buffer["debounce"].append(message)
            self._transition_to(RouterNode.BUFFERING)
            self._arm_debounce_timer()
            return None

        raise RuntimeError(f"router is busy in node {self.current_node.value}")

    def handle_cron_trigger(self, payload: CronTriggerPayload) -> RouterTurnResult | None:
        if self.current_node is not RouterNode.IDLE:
            self.logger.info(
                "Dropping CRON trigger because router is not idle",
                extra={"current_node": self.current_node.value, "scenario": payload.scenario, "user_id": payload.user_id},
            )
            return None

        return self._run_turn(
            question="",
            user_id=payload.user_id,
            scenario=payload.scenario,
            trigger="cron",
        )

    def process_timeouts(self) -> RouterTurnResult | None:
        if self.current_node is RouterNode.WAITING_TOOL:
            if self._tool_deadline_ms is None or self.now_ms() < self._tool_deadline_ms:
                return None

            timeout_payload = {
                "error": "tool_timeout",
                "message": f"Tool call timed out after {self.tool_timeout_ms}ms",
            }
            return self._resume_from_waiting_tool(timeout_payload)

        if self.current_node is not RouterNode.BUFFERING or self._debounce_deadline_ms is None:
            return None

        if self.now_ms() < self._debounce_deadline_ms:
            return None

        question = " ".join(self.session_state.buffer["debounce"])
        self.session_state.buffer["debounce"] = []
        self._debounce_deadline_ms = None
        result = self._compile_and_draft(
            question=question,
            user_id=self._debounce_user_id,
            scenario=self._debounce_scenario,
            trigger="user",
        )
        self._debounce_user_id = None
        self._debounce_scenario = None
        return result

    def _run_turn(
        self,
        *,
        question: str,
        user_id: int | None,
        scenario: str | None,
        trigger: str,
    ) -> RouterTurnResult:
        if self.current_node is not RouterNode.IDLE:
            raise RuntimeError(f"router is busy in node {self.current_node.value}")

        return self._compile_and_draft(
            question=question,
            user_id=user_id,
            scenario=scenario,
            trigger=trigger,
        )

    def handle_tool_result(self, payload: Any) -> RouterTurnResult:
        if self.current_node is not RouterNode.WAITING_TOOL:
            raise RuntimeError(f"router is not waiting for a tool in node {self.current_node.value}")

        return self._resume_from_waiting_tool(payload)

    def _compile_and_draft(
        self,
        *,
        question: str,
        user_id: int | None,
        scenario: str | None,
        trigger: str,
    ) -> RouterTurnResult:
        self._transition_to(RouterNode.EVALUATING_CONTEXT)
        compiled_context = self.compile_context(
            question=question,
            user_id=user_id,
            scenario=scenario,
            trigger=trigger,
        )

        if compiled_context.get("is_empty"):
            self._transition_to(RouterNode.BREAKPOINT_MISS)

        self._transition_to(RouterNode.DRAFTING_RESPONSE)
        response = self.draft_response(compiled_context)
        if self._is_function_call(response):
            self._paused_compiled_context = compiled_context
            self._transition_to(RouterNode.WAITING_TOOL)
            self._arm_tool_timer()
        else:
            self._publish_turn_closed(user_id=user_id, question=question)
            self._transition_to(RouterNode.IDLE)

        return RouterTurnResult(
            compiled_context=compiled_context,
            response=response,
            state_trace=self.state_trace[-4:] if len(self.state_trace) >= 4 else self.state_trace[:],
        )

    def _resume_from_waiting_tool(self, payload: Any) -> RouterTurnResult:
        paused_context = self._paused_compiled_context or {}
        resumed_context = dict(paused_context)
        system_turn = {
            "role": "system",
            "content": self._serialize_tool_payload(payload),
        }
        history = list(resumed_context.get("history", []))
        history.append(system_turn)
        resumed_context["history"] = history
        resumed_context["system_turn"] = system_turn

        self._tool_deadline_ms = None
        self._paused_compiled_context = resumed_context
        self._transition_to(RouterNode.DRAFTING_RESPONSE)
        response = self.draft_response(resumed_context)
        self._paused_compiled_context = None
        self._publish_turn_closed(
            user_id=self._coerce_user_id(resumed_context.get("user_id")),
            question=str(resumed_context.get("question") or ""),
        )
        self._transition_to(RouterNode.IDLE)
        return RouterTurnResult(
            compiled_context=resumed_context,
            response=response,
            state_trace=self.state_trace[-3:],
        )

    def _arm_debounce_timer(self) -> None:
        self._debounce_deadline_ms = self.now_ms() + DEBOUNCE_MS

    def _arm_tool_timer(self) -> None:
        self._tool_deadline_ms = self.now_ms() + self.tool_timeout_ms

    def _is_function_call(self, response: Any) -> bool:
        return isinstance(response, dict) and isinstance(response.get("function_call"), dict)

    def _serialize_tool_payload(self, payload: Any) -> str:
        if isinstance(payload, str):
            return payload
        return json.dumps(payload, sort_keys=True)

    def _publish_turn_closed(self, *, user_id: int | None, question: str) -> None:
        if self.turn_closed_publisher is None or not question:
            return
        self.turn_closed_publisher(user_id, question)

    def _coerce_user_id(self, value: Any) -> int | None:
        return value if isinstance(value, int) else None

    def _transition_to(self, node: RouterNode) -> None:
        self.current_node = node
        self.session_state.current_node = node
        self.state_trace.append(node)
