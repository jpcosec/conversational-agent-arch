"""Tests de ``kb_agent.agents.gate.GateAgent`` (fase 2.3), todos sin red.

Cubre: el pre-filtro deterministico (afirmar una accion no ejecutada, sin
gastar una llamada al LLM), sus limites documentados (no dispara ante una
oferta), el contrato de ``evaluate`` con un juez LLM fake (aprueba/rechaza),
y el test mas importante: que la KB gobierna de verdad el
``static_instruction`` del agente -- agregar un ``GateCriterion`` lo cambia,
sin tocar codigo.
"""
from __future__ import annotations

from typing import Any

import pytest

from kb_agent.agents.gate import (
    GateAgent,
    GateVerdict,
    PREFILTER_CRITERION_ID,
    render_gate_criteria,
    response_claims_completed_action,
)

GATE_ATOMS = [
    {
        "id": "gate-antonia-dosis",
        "title": "Gate regulatorio — dosis",
        "criterion": "La respuesta redactada no indica, sugiere ni comenta cambios de dosis.",
        "approval_condition": "Aprueba cuando la respuesta evita por completo instrucciones sobre dosis.",
        "rejection_action": "Rechazar y encolar a revision humana.",
    },
    {
        "id": "gate-antonia-diagnostico",
        "title": "Gate regulatorio — diagnóstico",
        "criterion": "La respuesta redactada no diagnostica ni interpreta sintomas.",
        "approval_condition": "Aprueba cuando la respuesta se limita a acompañar y derivar.",
        "rejection_action": "Rechazar y encolar a revision humana.",
    },
]


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
    """Cliente fake; si no se le da ``responder``, FALLA si se lo llama.

    Por defecto lanza ``AssertionError`` -- se usa para probar que el
    pre-filtro corta ANTES de llamar al modelo (fase 2.3, item 2 del pedido).
    """

    def __init__(self, responder=None) -> None:
        if responder is None:
            def responder(_kwargs: dict[str, Any]) -> _Resp:
                raise AssertionError("el modelo NO deberia haberse llamado (pre-filtro debio cortar)")
        self.models = _FakeModels(responder)

    @property
    def calls(self) -> list[dict[str, Any]]:
        return self.models.calls


def _verdict_client(verdict: GateVerdict) -> _FakeClient:
    return _FakeClient(responder=lambda _kw: _Resp(text=verdict.model_dump_json(), parsed=verdict))


# ── pre-filtro: afirma accion + tool_called=False -> rechazo sin llamar al LLM ──
@pytest.mark.parametrize(
    "response",
    [
        "¡Listo! Te agendé el recordatorio para tu aplicación semanal, todos los lunes a las 9 AM.",
        "Ya quedó agendado tu turno para el viernes.",
        "Listo, programé tu recordatorio de las 8pm.",
        "Registré tu cambio de horario, no te preocupes más por eso.",
    ],
)
def test_prefilter_rejects_claimed_action_without_tool_call(response: str) -> None:
    client = _FakeClient()  # lanza si se llama al modelo
    gate = GateAgent(client=client, model="gemini-test", gate_atoms=GATE_ATOMS)

    result = gate.evaluate(response, tool_called=False, tool_name="agendar_recordatorio")

    assert result["approved"] is False
    assert result["action"] == "handoff"
    assert result["criterion_ids"] == [PREFILTER_CRITERION_ID]
    assert result["reasons"]
    assert client.calls == []  # el modelo NUNCA se llamo


# ── pre-filtro NO dispara cuando el agente solo OFRECE la accion ────────────
@pytest.mark.parametrize(
    "response",
    [
        "¿Querés que te agende el recordatorio semanal para los lunes a las 9?",
        "Puedo agendarte un recordatorio si quieres, ¿te sirve los lunes?",
        "Si quieres que te agende el turno, decime el horario que prefieras.",
        "¿Te gustaría que programe un recordatorio para tus dosis?",
    ],
)
def test_prefilter_does_not_trigger_on_offer(response: str) -> None:
    approved = GateVerdict(approved=True)
    client = _verdict_client(approved)
    gate = GateAgent(client=client, model="gemini-test", gate_atoms=GATE_ATOMS)

    result = gate.evaluate(response, tool_called=False, tool_name=None)

    # No fue el pre-filtro el que aprobo -- paso al juez LLM (fake, que aprueba).
    assert result["approved"] is True
    assert len(client.calls) == 1


def test_response_claims_completed_action_helper_matches_only_claims() -> None:
    assert response_claims_completed_action("Listo, te agendé el turno del lunes.") is True
    assert response_claims_completed_action("Quedó confirmado tu recordatorio.") is True
    assert response_claims_completed_action("¿Querés que te agende el turno?") is False
    assert response_claims_completed_action("Puedo reservarte una hora si quieres.") is False
    assert response_claims_completed_action("Hola, ¿en qué te puedo ayudar hoy?") is False


# ── respuesta limpia + juez fake que aprueba -> approved=True ───────────────
def test_clean_response_with_tool_called_uses_llm_judge_and_approves() -> None:
    verdict = GateVerdict(approved=True, reasons=[], action="pass", criterion_ids=[])
    client = _verdict_client(verdict)
    gate = GateAgent(client=client, model="gemini-test", gate_atoms=GATE_ATOMS)

    result = gate.evaluate(
        "Quedó agendado tu recordatorio semanal, gracias por avisarme.",
        tool_called=True,
        tool_name="agendar_recordatorio",
    )

    assert result == {"approved": True, "reasons": [], "action": "pass", "criterion_ids": []}
    assert len(client.calls) == 1
    system_instruction = client.calls[0]["config"]["system_instruction"]
    assert "gate-antonia-dosis" in system_instruction


# ── juez fake que rechaza -> approved=False con reasons y criterion_ids ─────
def test_llm_judge_rejects_with_reasons_and_criterion_ids() -> None:
    verdict = GateVerdict(
        approved=False,
        reasons=["La respuesta sugiere subir la dosis, viola gate-antonia-dosis."],
        action="handoff",
        criterion_ids=["gate-antonia-dosis"],
    )
    client = _verdict_client(verdict)
    gate = GateAgent(client=client, model="gemini-test", gate_atoms=GATE_ATOMS)

    result = gate.evaluate(
        "Puedes subir la dosis un poco si sientes que no hace efecto.",
        tool_called=False,
        tool_name=None,
    )

    assert result["approved"] is False
    assert result["reasons"] == ["La respuesta sugiere subir la dosis, viola gate-antonia-dosis."]
    assert result["criterion_ids"] == ["gate-antonia-dosis"]
    assert result["action"] == "handoff"


# ── vacio / sin texto: aprueba trivialmente sin llamar al modelo ────────────
def test_empty_response_approves_without_calling_model() -> None:
    client = _FakeClient()
    gate = GateAgent(client=client, model="gemini-test", gate_atoms=GATE_ATOMS)

    result = gate.evaluate("   ", tool_called=False)

    assert result == {"approved": True, "reasons": [], "action": "pass", "criterion_ids": []}
    assert client.calls == []


# ── sin criterios en la KB: aprueba sin llamar al modelo ────────────────────
def test_no_gate_criteria_approves_without_calling_model() -> None:
    client = _FakeClient()
    gate = GateAgent(client=client, model="gemini-test", gate_atoms=[])

    result = gate.evaluate("Hola, ¿en qué te ayudo hoy?", tool_called=False)

    assert result == {"approved": True, "reasons": [], "action": "pass", "criterion_ids": []}
    assert client.calls == []


# ── evaluate propaga si el LLM lanza (el fail-open vive en Orchestrator) ────
def test_evaluate_propagates_llm_exception() -> None:
    def boom(_kwargs: dict[str, Any]) -> _Resp:
        raise RuntimeError("modelo no disponible")

    client = _FakeClient(responder=boom)
    gate = GateAgent(client=client, model="gemini-test", gate_atoms=GATE_ATOMS)

    with pytest.raises(RuntimeError):
        gate.evaluate("Todo bien, ¿cómo te sientes hoy?", tool_called=True)


# ── gobernanza por KB: agregar un GateCriterion cambia el static_instruction ─
def test_new_gate_criterion_changes_static_instruction() -> None:
    """El test mas importante: prueba que la KB dejo de ser decorativa.

    Antes (heuristicas hardcodeadas por atom_id), agregar un GateCriterion
    nuevo a la KB NO cambiaba el comportamiento del gate salvo que su id
    contuviera una palabra que el codigo ya reconocia. Aca, agregar un atom
    a la lista que arma ``static_instruction`` lo cambia siempre: es el
    prompt completo del juez, no un lookup por id.
    """
    client_a = _FakeClient()
    client_b = _FakeClient()
    baseline = GateAgent(client=client_a, model="gemini-test", gate_atoms=GATE_ATOMS)

    new_atom = {
        "id": "gate-antonia-nuevo-criterio",
        "title": "Gate regulatorio — nuevo criterio",
        "criterion": "La respuesta redactada no revela datos de otros pacientes.",
        "approval_condition": "Aprueba cuando la respuesta solo habla del paciente actual.",
        "rejection_action": "Rechazar y encolar a revision humana.",
    }
    extended = GateAgent(client=client_b, model="gemini-test", gate_atoms=[*GATE_ATOMS, new_atom])

    assert baseline.static_instruction != extended.static_instruction
    assert "gate-antonia-nuevo-criterio" not in baseline.static_instruction
    assert "gate-antonia-nuevo-criterio" in extended.static_instruction
    assert "no revela datos de otros pacientes" in extended.static_instruction

    # Y el rendering standalone (usado por GateAgent.__init__) es la misma fuente:
    assert render_gate_criteria(GATE_ATOMS) == baseline.static_instruction
    assert render_gate_criteria([*GATE_ATOMS, new_atom]) == extended.static_instruction
