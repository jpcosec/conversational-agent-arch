"""Tool registrar_consulta: ticket MedInfo / reporte de evento adverso persistido."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from kb_agent.models_sql.consultas import Consultas
from kb_agent.models_sql.identity import Base, Users
from kb_agent.tools.consultas import registrar_consulta


def _engine_with_user():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        user = Users(external_id="ui:test-session", channel="ui")
        session.add(user)
        session.commit()
        return engine, user.id


def test_registrar_consulta_persists_a_medinfo_ticket_with_verbatim_text() -> None:
    engine, user_id = _engine_with_user()
    with Session(engine) as session:
        result = registrar_consulta(session, user_id, {"tipo": "medinfo", "texto": "se me olvidó la dosis del jueves, ¿qué hago?"})
        assert result["tipo"] == "medinfo" and result["estado"] == "abierta" and result["urgente"] is False
        # el texto clinico no se duplica en claro en el rastro del turno
        assert result["args"] == {"tipo": "medinfo", "texto_informado": True, "urgente": False}
    with Session(engine) as session:
        row = session.get(Consultas, result["consulta_id"])
        assert row.user_id == user_id and row.texto.startswith("se me olvidó")


def test_registrar_consulta_adverse_event_can_be_urgent_and_rejects_bad_input() -> None:
    engine, user_id = _engine_with_user()
    with Session(engine) as session:
        ok = registrar_consulta(session, user_id, {"tipo": "evento_adverso", "texto": "náuseas fuertes", "urgente": "sí"})
        assert ok["urgente"] is True
        assert registrar_consulta(session, user_id, {"tipo": "otra", "texto": "x"})["status"] == "error"
        assert registrar_consulta(session, user_id, {"tipo": "medinfo"})["status"] == "error"
