"""Tests de ``kb_agent.agents.orchestrator_agent.OrchestratorAgent`` (fase 2.4),
todos sin red.

Cubre: el render del grafo de steps a ``static_instruction`` (gobernanza por
KB, mismo patron que ``render_gate_criteria``), el prefiltro deterministico
(contexto vacio + sin tools -> fallback sin llamar al modelo), el contrato de
``decide`` con un modelo fake (tool_call / nl / fallback con ``reason``
siempre presente), y el test MAS IMPORTANTE del plan: la guardia dura
``apply_transition_guard`` -- un ``step_target`` fuera de
``allowed_transitions`` NUNCA se aplica, venga de donde venga la decision.
"""
from __future__ import annotations

from typing import Any

import pytest

from kb_agent.agents.orchestrator_agent import (
    OrchestratorAgent,
    OrchestratorDecision,
    ToolCallDecision,
    apply_transition_guard,
    render_orchestrator_flow,
)

STEP_ATOMS = [
    {
        "id": "conversation:steps.onboarding",
        "title": "Onboarding",
        "kind": "interaccion_simple",
        "instructions": "Saluda y recolecta el motivo de contacto.",
        "allowed_transitions": "conversation:steps.booking",
    },
    {
        "id": "conversation:steps.booking",
        "title": "Reserva",
        "kind": "llamado_tool",
        "instructions": "Confirma fecha/hora/personas y llama a crear_reserva.",
        "allowed_transitions": "",
    },
]

RESERVA_TOOL_DECLARATION = {
    "name": "crear_reserva",
    "description": "Crea una reserva",
    "parameters": {
        "type": "object",
        "properties": {"fecha": {"type": "string"}, "personas": {"type": "integer"}},
        "required": ["fecha", "personas"],
    },
}


class _Resp:
    """Respuesta cruda minima, con la forma que expone google-genai."""

    def __init__(self, text: str = "", parsed: Any = None) -> None:
        self.text = text
        self.parsed = parsed
        self.function_calls: list[Any] = []


class _FakeModels:
    def __init__(self, responder) -> None:
        self._responder = responder
        self.calls: list[dict[str, Any]] = []

    def generate_content(self, **kwargs: Any) -> _Resp:
        self.calls.append(kwargs)
        return self._responder(kwargs)


class _FakeClient:
    """Cliente fake; si no se le da ``responder``, FALLA si se lo llama."""

    def __init__(self, responder=None) -> None:
        if responder is None:
            def responder(_kwargs: dict[str, Any]) -> _Resp:
                raise AssertionError("el modelo NO deberia haberse llamado (prefiltro debio cortar)")
        self.models = _FakeModels(responder)

    @property
    def calls(self) -> list[dict[str, Any]]:
        return self.models.calls


def _decision_client(decision: OrchestratorDecision) -> _FakeClient:
    return _FakeClient(responder=lambda _kw: _Resp(text=decision.model_dump_json(), parsed=decision))


GROUNDED_CONTEXT = {
    "question": "¿tienen mesa para el viernes?",
    "flow_node": "conversation:steps.onboarding",
    "allowed_transitions": ["conversation:steps.booking"],
    "domain_facts": [{"id": "d", "body": "abrimos a las 19"}],
    "rules": [],
    "tools": [RESERVA_TOOL_DECLARATION],
    "is_empty": False,
}


# ── render del grafo: gobernanza por KB (mismo espiritu que el test de gate) ─
def test_render_orchestrator_flow_reflects_step_atoms() -> None:
    rendered = render_orchestrator_flow(STEP_ATOMS)
    assert "conversation:steps.onboarding" in rendered
    assert "conversation:steps.booking" in rendered
    assert "Confirma fecha/hora/personas" in rendered


def test_render_orchestrator_flow_without_steps_uses_no_graph_instruction() -> None:
    rendered = render_orchestrator_flow([])
    assert "no tiene ningun ConversationStep" in rendered
    assert "step_target" in rendered


def test_static_instruction_changes_when_kb_step_graph_changes() -> None:
    baseline = OrchestratorAgent(client=_FakeClient(), model="gemini-test", step_atoms=STEP_ATOMS[:1])
    extended = OrchestratorAgent(client=_FakeClient(), model="gemini-test", step_atoms=STEP_ATOMS)
    assert baseline.static_instruction != extended.static_instruction
    assert "Confirma fecha/hora/personas" not in baseline.static_instruction
    assert "Confirma fecha/hora/personas" in extended.static_instruction


# ── prefiltro deterministico: contexto vacio + sin tools -> fallback sin LLM ─
def test_empty_context_without_tools_returns_fallback_without_calling_model() -> None:
    client = _FakeClient()  # lanza si se llama al modelo
    agent = OrchestratorAgent(client=client, model="gemini-test", step_atoms=STEP_ATOMS)

    result = agent.decide({"question": "algo", "is_empty": True, "domain_facts": [], "rules": [], "tools": []})

    assert result["kind"] == "fallback"
    assert result["reason"]
    assert client.calls == []


def test_empty_context_with_tools_still_calls_model() -> None:
    """Si hay tools declaradas, el modelo decide igual (podria ser tool_call)."""
    decision = OrchestratorDecision(kind="nl", reason="sin grounding pero puedo redactar con lo poco que hay")
    client = _decision_client(decision)
    agent = OrchestratorAgent(client=client, model="gemini-test", step_atoms=STEP_ATOMS)

    result = agent.decide({
        "question": "algo", "is_empty": True, "domain_facts": [], "rules": [],
        "tools": [RESERVA_TOOL_DECLARATION],
    })

    assert len(client.calls) == 1
    assert result["kind"] == "nl"


# ── tool_call: el modelo produce name+args, sin matching de keywords ────────
def test_tool_call_decision_is_translated_to_function_call() -> None:
    decision = OrchestratorDecision(
        kind="tool_call",
        tool_call=ToolCallDecision(name="crear_reserva", args={"fecha": "viernes", "personas": 4}),
        reason="El usuario confirmo fecha y personas, la tool esta declarada y tengo todos los argumentos.",
    )
    client = _decision_client(decision)
    agent = OrchestratorAgent(client=client, model="gemini-test", step_atoms=STEP_ATOMS)

    result = agent.decide(GROUNDED_CONTEXT)

    assert result["kind"] == "tool_call"
    assert result["function_call"] == {"name": "crear_reserva", "args": {"fecha": "viernes", "personas": 4}}
    assert result["reason"] == decision.reason
    # el contexto dinamico le paso las tools declaradas del turno, no una busqueda propia
    dynamic_context_sent = client.calls[0]["contents"][0]["parts"][0]["text"]
    assert "crear_reserva" in dynamic_context_sent


def test_tool_call_kind_without_tool_call_payload_degrades_to_nl() -> None:
    """Guardia: el modelo dice 'tool_call' pero no da la tool -- no rompe el turno."""
    decision = OrchestratorDecision(kind="tool_call", tool_call=None, reason="deberia haber elegido una tool")
    client = _decision_client(decision)
    agent = OrchestratorAgent(client=client, model="gemini-test", step_atoms=STEP_ATOMS)

    result = agent.decide(GROUNDED_CONTEXT)

    assert result["kind"] == "nl"
    assert "function_call" not in result
    assert "degradado a 'nl'" in result["reason"]


# ── reason siempre presente, incluso en 'nl' y 'fallback' ───────────────────
def test_nl_decision_carries_reason() -> None:
    decision = OrchestratorDecision(kind="nl", reason="no hay tool que aplique, redacto con el grounding")
    client = _decision_client(decision)
    agent = OrchestratorAgent(client=client, model="gemini-test", step_atoms=STEP_ATOMS)

    result = agent.decide(GROUNDED_CONTEXT)

    assert result == {"kind": "nl", "reason": decision.reason}


# ── LA GUARDIA: step_target fuera de allowed_transitions NUNCA se aplica ────
class TestApplyTransitionGuard:
    def test_target_within_allowed_transitions_passes_through(self) -> None:
        effective, vetoed = apply_transition_guard("conversation:steps.booking", ["conversation:steps.booking"])
        assert effective == "conversation:steps.booking"
        assert vetoed is None

    def test_target_outside_allowed_transitions_is_vetoed(self) -> None:
        effective, vetoed = apply_transition_guard(
            "conversation:steps.journey_operativo", ["conversation:steps.registro_estado"]
        )
        assert effective is None
        assert vetoed == "conversation:steps.journey_operativo"

    def test_no_target_is_a_noop(self) -> None:
        assert apply_transition_guard(None, ["conversation:steps.booking"]) == (None, None)

    def test_empty_allowed_transitions_vetoes_any_target(self) -> None:
        effective, vetoed = apply_transition_guard("conversation:steps.booking", [])
        assert effective is None
        assert vetoed == "conversation:steps.booking"


def test_decide_vetoes_step_target_outside_allowed_transitions_and_records_it() -> None:
    """Reproduce el bug 2 medido: el modelo elige un step fuera de grafo -- la
    guardia de CODIGO (no el prompt) lo descarta y lo deja explicito."""
    decision = OrchestratorDecision(
        kind="nl",
        step_target="conversation:steps.journey_operativo",
        reason="el usuario confirmo, navego a operativo",
    )
    client = _decision_client(decision)
    agent = OrchestratorAgent(client=client, model="gemini-test", step_atoms=STEP_ATOMS)

    result = agent.decide({
        **GROUNDED_CONTEXT,
        "flow_node": "conversation:steps.onboarding",
        "allowed_transitions": ["conversation:steps.registro_estado"],
    })

    assert "flow_target" not in result  # NUNCA se aplica
    assert result["step_target_vetado"] == "conversation:steps.journey_operativo"
    assert result["kind"] == "nl"


def test_decide_applies_step_target_when_within_allowed_transitions() -> None:
    decision = OrchestratorDecision(
        kind="nl", step_target="conversation:steps.booking", reason="el usuario quiere reservar"
    )
    client = _decision_client(decision)
    agent = OrchestratorAgent(client=client, model="gemini-test", step_atoms=STEP_ATOMS)

    result = agent.decide(GROUNDED_CONTEXT)

    assert result["flow_target"] == "conversation:steps.booking"
    assert "step_target_vetado" not in result


@pytest.mark.parametrize("bad_kind", ["nl", "fallback"])
def test_reason_is_required_by_schema(bad_kind: str) -> None:
    with pytest.raises(Exception):
        OrchestratorDecision(kind=bad_kind)  # sin 'reason' -> ValidationError de pydantic
