"""Bucle de conversacion: usuario simulado <-> orquestador, con transcripcion auditable."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kb_agent.orchestrator import Orchestrator

from .simulated_user import SimulatedUser


@dataclass
class Transcript:
    scenario_id: str
    external_id: str
    turns: list[dict[str, Any]] = field(default_factory=list)
    ended_by: str = ""          # "user_done" | "max_turns"
    end_reason: str = ""

    @property
    def kinds(self) -> list[str]:
        return [t["kind"] for t in self.turns]

    @property
    def assistant_text(self) -> str:
        return "\n".join(t["assistant"] for t in self.turns)

    def tool_calls(self) -> list[dict[str, Any]]:
        return [t["system_turn"] for t in self.turns if t.get("system_turn")]

    def for_llm(self) -> list[dict[str, Any]]:
        return [{"user": t["user"], "assistant": t["assistant"], "kind": t["kind"], "system_turn": t.get("system_turn")} for t in self.turns]

    def pretty(self) -> str:
        out = [f"--- {self.scenario_id} ({self.ended_by}: {self.end_reason}) ---"]
        for i, t in enumerate(self.turns, 1):
            out.append(f"[{i}] USER > {t['user']}")
            extra = f" tool={t['system_turn']['tool']}/{t['system_turn']['status']}" if t.get("system_turn") else ""
            out.append(f"[{i}] BOT ({t['kind']}{extra}) > {t['assistant']}")
        return "\n".join(out)

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "scenario_id": self.scenario_id,
            "external_id": self.external_id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "ended_by": self.ended_by,
            "end_reason": self.end_reason,
            "turns": self.turns,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return path


def run_conversation(
    orchestrator: Orchestrator,
    user: SimulatedUser,
    *,
    scenario_id: str,
    external_id: str,
    max_turns: int = 6,
    scenario: str | None = None,
) -> Transcript:
    transcript = Transcript(scenario_id=scenario_id, external_id=external_id)
    for _ in range(max_turns):
        move = user.next_move(transcript.for_llm())
        if move.done:
            transcript.ended_by, transcript.end_reason = "user_done", move.reason
            return transcript
        raw = orchestrator.handle_turn(external_id=external_id, message=move.message, scenario=scenario)
        transcript.turns.append({
            "user": move.message,
            "user_reason": move.reason,
            "assistant": raw["reply_text"],
            "kind": raw["kind"],
            "system_turn": raw.get("system_turn"),
            "traits_after": raw.get("traits_after", []),
            "used_traits_in_context": raw.get("used_traits_in_context", []),
            "flow_node": raw.get("flow_node"),
            "state_trace": raw.get("state_trace", []),
        })
    transcript.ended_by, transcript.end_reason = "max_turns", f"se alcanzo el maximo de {max_turns} turnos"
    return transcript
