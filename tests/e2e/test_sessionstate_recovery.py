from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from kb_agent.agent import CANONICAL_FALLBACK_RESPONSE
from kb_agent.models_sql.session import SessionState
from kb_agent.orchestrator import Orchestrator

STORE_ROOT = PROJECT_ROOT / ".sldb_e2e_donpeppe"
USER = "wa:+56923333333"


def _active_domain(orch: Orchestrator, external_id: str) -> tuple[int, str | None]:
    session = orch.SessionLocal()
    try:
        user = orch.ensure_user(session, external_id)
        state = session.scalar(select(SessionState).where(SessionState.user_id == user.id))
        assert state is not None
        return user.id, state.active_domain
    finally:
        session.close()


def test_sessionstate_recovery_real_sqlite_file(tmp_path: Path) -> None:
    db_file = tmp_path / "sessionstate-recovery.sqlite"
    evidence_path = PROJECT_ROOT / "runs" / "e2e" / "sessionstate-recovery.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

    orch_a = Orchestrator(kb_root=STORE_ROOT, db_url=f"sqlite:///{db_file}")
    turn_1 = orch_a.handle_turn(
        external_id=USER,
        message="Hola, que pizzas vegetarianas recomiendan?",
        scenario="pizzeria",
    )
    user_id, active_domain_before_restart = _active_domain(orch_a, USER)

    assert turn_1["scenario_effective"] == "pizzeria"
    assert turn_1["scenario_source"] == "argument"
    assert active_domain_before_restart == "pizzeria"

    orch_a.engine.dispose()
    del orch_a

    orch_b = Orchestrator(kb_root=STORE_ROOT, db_url=f"sqlite:///{db_file}")
    turn_2 = orch_b.handle_turn(
        external_id=USER,
        message="Y para hoy, cual me recomiendan?",
    )
    _, active_domain_after_restart = _active_domain(orch_b, USER)

    evidence_path.write_text(
        json.dumps(
            {
                "db_file": str(db_file),
                "user_id": user_id,
                "before_restart": {
                    "active_domain": active_domain_before_restart,
                    "turn": {
                        "scenario_effective": turn_1["scenario_effective"],
                        "scenario_source": turn_1["scenario_source"],
                        "kind": turn_1["kind"],
                    },
                },
                "after_restart": {
                    "active_domain": active_domain_after_restart,
                    "turn": {
                        "scenario_effective": turn_2["scenario_effective"],
                        "scenario_source": turn_2["scenario_source"],
                        "kind": turn_2["kind"],
                        "reply": turn_2["reply"],
                    },
                },
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    assert turn_2["scenario_effective"] == "pizzeria"
    assert turn_2["scenario_source"] == "session_state"
    assert active_domain_after_restart == "pizzeria"
    assert turn_2["reply"] != CANONICAL_FALLBACK_RESPONSE
    assert turn_2["kind"] != "fallback"

    reply_text = json.dumps(turn_2["reply"], ensure_ascii=False) if isinstance(turn_2["reply"], dict) else str(turn_2["reply"])
    assert any(token in reply_text.lower() for token in ("pizza", "pizzas", "don peppe", "vegetar")), reply_text

    orch_b.engine.dispose()
