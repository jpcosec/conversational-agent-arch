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

from kb_agent.models_sql.identity import UserTraits
from kb_agent.orchestrator import Orchestrator

STORE_ROOT = PROJECT_ROOT / ".sldb_e2e_donpeppe"
USER = "wa:+56922222222"
TRAIT_ID = "trait-vegetariano"


def _sorted_traits(orch: Orchestrator, user_id: int) -> list[str]:
    session = orch.SessionLocal()
    try:
        return list(session.scalars(select(UserTraits.trait_id).where(UserTraits.user_id == user_id).order_by(UserTraits.trait_id)))
    finally:
        session.close()


def test_persistence_lifecycle_real_sqlite_file(tmp_path: Path) -> None:
    db_file = tmp_path / "orchestrator-persistence.sqlite"
    evidence_path = PROJECT_ROOT / "runs" / "e2e" / "persistence-check.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

    orch = Orchestrator(kb_root=STORE_ROOT, db_url=f"sqlite:///{db_file}")
    first_turn = orch.handle_turn(
        external_id=USER,
        message="reservar mesa para 4 el viernes a las 20:00 a nombre de Rojas",
        scenario="pizzeria",
    )

    assert first_turn["kind"] == "tool_call"
    assert first_turn["system_turn"] is not None
    assert first_turn["system_turn"]["status"] == "ok"

    session = orch.SessionLocal()
    try:
        session.add(
            UserTraits(
                user_id=first_turn["user_id"],
                trait_id=TRAIT_ID,
                confidence=1.0,
                source="test_persistence_lifecycle",
            )
        )
        session.commit()
    finally:
        session.close()

    before_restart = {
        "db_url": f"sqlite:///{db_file}",
        "db_file": str(db_file),
        "user_id": first_turn["user_id"],
        "count_reservas": orch.count_reservas(),
        "traits": _sorted_traits(orch, first_turn["user_id"]),
    }

    orch.engine.dispose()
    del orch

    orch_restarted = Orchestrator(kb_root=STORE_ROOT, db_url=f"sqlite:///{db_file}")
    after_restart = {
        "db_url": f"sqlite:///{db_file}",
        "db_file": str(db_file),
        "count_reservas": orch_restarted.count_reservas(),
        "traits": _sorted_traits(orch_restarted, first_turn["user_id"]),
    }

    evidence_path.write_text(
        json.dumps(
            {
                "before_restart": before_restart,
                "after_restart": after_restart,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    assert before_restart["count_reservas"] == 1
    assert before_restart["traits"] == [TRAIT_ID]
    assert after_restart["count_reservas"] == 1
    assert after_restart["traits"] == [TRAIT_ID]

    orch_restarted.engine.dispose()
