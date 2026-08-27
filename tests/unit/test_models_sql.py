"""Modelos SQL: identidad (Users/UserTraits), sesion (SessionState/ChatHistory), turnos (Turns)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from kb_agent.models_sql.identity import Base, UserTraits, Users
from kb_agent.models_sql.reservas import Reservas
from kb_agent.models_sql.session import ChatHistory, SessionNode, SessionState
from kb_agent.models_sql.turns import Turns


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _user(session: Session, external_id: str, channel: str = "whatsapp") -> Users:
    user = Users(external_id=external_id, channel=channel)
    session.add(user)
    session.flush()
    return user


def test_traits_are_reusable_subgraphs_shared_across_users(session: Session) -> None:
    a, b = _user(session, "wa:+1"), _user(session, "wa:+2")
    session.add_all([
        UserTraits(user_id=a.id, trait_id="trait-vegetariano", confidence=0.95, source="extractor"),
        UserTraits(user_id=a.id, trait_id="trait-prefiere-picante", confidence=0.80, source="extractor"),
        UserTraits(user_id=b.id, trait_id="trait-vegetariano", confidence=0.70, source="extractor"),
    ])
    session.commit()

    assert {t.trait_id for t in session.scalar(select(Users).where(Users.id == a.id)).traits} == {"trait-vegetariano", "trait-prefiere-picante"}
    assert {r.user_id for r in session.scalars(select(UserTraits).where(UserTraits.trait_id == "trait-vegetariano"))} == {a.id, b.id}


def test_trait_id_is_free_text_without_sldb_validation(session: Session) -> None:
    user = _user(session, "telegram:999", "telegram")
    weird = "trait:any/string::from-external-source?value=42"
    session.add(UserTraits(user_id=user.id, trait_id=weird, confidence=0.55, source="manual"))
    session.commit()
    assert session.scalar(select(UserTraits.trait_id).where(UserTraits.trait_id == weird)) == weird


def test_session_state_persists_node_domain_and_flow(session: Session) -> None:
    user = _user(session, "wa:+3")
    state = SessionState(user_id=user.id, current_node=SessionNode.IDLE, active_domain=None)
    session.add(state)
    session.commit()
    assert state.buffer == {"debounce": [], "tool_wait": []}
    assert state.active_domain is None and state.flow_node is None and state.flow_slots is None

    state.current_node = SessionNode.WAITING_TOOL
    state.active_domain = "pizzeria"
    state.flow_node = "conversation:steps.booking"
    state.flow_slots = {"missing_slots": ["hora"]}
    state.buffer = {"debounce": ["hola"], "tool_wait": []}
    session.commit()
    session.expire_all()

    reloaded = session.get(SessionState, user.id)
    assert reloaded.current_node == SessionNode.WAITING_TOOL
    assert reloaded.active_domain == "pizzeria"
    assert (reloaded.flow_node, reloaded.flow_slots) == ("conversation:steps.booking", {"missing_slots": ["hora"]})
    assert reloaded.buffer["debounce"] == ["hola"]


def test_session_buffers_are_isolated_per_user(session: Session) -> None:
    a, b = _user(session, "user-a", "web"), _user(session, "user-b", "web")
    session.add_all([SessionState(user_id=a.id), SessionState(user_id=b.id)])
    session.commit()
    session.get(SessionState, a.id).buffer = {"debounce": ["x"], "tool_wait": []}
    session.commit()
    session.expire_all()
    assert session.get(SessionState, b.id).buffer == {"debounce": [], "tool_wait": []}


def test_chat_history_defaults_to_unscrubbed_and_validates_role(session: Session) -> None:
    user = _user(session, "user-history", "web")
    row = ChatHistory(user_id=user.id, role="user", content="Mi correo es ejemplo@test.com")
    session.add(row)
    session.commit()
    assert row.pii_scrubbed is False
    assert row.created_at is not None

    session.add(ChatHistory(user_id=user.id, role="alien", content="x"))
    with pytest.raises(Exception):
        session.commit()
    session.rollback()


def _turn_kwargs(user_id: int, session_id: str = "sess-1", turn_id: str = "t1") -> dict:
    return dict(
        turn_id=turn_id,
        session_id=session_id,
        user_id=user_id,
        step_before="idle",
        step_after="drafting_response",
        decision={"action": "responder", "motivo": "saludo"},
        draft="Hola, en que te puedo ayudar?",
        gate={"approved": True, "reasons": []},
        bundle=[{"doc_id": "doc-1", "family": "menu", "motivo": "match directo", "score": 0.9}],
    )


def test_turns_stores_full_audit_trail_of_a_turn(session: Session) -> None:
    user = _user(session, "wa:+turns-1")
    turn = Turns(**_turn_kwargs(user.id))
    session.add(turn)
    session.commit()
    session.expire_all()

    reloaded = session.scalar(select(Turns).where(Turns.turn_id == "t1"))
    assert reloaded.session_id == "sess-1"
    assert reloaded.user_id == user.id
    assert (reloaded.step_before, reloaded.step_after) == ("idle", "drafting_response")
    assert reloaded.decision == {"action": "responder", "motivo": "saludo"}
    assert reloaded.draft == "Hola, en que te puedo ayudar?"
    assert reloaded.gate == {"approved": True, "reasons": []}
    assert reloaded.bundle == [{"doc_id": "doc-1", "family": "menu", "motivo": "match directo", "score": 0.9}]
    assert reloaded.tool is None
    assert reloaded.created_at is not None


def test_turns_tool_field_is_nullable_and_optional(session: Session) -> None:
    user = _user(session, "wa:+turns-2")
    kwargs = _turn_kwargs(user.id, session_id="sess-2")
    kwargs["tool"] = {"name": "crear_reserva", "result": {"ok": True}}
    session.add(Turns(**kwargs))
    session.commit()
    session.expire_all()

    reloaded = session.scalar(select(Turns).where(Turns.session_id == "sess-2"))
    assert reloaded.tool == {"name": "crear_reserva", "result": {"ok": True}}


def test_turns_step_before_and_after_are_nullable(session: Session) -> None:
    user = _user(session, "wa:+turns-3")
    kwargs = _turn_kwargs(user.id, session_id="sess-3")
    kwargs["step_before"] = None
    kwargs["step_after"] = None
    session.add(Turns(**kwargs))
    session.commit()
    session.expire_all()

    reloaded = session.scalar(select(Turns).where(Turns.session_id == "sess-3"))
    assert reloaded.step_before is None and reloaded.step_after is None


def test_turns_requires_a_user(session: Session) -> None:
    kwargs = _turn_kwargs(user_id=None, session_id="sess-4")  # type: ignore[arg-type]
    session.add(Turns(**kwargs))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_turn_id_is_unique_only_within_its_session(session: Session) -> None:
    """turn_id tipo "t1" lo genera un contador por-sesion (frontends/chat/app.py),
    asi que el mismo turn_id puede repetirse en sesiones distintas: la unicidad
    real es (session_id, turn_id), no turn_id solo."""
    a, b = _user(session, "wa:+turns-5a"), _user(session, "wa:+turns-5b")
    session.add(Turns(**_turn_kwargs(a.id, session_id="sess-5a", turn_id="t1")))
    session.add(Turns(**_turn_kwargs(b.id, session_id="sess-5b", turn_id="t1")))
    session.commit()

    rows = session.scalars(select(Turns).where(Turns.turn_id == "t1")).all()
    assert {r.session_id for r in rows} == {"sess-5a", "sess-5b"}


def test_turn_id_rejects_duplicates_within_the_same_session(session: Session) -> None:
    user = _user(session, "wa:+turns-6")
    session.add(Turns(**_turn_kwargs(user.id, session_id="sess-6", turn_id="t1")))
    session.commit()

    session.add(Turns(**_turn_kwargs(user.id, session_id="sess-6", turn_id="t1")))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_chat_history_session_id_is_nullable_and_indexable(session: Session) -> None:
    user = _user(session, "wa:+ch-session")
    with_session = ChatHistory(user_id=user.id, role="user", content="hola", session_id="sess-7")
    without_session = ChatHistory(user_id=user.id, role="user", content="legado")
    session.add_all([with_session, without_session])
    session.commit()
    session.expire_all()

    rows = session.scalars(
        select(ChatHistory).where(ChatHistory.user_id == user.id).order_by(ChatHistory.id)
    ).all()
    assert [r.session_id for r in rows] == ["sess-7", None]


def test_reservas_table_links_optional_user(session: Session) -> None:
    user = _user(session, "wa:+4")
    session.add_all([
        Reservas(user_id=user.id, fecha="viernes", hora="20:00", personas=4, nombre="Rojas"),
        Reservas(user_id=None, fecha="sabado", hora="21:00", personas=2),
    ])
    session.commit()
    rows = session.scalars(select(Reservas).order_by(Reservas.id)).all()
    assert [(r.user_id, r.personas, r.nombre) for r in rows] == [(user.id, 4, "Rojas"), (None, 2, None)]
