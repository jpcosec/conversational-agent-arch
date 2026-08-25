from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class RouterNode(str, Enum):
    IDLE = "idle"
    BUFFERING = "buffering"
    EVALUATING_CONTEXT = "evaluating_context"
    DRAFTING_RESPONSE = "drafting_response"
    WAITING_TOOL = "waiting_tool"
    BREAKPOINT_MISS = "breakpoint_miss"


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
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))
    current_node: RouterNode = RouterNode.IDLE
    state_trace: list[RouterNode] = field(default_factory=lambda: [RouterNode.IDLE])
    pending_events: list[dict[str, Any]] = field(default_factory=list)

    def handle_user_message(self, message: str, *, user_id: int | None = None, scenario: str | None = None) -> RouterTurnResult:
        return self._run_turn(
            question=message,
            user_id=user_id,
            scenario=scenario,
            trigger="user",
        )

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
        self._transition_to(RouterNode.IDLE)

        return RouterTurnResult(
            compiled_context=compiled_context,
            response=response,
            state_trace=self.state_trace[-4:] if len(self.state_trace) >= 4 else self.state_trace[:],
        )

    def _transition_to(self, node: RouterNode) -> None:
        self.current_node = node
        self.state_trace.append(node)
