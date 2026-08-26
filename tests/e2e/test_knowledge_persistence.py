"""E2E: knowledge CLI + SQLite persistence.

Prueba que el CLI knowledge lea/escriba correctamente SQLite:
- step next: flow_node + flow_slots desde SessionState
- traits: UserTraits resueltos contra TraitAtom
- context: todo-en-uno
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from kb_agent.models_sql.identity import Base, Users, UserTraits
from kb_agent.models_sql.session import SessionState, SessionNode, ChatHistory

REPO_ROOT = Path(__file__).resolve().parents[2]
KB_ROOT = REPO_ROOT / "tests" / "knowledge_antonia"


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=30, cwd=REPO_ROOT,
    )


def _knowledge(*args: str) -> dict:
    cmd = [
        sys.executable, "-m", "knowledge_base",
        "--kb", str(KB_ROOT),
        "--pythonpath", ".",
        *args,
    ]
    r = _run(cmd)
    assert r.returncode == 0, f"FAIL: {' '.join(cmd)}\nstdout:{r.stdout}\nstderr:{r.stderr}"
    return json.loads(r.stdout)


def test_persistence_step_next_reads_session_state(tmp_path: Path) -> None:
    """knowledge step next lee flow_node y flow_slots desde SQL."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        user = Users(external_id="wa:+56900000000", channel="whatsapp")
        session.add(user)
        session.flush()
        session.add(SessionState(
            user_id=user.id,
            current_node=SessionNode.IDLE,
            flow_node="conversation:steps.onboarding",
            flow_slots={"missing_slots": ["nombre"]},
        ))
        session.commit()
    finally:
        session.close()
        engine.dispose()

    result = _knowledge("--db", db_url, "step", "next", "--user", "wa:+56900000000")
    assert result["flow_node"] == "conversation:steps.onboarding"
    assert "nombre" in result["missing_slots"]


def test_persistence_traits_resolves_from_sql(tmp_path: Path) -> None:
    """knowledge traits lee UserTraits y los resuelve contra TraitAtom."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        user = Users(external_id="wa:+56900000000", channel="whatsapp")
        session.add(user)
        session.flush()
        session.add(UserTraits(
            user_id=user.id, trait_id="trait-vegetariano",
            confidence=0.9, source="test",
        ))
        session.commit()
    finally:
        session.close()
        engine.dispose()

    # TraitAtom "trait-vegetariano" vive en KB_ROOT
    result = _knowledge("--db", db_url, "traits", "--user", "wa:+56900000000")
    assert len(result) == 1
    assert result[0]["trait_id"] == "trait-vegetariano"
    assert result[0]["confidence"] == 0.9


def test_persistence_context_aggregates_all(tmp_path: Path) -> None:
    """knowledge context devuelve step + traits + self."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        user = Users(external_id="wa:+56900000000", channel="whatsapp")
        session.add(user)
        session.flush()
        session.add(SessionState(
            user_id=user.id, current_node=SessionNode.IDLE,
            flow_node="conversation:steps.onboarding",
        ))
        session.add(UserTraits(
            user_id=user.id, trait_id="trait-vegetariano",
            confidence=0.9, source="test",
        ))
        session.commit()
    finally:
        session.close()
        engine.dispose()

    result = _knowledge("--db", db_url, "context", "--user", "wa:+56900000000")
    assert set(result.keys()) == {"step", "traits", "self"}
    assert result["step"]["flow_node"] == "conversation:steps.onboarding"
    assert len(result["traits"]) == 1
    # self no depende de SQL
    assert len(result["self"]["identity"]) >= 1
    assert len(result["self"]["style"]) >= 1
    assert len(result["self"]["boundaries"]) >= 1


def test_persistence_unknown_user_returns_empty(tmp_path: Path) -> None:
    """Usuario no existente en SQL devuelve datos vacíos, no crash."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    engine.dispose()

    # Sin seedear nada
    result = _knowledge("--db", db_url, "step", "next", "--user", "wa:+unknown")
    assert "flow_node" in result

    traits = _knowledge("--db", db_url, "traits", "--user", "wa:+unknown")
    assert traits == []


def test_persistence_graceful_without_sql(tmp_path: Path) -> None:
    """Sin argumento --db, los comandos fallback graceful."""
    # no db_url, no sqlite file
    result = _knowledge("step", "next", "--user", "wa:+56900000000")
    assert "flow_node" in result

    traits = _knowledge("traits", "--user", "wa:+56900000000")
    assert traits == []


def test_persistence_none_flow_node_does_not_crash(tmp_path: Path) -> None:
    """SessionState con flow_node=None no debe crashear."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        user = Users(external_id="wa:+56900000000", channel="whatsapp")
        session.add(user)
        session.flush()
        session.add(SessionState(
            user_id=user.id, current_node=SessionNode.IDLE,
            flow_node=None, flow_slots={"missing_slots": ["nombre"]},
        ))
        session.commit()
    finally:
        session.close()
        engine.dispose()

    result = _knowledge("--db", db_url, "step", "next", "--user", "wa:+56900000000")
    assert "flow_node" in result  # no crash, fallback a semantic search


def test_persistence_none_flow_slots_does_not_crash(tmp_path: Path) -> None:
    """SessionState con flow_slots=None no debe crashear."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        user = Users(external_id="wa:+56900000000", channel="whatsapp")
        session.add(user)
        session.flush()
        session.add(SessionState(
            user_id=user.id, current_node=SessionNode.IDLE,
            flow_node="conversation:steps.onboarding", flow_slots=None,
        ))
        session.commit()
    finally:
        session.close()
        engine.dispose()

    result = _knowledge("--db", db_url, "step", "next", "--user", "wa:+56900000000")
    assert result["flow_node"] == "conversation:steps.onboarding"
    assert result["missing_slots"] == []


def test_persistence_reflect_connects_to_sql(tmp_path: Path) -> None:
    """knowledge reflect conecta a SQL con tabla chat_history (aunque vacía)."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        user = Users(external_id="wa:+56900000000", channel="whatsapp")
        session.add(user)
        session.flush()
        # Seed algunos mensajes
        session.add(ChatHistory(user_id=user.id, role="user", content="hola", pii_scrubbed=True))
        session.add(ChatHistory(user_id=user.id, role="assistant", content="cómo estás?", pii_scrubbed=True))
        session.commit()
    finally:
        session.close()
        engine.dispose()

    # reflect devuelve lista vacía si no hay patrones recurrentes ( < 5 repeticiones )
    result = _knowledge("--db", db_url, "reflect")
    assert isinstance(result, list)


def test_persistence_nonexistent_db_file(tmp_path: Path) -> None:
    """--db apuntando a archivo inexistente no crashea."""
    db_url = f"sqlite:///{tmp_path}/noexiste.db"
    result = _knowledge("--db", db_url, "step", "next", "--user", "wa:+56900000000")
    assert "flow_node" in result

    traits = _knowledge("--db", db_url, "traits", "--user", "wa:+56900000000")
    assert traits == []