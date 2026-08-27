"""Agrupamiento de conversaciones reales en ``/api/profiles`` (Problema 1).

Antes ``/api/profiles`` armaba una entrada por FILA de ``ChatHistory`` (un
mensaje, no un turno): un usuario con una sola charla de N turnos aparecia
con 2N "conversaciones" en la UI, la mitad vacias (las del lado assistant,
sin summary) -- ver ``frontends/chat/app.py`` antes de esta fase.

Esto verifica el contrato correcto: una CONVERSACION real es una entrada por
``session_id`` (migracion ``8df38d93ccd7``), con ``n_turns`` contando turnos
reales (1 fila 'user' + 1 fila 'assistant' cada uno), no mensajes sueltos.
Tambien cubre las filas legadas sin ``session_id`` (el orquestador en
produccion aun no lo setea -- gap documentado, fuera de este alcance): deben
agruparse de forma honesta (por dia), nunca inventarse una sesion por fila.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from frontends.chat.app import create_app
from kb_agent.models_sql.identity import Base as IdentityBase, Users
from kb_agent.models_sql.session import ChatHistory
from kb_agent.project_config import load_project_config
from kb_agent.tools import load_tool_handlers
from tests.support.fakes import offline_orchestrator


@pytest.fixture()
def client(tmp_path: Path, donpeppe_kb: Path) -> TestClient:
    db = tmp_path / "chat.sqlite"
    cfg = load_project_config(mode="test", env={"CHAT_DB": str(db), "PROFILING_DB": str(db)})
    orch = offline_orchestrator(cfg.kb_root, cfg.chat_db_url, tool_handlers=load_tool_handlers(cfg.tool_handlers))
    with TestClient(create_app(cfg, orch)) as c:
        yield c
    orch.close()


def _seed_rows(profiling_db, external_id: str, sessions: list[tuple[str | None, list[tuple[str, str]]]]) -> None:
    """Inserta ChatHistory directamente (sin pasar por el orquestador) para
    simular tanto sesiones reales (``session_id`` set) como filas legadas
    (``session_id`` None) -- ``sessions``: lista de (session_id_o_None, [(role, content), ...]).
    """
    engine = create_engine(f"sqlite:///{profiling_db}", future=True)
    IdentityBase.metadata.create_all(engine)
    ChatHistory.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    now = datetime.now(timezone.utc)
    with Session() as s:
        user = s.query(Users).filter(Users.external_id == external_id).first()
        if user is None:
            user = Users(external_id=external_id, channel="whatsapp")
            s.add(user)
            s.flush()
        t = now
        for session_id, rows in sessions:
            for role, content in rows:
                s.add(ChatHistory(user_id=user.id, session_id=session_id, role=role, content=content, created_at=t))
                t += timedelta(minutes=1)
            t += timedelta(hours=1)
        s.commit()
    engine.dispose()


def test_one_session_with_n_turns_is_one_conversation(client: TestClient) -> None:
    """El caso central del Problema 1: una sesion de 3 turnos (6 filas)
    debe aparecer como UNA conversacion con n_turns == 3, no 6.
    """
    cfg = client.app.state.cfg
    external_id = "wa-grouping-test"
    turns = [
        ("user", "hola"), ("assistant", "hola, bienvenido"),
        ("user", "que pizzas tienen?"), ("assistant", "margherita y napolitana"),
        ("user", "cual me recomiendas?"), ("assistant", "la margherita"),
    ]
    _seed_rows(cfg.profiling_db, external_id, [("sess-abc123", turns)])

    profiles = client.get("/api/profiles").json()
    users = {u["external_id"]: u for u in profiles["users"]}
    user = users[external_id]

    assert len(user["conversations"]) == 1, f"esperaba 1 conversacion, salieron {len(user['conversations'])}: {user['conversations']}"
    conv = user["conversations"][0]
    assert conv["session_id"] == "sess-abc123"
    assert conv["n_turns"] == 3, f"n_turns deberia ser 3 (turnos reales), salio {conv['n_turns']}"
    assert conv["n_messages"] == 6
    assert conv["summary"] == "hola"
    assert user["total_turns"] == 3


def test_multiple_sessions_are_multiple_conversations(client: TestClient) -> None:
    """Dos sesiones distintas del mismo usuario -> dos conversaciones, cada
    una con su propio n_turns (no se mezclan).
    """
    cfg = client.app.state.cfg
    external_id = "wa-multi-session"
    _seed_rows(cfg.profiling_db, external_id, [
        ("sess-1", [("user", "hola"), ("assistant", "hola")]),
        ("sess-2", [("user", "a"), ("assistant", "b"), ("user", "c"), ("assistant", "d")]),
    ])

    profiles = client.get("/api/profiles").json()
    users = {u["external_id"]: u for u in profiles["users"]}
    user = users[external_id]

    by_session = {c["session_id"]: c for c in user["conversations"]}
    assert set(by_session) == {"sess-1", "sess-2"}
    assert by_session["sess-1"]["n_turns"] == 1
    assert by_session["sess-2"]["n_turns"] == 2
    assert user["total_turns"] == 3


def test_legacy_rows_without_session_id_group_honestly_not_per_row(client: TestClient) -> None:
    """Filas legadas (session_id NULL) no se inventan como N conversaciones
    sinteticas: se agrupan por dia, con session_id explicitamente None.
    """
    cfg = client.app.state.cfg
    external_id = "wa-legacy-test"
    turns = [("user", "hola"), ("assistant", "hola"), ("user", "gracias"), ("assistant", "de nada")]
    _seed_rows(cfg.profiling_db, external_id, [(None, turns)])

    profiles = client.get("/api/profiles").json()
    users = {u["external_id"]: u for u in profiles["users"]}
    user = users[external_id]

    assert len(user["conversations"]) == 1, f"4 filas legadas del mismo dia deberian agruparse en 1, salieron {len(user['conversations'])}"
    conv = user["conversations"][0]
    assert conv["session_id"] is None
    assert conv["legacy_group"] is not None
    assert conv["n_turns"] == 2
