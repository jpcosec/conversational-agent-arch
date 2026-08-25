from pathlib import Path
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kb_agent.models_sql.identity import Base, Users
from kb_agent.models_sql.session import ChatHistory, SessionNode, SessionState


def _build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_session_state_persists_current_node_transitions() -> None:
    with _build_session() as session:
        user = Users(external_id="wa:+56933333333", channel="whatsapp")
        session.add(user)
        session.flush()

        state = SessionState(user_id=user.id, current_node=SessionNode.IDLE)
        session.add(state)
        session.commit()

        persisted = session.scalar(
            select(SessionState).where(SessionState.user_id == user.id)
        )
        assert persisted is not None
        assert persisted.current_node == SessionNode.IDLE

        persisted.current_node = SessionNode.WAITING_TOOL
        session.commit()

        transitioned = session.scalar(
            select(SessionState).where(SessionState.user_id == user.id)
        )
        assert transitioned is not None
        assert transitioned.current_node == SessionNode.WAITING_TOOL


def test_session_state_active_domain_accepts_null_and_string_values() -> None:
    with _build_session() as session:
        user = Users(external_id="telegram:111", channel="telegram")
        session.add(user)
        session.flush()

        state = SessionState(user_id=user.id, active_domain=None)
        session.add(state)
        session.commit()

        persisted = session.scalar(
            select(SessionState).where(SessionState.user_id == user.id)
        )
        assert persisted is not None
        assert persisted.active_domain is None

        persisted.active_domain = "pizza"
        session.commit()

        updated = session.scalar(
            select(SessionState).where(SessionState.user_id == user.id)
        )
        assert updated is not None
        assert updated.active_domain == "pizza"


def test_session_state_buffer_defaults_and_keys_are_isolated() -> None:
    with _build_session() as session:
        user_a = Users(external_id="user-a", channel="web")
        user_b = Users(external_id="user-b", channel="web")
        session.add_all([user_a, user_b])
        session.flush()

        state_a = SessionState(user_id=user_a.id)
        state_b = SessionState(user_id=user_b.id)
        session.add_all([state_a, state_b])
        session.commit()

        persisted_a = session.scalar(
            select(SessionState).where(SessionState.user_id == user_a.id)
        )
        persisted_b = session.scalar(
            select(SessionState).where(SessionState.user_id == user_b.id)
        )
        assert persisted_a is not None
        assert persisted_b is not None
        assert persisted_a.buffer == {"debounce": [], "tool_wait": []}
        assert persisted_b.buffer == {"debounce": [], "tool_wait": []}

        mutated_buffer = {
            "debounce": ["hola", "necesito ayuda"],
            "tool_wait": [],
        }
        persisted_a.buffer = mutated_buffer
        session.commit()

        updated_a = session.scalar(
            select(SessionState).where(SessionState.user_id == user_a.id)
        )
        updated_b = session.scalar(
            select(SessionState).where(SessionState.user_id == user_b.id)
        )
        assert updated_a is not None
        assert updated_b is not None
        assert updated_a.buffer["debounce"] == ["hola", "necesito ayuda"]
        assert updated_a.buffer["tool_wait"] == []
        assert updated_b.buffer == {"debounce": [], "tool_wait": []}


def test_chat_history_defaults_pii_scrubbed_to_false() -> None:
    with _build_session() as session:
        user = Users(external_id="user-history", channel="web")
        session.add(user)
        session.flush()

        history_row = ChatHistory(
            user_id=user.id,
            role="user",
            content="Mi correo es ejemplo@test.com",
        )
        session.add(history_row)
        session.commit()

        persisted = session.scalar(
            select(ChatHistory).where(ChatHistory.user_id == user.id)
        )
        assert persisted is not None
        assert persisted.pii_scrubbed is False
