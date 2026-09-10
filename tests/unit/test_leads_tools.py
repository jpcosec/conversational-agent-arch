"""Tools ``registrar_lead`` y ``crear_visita``: wrappers semanticos sobre ``leads``/``visitas``.

Sin LLM ni KB: sqlite en memoria, un ``Users`` y su ``SessionState`` con los
slots que el orquestador captura del mensaje crudo (``flow_slots.collected``).
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from kb_agent.models_sql import Base, Leads, Users, Visitas
from kb_agent.models_sql.session import SessionState
from kb_agent.tools import execute_tool, load_tool_handlers
from kb_agent.tools.leads import normalize_modalidad, registrar_lead
from kb_agent.tools.visitas import crear_visita

EMAIL = "ana.perez@example.com"
PHONE = "+56912345678"


def _engine_with_user(collected: dict | None = None):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        user = Users(external_id="ui:test-session", channel="ui")
        session.add(user)
        session.flush()
        session.add(SessionState(user_id=user.id, flow_slots={"collected": dict(collected or {})}))
        session.commit()
        user_id = user.id
    return engine, user_id


def test_registrar_lead_is_a_partial_upsert_completed_with_collected_slots() -> None:
    engine, user_id = _engine_with_user({"email": EMAIL, "telefono": PHONE})
    with Session(engine) as session:
        first = registrar_lead(session, user_id, {"para_quien": "un familiar", "edad_rango": "80 o mas"})
        assert first["lead_id"]
        assert set(first["campos_actualizados"]) == {"email", "telefono", "para_quien", "edad_rango"}
        assert first["conocido"]["email_registrado"] is True
        assert first["falta_contacto"] == []

        second = registrar_lead(session, user_id, {"ciudad": "Santiago", "email": ""})
        assert second["campos_actualizados"] == ["ciudad"]

    with Session(engine) as session:
        lead = session.query(Leads).filter(Leads.user_id == user_id).one()
        assert (lead.email, lead.telefono, lead.para_quien, lead.ciudad) == (EMAIL, PHONE, "un familiar", "Santiago")
        assert session.query(Leads).count() == 1


def test_registrar_lead_result_does_not_leak_pii() -> None:
    engine, user_id = _engine_with_user()
    with Session(engine) as session:
        result = registrar_lead(session, user_id, {"nombre": "Ana Perez", "email": EMAIL, "telefono": PHONE})
    serialized = repr(result)
    assert "Ana" not in serialized and EMAIL not in serialized and PHONE not in serialized
    assert result["args"] == {"nombre_provisto": True, "email_provisto": True, "telefono_provisto": True}


def test_crear_visita_without_contact_creates_nothing_and_says_what_is_missing() -> None:
    engine, user_id = _engine_with_user()
    with Session(engine) as session:
        result = crear_visita(session, user_id, {"modalidad": "en la oficina", "preferencia": "jueves en la tarde"})
        assert result["status"] == "faltan_datos"
        assert result["faltan"] == ["email", "telefono"]
        assert session.query(Visitas).count() == 0
        # lo dicho no se pierde: el lead existe aunque la visita no
        assert session.query(Leads).filter(Leads.user_id == user_id).one_or_none() is not None


def test_crear_visita_uses_collected_slots_and_is_idempotent() -> None:
    engine, user_id = _engine_with_user(
        {"email": EMAIL, "telefono": PHONE, "modalidad": "videollamada", "preferencia_visita": "jueves en la tarde"}
    )
    with Session(engine) as session:
        first = crear_visita(session, user_id, {})
        assert first["creada"] is True
        assert first["estado"] == "solicitada"
        assert first["modalidad"] == "videollamada"
        assert first["preferencia"] == "jueves en la tarde"
        assert first["duracion_min"] == 30
        assert first["conocido"]["email_registrado"] is True

        again = crear_visita(session, user_id, {"modalidad": "video llamada", "preferencia": "jueves en la tarde"})
        assert again["creada"] is False and again["visita_id"] == first["visita_id"]

    with Session(engine) as session:
        assert session.query(Visitas).count() == 1
        visita = session.query(Visitas).one()
        lead = session.query(Leads).filter(Leads.user_id == user_id).one()
        assert visita.lead_id == lead.id and lead.email == EMAIL and lead.telefono == PHONE
    assert EMAIL not in repr(first) and PHONE not in repr(first)


def test_crear_visita_explicit_args_win_over_collected() -> None:
    engine, user_id = _engine_with_user({"email": "viejo@example.com", "telefono": PHONE, "modalidad": "presencial"})
    with Session(engine) as session:
        result = crear_visita(
            session, user_id,
            {"modalidad": "videollamada", "preferencia": "martes en la manana", "email": EMAIL, "titulo": "Reu Vitali - suite"},
        )
        assert result["creada"] is True and result["modalidad"] == "videollamada" and result["titulo"] == "Reu Vitali - suite"
        lead = session.query(Leads).filter(Leads.user_id == user_id).one()
        assert lead.email == EMAIL


def test_execute_tool_trail_redacts_pii_for_both_tools() -> None:
    engine, user_id = _engine_with_user({"modalidad": "presencial", "preferencia_visita": "viernes en la tarde"})
    handlers = load_tool_handlers(
        {"registrar_lead": "kb_agent.tools.leads:registrar_lead", "crear_visita": "kb_agent.tools.visitas:crear_visita"}
    )
    with Session(engine) as session:
        trail = execute_tool(
            session, user_id, {"name": "crear_visita", "args": {"email": EMAIL, "telefono": PHONE}}, handlers
        )
    assert trail["status"] == "ok" and trail["creada"] is True
    assert EMAIL not in repr(trail) and PHONE not in repr(trail)
    assert trail["args"]["email_provisto"] is True


def test_normalize_modalidad() -> None:
    assert normalize_modalidad("en la oficina") == "presencial"
    assert normalize_modalidad("por Zoom") == "videollamada"
    assert normalize_modalidad("Videollamada") == "videollamada"
    assert normalize_modalidad("") is None
