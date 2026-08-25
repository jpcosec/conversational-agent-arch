from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from kb_agent.orchestrator import Orchestrator

STORE_ROOT = PROJECT_ROOT / ".sldb_e2e_donpeppe"
USER_NL = "wa:+56924444441"
USER_TOOL = "wa:+56924444442"


def test_orchestrator_routes_turns_through_real_state_machine(tmp_path: Path) -> None:
    db_file = tmp_path / "statemachine-wiring.sqlite"
    evidence_path = PROJECT_ROOT / "runs" / "e2e" / "state-trace.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

    orch = Orchestrator(kb_root=STORE_ROOT, db_url=f"sqlite:///{db_file}")
    try:
        nl_turn = orch.handle_turn(
            external_id=USER_NL,
            message="Hola, que pizzas vegetarianas recomiendan?",
            scenario="pizzeria",
        )
        tool_turn = orch.handle_turn(
            external_id=USER_TOOL,
            message="reservar mesa para 4 el viernes a las 20:00 a nombre de Rojas",
            scenario="pizzeria",
        )

        payload = {
            "db_file": str(db_file),
            "nl_turn": {
                "kind": nl_turn["kind"],
                "reply": nl_turn["reply"],
                "state_trace": nl_turn["state_trace"],
            },
            "tool_turn": {
                "kind": tool_turn["kind"],
                "reply": tool_turn["reply"],
                "system_turn": tool_turn["system_turn"],
                "state_trace": tool_turn["state_trace"],
            },
        }
        evidence_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        assert nl_turn["kind"] == "nl"
        assert nl_turn["state_trace"] == ["idle", "evaluating_context", "drafting_response", "idle"]

        assert tool_turn["kind"] == "tool_call"
        assert "waiting_tool" in tool_turn["state_trace"]
        assert tool_turn["state_trace"][-1] == "idle"
        assert tool_turn["system_turn"] is not None
        assert tool_turn["system_turn"]["status"] == "ok"
        assert orch.count_reservas() == 1
    finally:
        orch.engine.dispose()
