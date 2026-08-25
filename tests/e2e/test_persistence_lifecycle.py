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

    # Turno 1: el cliente revela un trait -> el PERFILADOR real (Gemini) debe
    # aprenderlo y persistirlo. NADA de inserciones a mano.
    profiling_turn = orch.handle_turn(
        external_id=USER,
        message="Hola, soy vegetariano, que me recomiendan?",
        scenario="pizzeria",
    )
    assert TRAIT_ID in profiling_turn["traits_after"], (
        "el perfilador real no aprendio el trait desde el mensaje"
    )

    # Turno 2: reserva real -> tool dispatcher persiste en SQL
    reserva_turn = orch.handle_turn(
        external_id=USER,
        message="reservar mesa para 4 el viernes a las 20:00 a nombre de Rojas",
        scenario="pizzeria",
    )
    assert reserva_turn["kind"] == "tool_call"
    assert reserva_turn["system_turn"] is not None
    assert reserva_turn["system_turn"]["status"] == "ok"
    user_id = profiling_turn["user_id"]

    before_restart = {
        "db_url": f"sqlite:///{db_file}",
        "db_file": str(db_file),
        "user_id": user_id,
        "count_reservas": orch.count_reservas(),
        "traits": _sorted_traits(orch, user_id),
    }

    orch.engine.dispose()
    del orch

    orch_restarted = Orchestrator(kb_root=STORE_ROOT, db_url=f"sqlite:///{db_file}")
    after_restart = {
        "db_url": f"sqlite:///{db_file}",
        "db_file": str(db_file),
        "count_reservas": orch_restarted.count_reservas(),
        "traits": _sorted_traits(orch_restarted, user_id),
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
