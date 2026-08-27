"""Cableado de ``OrchestratorAgent`` en ``Orchestrator.handle_turn`` (fase 2.4),
sin red: ``offline_orchestrator`` + ``FakeOrchestratorAgent`` (ver
``tests/support/fakes.py``), que reemplaza al ``OrchestratorAgent`` real --
asi se prueba el CABLEADO end-to-end (veto de step, ejecucion real de tool
decidida sin keywords, convivencia con el ``GateAgent``) sin LLM real.

Reproduce los DOS bugs medidos que motivaron la fase 2.4:
  1. el Conversador afirmaba una accion que la policy por keywords nunca
     mando a ejecutar (``tool.called: false`` con texto "¡Listo! Te agendé...");
  2. el orquestador navegaba a un step fuera de ``allowed_transitions`` del
     step activo (``step.before=onboarding``, ``step.after=journey_operativo``,
     con ``allowed_transitions=[registro_estado]``).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from kb_agent.agents.gate import GateAgent
from kb_agent.orchestrator import Orchestrator
from kb_agent.project_config import load_project_config
from kb_agent.tools import load_tool_handlers
from tests.support.fakes import FakeConversador, FakeGate, FakeOrchestratorAgent, FakeTraitMapper, offline_orchestrator

RESERVA_HANDLERS = load_tool_handlers(load_project_config(mode="test").tool_handlers)


class _UncallableClient:
    """Cliente que revienta si se lo llama -- prueba que el PREFILTRO deterministico
    del gate (``response_claims_completed_action``) corta ANTES de necesitar el LLM.
    """

    class _Models:
        def generate_content(self, **_kwargs):
            raise AssertionError("el modelo del gate NO deberia haberse llamado (prefiltro debio cortar)")

    models = _Models()


@pytest.fixture()
def orch_factory(donpeppe_kb: Path, tmp_db_url: str):
    made: list[Orchestrator] = []

    def _make(**kwargs) -> Orchestrator:
        o = offline_orchestrator(donpeppe_kb, tmp_db_url, **kwargs)
        made.append(o)
        return o

    yield _make
    for o in made:
        o.close()


# ── EL TEST MAS IMPORTANTE: veto de transicion fuera de allowed_transitions ─
def test_step_target_outside_allowed_transitions_is_not_applied(orch_factory) -> None:
    """Bug 2 reproducido: el orquestador propone un step FUERA del grafo
    declarado por el step activo. La guardia de codigo lo descarta -- el
    turno se queda en el step actual -- y el veto queda explicito en el
    rastro (``decisions.orquestador.step_target_vetado``).
    """
    def rogue_decision(compiled_context: dict) -> dict:
        # El unico step permitido desde onboarding (donpeppe_kb) es booking;
        # esto imita el bug real: navegar a un step no declarado.
        return {"kind": "nl", "flow_target": "conversation:steps.NO_AUTORIZADO"}

    orch = orch_factory(orchestrator_agent=FakeOrchestratorAgent(rogue_decision))

    turn = orch.handle_turn(external_id="ui:veto", message="hola, como estas?")

    # el step NO cambio -- se quedo en el step activo del turno
    assert turn["flow_node"] == "conversation:steps.onboarding"
    assert turn["decisions"]["step"]["before"] is None  # primer turno, sin sesion previa
    assert turn["decisions"]["step"]["after"] == "conversation:steps.onboarding"
    assert turn["decisions"]["step"]["target"] is None  # _flow_target nunca se poblo

    # el veto queda EXPLICITO y auditable en el rastro del orquestador
    assert turn["decisions"]["orquestador"]["step_target_vetado"] == "conversation:steps.NO_AUTORIZADO"
    assert turn["decisions"]["orquestador"]["reason"]

    # y persiste: un segundo turno arranca del mismo step, no del vetoed
    second = orch.handle_turn(external_id="ui:veto", message="otra pregunta")
    assert second["decisions"]["step"]["before"] == "conversation:steps.onboarding"


def test_step_target_within_allowed_transitions_is_applied(orch_factory) -> None:
    """Control: una transicion SI declarada se aplica normalmente (la
    guardia no bloquea navegacion legitima)."""
    def valid_decision(compiled_context: dict) -> dict:
        return {"kind": "nl", "flow_target": "conversation:steps.booking"}

    orch = orch_factory(orchestrator_agent=FakeOrchestratorAgent(valid_decision))

    turn = orch.handle_turn(external_id="ui:veto-ok", message="hola")

    assert turn["flow_node"] == "conversation:steps.booking"
    assert turn["decisions"]["orquestador"].get("step_target_vetado") is None


# ── BUG 1: tool_call decidido con contexto completo, no con keywords ────────
def test_typed_tool_call_executes_even_without_keyword_match(donpeppe_kb: Path, tmp_db_url: str) -> None:
    """Reproduce el bug 1: un mensaje SIN ninguna keyword de intencion de tool
    (``decide_turn`` clasificaria esto como 'nl', nunca ejecutaria la tool)
    pero el orquestador (aca, el fake sustituyendo al LLM) SI decide
    'tool_call' con el contexto completo -- la tool se ejecuta de verdad.
    """
    CONFIRMATION_MESSAGE = "sí, dale, confirmalo"  # sin "reserva/mesa/agenda/..." -- decide_turn no matchea nada

    def forced_tool_call(compiled_context: dict) -> dict:
        return {
            "kind": "tool_call",
            "function_call": {
                "name": "crear_reserva",
                "args": {"fecha": "viernes", "hora": "20:00", "personas": 4, "nombre": "Rojas"},
            },
        }

    orch = offline_orchestrator(
        donpeppe_kb, tmp_db_url,
        orchestrator_agent=FakeOrchestratorAgent(forced_tool_call),
        tool_handlers=RESERVA_HANDLERS,
    )
    try:
        # Control: sin forzar la decision, decide_turn (backing default del
        # fake) NO detecta intencion de tool en este mensaje -- confirma que
        # el mensaje elegido de verdad ejercita el camino "sin keywords".
        control = offline_orchestrator(donpeppe_kb, tmp_db_url, tool_handlers=RESERVA_HANDLERS)
        try:
            control_turn = control.handle_turn(external_id="ui:control", message=CONFIRMATION_MESSAGE)
            assert control_turn["kind"] != "tool_call"
        finally:
            control.close()

        turn = orch.handle_turn(external_id="ui:bug1", message=CONFIRMATION_MESSAGE)

        assert turn["kind"] == "tool_call"
        assert turn["system_turn"] is not None
        assert turn["system_turn"]["status"] == "ok"
        assert turn["system_turn"]["tool"] == "crear_reserva"
        assert orch.count_reservas() == 1
        # el conversador redacto DESPUES del resultado real de la tool (no antes)
        assert turn["decisions"]["conversador"]["draft"] == turn["reply"]
        assert "reserva_id" in turn["reply"]
    finally:
        orch.close()


def test_typed_tool_call_without_registered_handler_still_yields_unknown_tool(
    donpeppe_kb: Path, tmp_db_url: str
) -> None:
    """La guardia de step no reemplaza el manejo existente de tools desconocidas."""
    def forced_tool_call(compiled_context: dict) -> dict:
        return {"kind": "tool_call", "function_call": {"name": "no_existe", "args": {}}}

    orch = offline_orchestrator(
        donpeppe_kb, tmp_db_url, tool_handlers={},
        orchestrator_agent=FakeOrchestratorAgent(forced_tool_call),
    )
    try:
        turn = orch.handle_turn(external_id="ui:unknown", message="algo")
        assert turn["system_turn"]["status"] == "unknown_tool"
    finally:
        orch.close()


# ── convivencia gate + orquestador: el gate sigue de backstop ───────────────
def test_gate_still_catches_false_action_claim_when_orchestrator_wrongly_says_nl(orch_factory) -> None:
    """Aunque el orquestador tipado (fase 2.4) sea la correccion de fondo del
    bug 1, si de todos modos decide mal ('nl' cuando debia ser 'tool_call')
    y el Conversador redacta afirmando una accion no ejecutada, el
    ``GateAgent`` (fase 2.3) sigue funcionando como red de seguridad -- los
    dos mecanismos conviven, no se pisan.
    """
    def wrong_nl_decision(compiled_context: dict) -> dict:
        return {"kind": "nl"}  # deberia haber sido tool_call, pero "se equivoca"

    claiming_conversador = FakeConversador(
        lambda _c: "¡Listo! Te agendé el recordatorio para tu aplicación semanal, todos los lunes a las 9 AM."
    )
    # Gate REAL (no FakeGate): asi se ejercita el prefiltro deterministico de
    # verdad (``response_claims_completed_action``), no solo el cableado.
    real_gate = GateAgent(client=_UncallableClient(), model="gemini-test", gate_atoms=[])

    orch = orch_factory(
        orchestrator_agent=FakeOrchestratorAgent(wrong_nl_decision),
        conversador=claiming_conversador,
        gate=real_gate,
    )

    turn = orch.handle_turn(external_id="ui:backstop", message="agendame un recordatorio los lunes a las 9")

    assert turn["kind"] == "derived"  # el gate reemplazo la respuesta
    assert turn["system_turn"] is None  # ninguna tool se ejecuto de verdad
    assert turn["decisions"]["gate"]["approved"] is False
    assert "no hubo ninguna ejecucion real de tool" in turn["decisions"]["gate"]["reasons"][0]
    # el borrador original (el que afirmaba la accion) se conserva en el rastro, no se envia
    assert "agendé" in turn["decisions"]["conversador"]["draft"]
    assert "agendé" not in turn["reply"]


def test_orchestrator_and_gate_do_not_double_reject_a_correct_tool_call(orch_factory) -> None:
    """Cuando el orquestador SI decide bien (tool_call), el gate no tiene
    nada que objetar -- ve tool_called=True y no dispara el prefiltro."""
    def correct_tool_call(compiled_context: dict) -> dict:
        return {
            "kind": "tool_call",
            "function_call": {"name": "crear_reserva", "args": {"fecha": "viernes", "hora": "20:00", "personas": 2}},
        }

    gate = FakeGate()
    orch = orch_factory(
        orchestrator_agent=FakeOrchestratorAgent(correct_tool_call), gate=gate, tool_handlers=RESERVA_HANDLERS
    )

    turn = orch.handle_turn(external_id="ui:no-double-reject", message="reservame algo")

    assert turn["kind"] == "tool_call"
    assert turn["system_turn"]["status"] == "ok"
    # el gate NUNCA se llama en la rama tool_call (ver Orchestrator.handle_turn)
    assert gate.calls == []
