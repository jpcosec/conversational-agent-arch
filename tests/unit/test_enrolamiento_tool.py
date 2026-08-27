"""Tool registrar_enrolamiento: marca users.enrolled sin persistir PII en claro."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from kb_agent.models_sql.identity import Base, Users
from kb_agent.tools import execute_tool
from kb_agent.tools.enrolamiento import registrar_enrolamiento


def _engine_with_user(enrolled: bool = False):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        user = Users(external_id="ui:test-session", channel="ui", enrolled=enrolled)
        session.add(user)
        session.commit()
        user_id = user.id
    return engine, user_id


def test_registrar_enrolamiento_marks_user_enrolled() -> None:
    engine, user_id = _engine_with_user(enrolled=False)
    with Session(engine) as session:
        result = registrar_enrolamiento(
            session,
            user_id,
            {"nombre": "Juana Perez", "telefono": "+56911112222", "mail": "juana@example.com"},
        )
        assert result["enrolled"] is True
        assert result["user_id"] == user_id

    with Session(engine) as session:
        row = session.get(Users, user_id)
        assert row.enrolled is True


def test_registrar_enrolamiento_does_not_leak_pii_in_its_own_result() -> None:
    engine, user_id = _engine_with_user()
    with Session(engine) as session:
        result = registrar_enrolamiento(
            session,
            user_id,
            {"nombre": "Juana Perez", "telefono": "+56911112222", "mail": "juana@example.com"},
        )

    serialized = repr(result)
    assert "Juana" not in serialized
    assert "+56911112222" not in serialized
    assert "juana@example.com" not in serialized
    assert result["args"] == {
        "telefono_provisto": True,
        "mail_provisto": True,
        "nombre_provisto": True,
    }


def test_registrar_enrolamiento_handles_missing_user_gracefully() -> None:
    engine, _ = _engine_with_user()
    with Session(engine) as session:
        result = registrar_enrolamiento(session, None, {"nombre": "X"})
        assert result["enrolled"] is False
        assert result["user_id"] is None


def test_execute_tool_system_turn_does_not_leak_raw_pii_args() -> None:
    """``execute_tool`` agrega los args crudos de la llamada al System Turn;
    el handler debe pisarlos con su propio ``args`` redactado (ver
    ``kb_agent/tools/enrolamiento.py``), o el telefono/mail/nombre quedarian
    en claro en ``turns.tool`` (columna JSON que no pasa por el scrubber de
    ``chat_history``).
    """
    engine, user_id = _engine_with_user()
    with Session(engine) as session:
        system_turn = execute_tool(
            session,
            user_id,
            {
                "name": "registrar_enrolamiento",
                "args": {"nombre": "Juana Perez", "telefono": "+56911112222", "mail": "juana@example.com"},
            },
            {"registrar_enrolamiento": registrar_enrolamiento},
        )

    assert system_turn["status"] == "ok"
    assert system_turn["enrolled"] is True
    serialized = repr(system_turn)
    assert "Juana" not in serialized
    assert "+56911112222" not in serialized
    assert "juana@example.com" not in serialized
