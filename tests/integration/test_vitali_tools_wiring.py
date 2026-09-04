"""Cableado end-to-end (sin LLM) de las tools de Vitali en ``Orchestrator.handle_turn``.

Lo que se prueba es el contrato entre piezas, no el juicio del modelo:
- la KB de Vitali declara las dos tools y el orquestador las ve como
  ``tools_disponibles``;
- los slots capturados del mensaje crudo entran al contexto compilado ANTES
  de decidir (``collected_slots``) y el handler los usa como argumentos;
- un ``tool_call`` con ``flow_target`` ejecuta la tool, persiste ``leads`` y
  ``visitas``, avanza el step y redacta con el resultado real;
- el rastro del turno no expone email ni telefono en claro.
"""
from __future__ import annotations

from pathlib import Path

from kb_agent.agent import build_function_declarations
from kb_agent.models_sql import Leads, Visitas
from kb_agent.models_sql.session import SessionState
from kb_agent.project_config import load_project_config
from kb_agent.tools import load_tool_handlers
from tests.support.fakes import FakeOrchestratorAgent, offline_orchestrator

VITALI_CFG = Path(__file__).resolve().parents[2] / "project.vitali.yaml"
EMAIL = "ana.perez@example.com"
PHONE = "+56912345678"
CONTACT_STEP = "conversation:steps.datos_contacto"
CLOSE_STEP = "conversation:steps.cierre"


def _vitali_handlers():
    return load_tool_handlers(load_project_config(VITALI_CFG, mode="test").tool_handlers)


def _place_user_at(orch, external_id: str, step: str, collected: dict) -> None:
    with orch.SessionLocal() as s:
        user = orch.ensure_user(s, external_id)
        state = s.get(SessionState, user.id)
        if state is None:
            state = SessionState(user_id=user.id)
            s.add(state)
        state.flow_node = step
        state.flow_slots = {"collected": dict(collected)}
        s.commit()


def test_vitali_config_declares_both_tools() -> None:
    assert set(_vitali_handlers()) == {"registrar_lead", "crear_visita"}


def test_crear_visita_turn_persists_lead_and_visit_and_advances_to_close(vitali_kb: Path, tmp_db_url: str) -> None:
    def decide(compiled):
        # El fake decide lo que el OrchestratorAgent real decidiria con email
        # y telefono en el turno y modalidad/preferencia ya capturados.
        return {
            "kind": "tool_call",
            "function_call": {"name": "crear_visita", "args": {"email": EMAIL, "telefono": PHONE}},
            "flow_target": CLOSE_STEP,
            "reason": "test",
        }

    agent = FakeOrchestratorAgent(decide)
    orch = offline_orchestrator(vitali_kb, tmp_db_url, orchestrator_agent=agent, tool_handlers=_vitali_handlers())
    try:
        _place_user_at(orch, "ui:lead-1", CONTACT_STEP, {"modalidad": "videollamada", "preferencia_visita": "jueves en la tarde"})
        turn = orch.handle_turn(external_id="ui:lead-1", message=f"Mi correo es {EMAIL} y mi celular {PHONE}")

        # 1. la KB de Vitali declara las tools y el orquestador las vio
        seen = {d["name"] for d in build_function_declarations(agent.calls[0])}
        assert {"registrar_lead", "crear_visita"} <= seen
        # 2. los slots capturados (incluido lo de ESTE mensaje) entraron antes de decidir
        captured = agent.calls[0]["collected_slots"]
        assert captured["email"] == EMAIL and captured["modalidad"] == "videollamada"

        # 3. tool ejecutada, persistida y step avanzado
        assert turn["kind"] == "tool_call"
        assert turn["system_turn"]["status"] == "ok" and turn["system_turn"]["creada"] is True
        assert turn["flow_node"] == CLOSE_STEP
        assert turn["decisions"]["step"] == {
            **turn["decisions"]["step"], "before": CONTACT_STEP, "after": CLOSE_STEP, "target": CLOSE_STEP
        }
        assert str(turn["reply"]).startswith("[tool-ok]")

        with orch.SessionLocal() as s:
            visita = s.query(Visitas).one()
            lead = s.query(Leads).one()
            assert (visita.modalidad, visita.preferencia, visita.estado) == ("videollamada", "jueves en la tarde", "solicitada")
            assert visita.user_id == turn["user_id"] and visita.lead_id == lead.id
            assert (lead.email, lead.telefono) == (EMAIL, PHONE)

        # 4. rastro sin PII en claro
        trail = repr(turn["decisions"]["tool"])
        assert EMAIL not in trail and PHONE not in trail
        assert turn["decisions"]["tool"]["args"]["email_provisto"] is True
    finally:
        orch.close()


def test_crear_visita_with_missing_contact_does_not_advance(vitali_kb: Path, tmp_db_url: str) -> None:
    agent = FakeOrchestratorAgent(
        lambda compiled: {
            "kind": "tool_call",
            "function_call": {"name": "crear_visita", "args": {"modalidad": "presencial", "preferencia": "lunes en la manana"}},
            "flow_target": CLOSE_STEP,
            "reason": "test",
        }
    )
    orch = offline_orchestrator(vitali_kb, tmp_db_url, orchestrator_agent=agent, tool_handlers=_vitali_handlers())
    try:
        _place_user_at(orch, "ui:lead-2", CONTACT_STEP, {})
        turn = orch.handle_turn(external_id="ui:lead-2", message="el lunes en la manana, presencial")
        assert turn["system_turn"]["status"] == "faltan_datos"
        assert turn["system_turn"]["faltan"] == ["email", "telefono"]
        with orch.SessionLocal() as s:
            assert s.query(Visitas).count() == 0
        # Sin visita creada el flujo NO avanza al cierre aunque el orquestador
        # lo haya propuesto: el Conversador redacta con el resultado real
        # (faltan_datos) y pide lo que falta desde el mismo step.
        assert turn["flow_node"] == CONTACT_STEP
        assert turn["decisions"]["step"]["target"] is None
        assert turn["decisions"]["tool"]["called"] is True
        assert turn["decisions"]["tool"]["status"] == "faltan_datos"
    finally:
        orch.close()
