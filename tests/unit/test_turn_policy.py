"""Policy pura de turno (``kb_agent.agent``): decide sin LLM, no redacta.

Cubre las tres salidas de ``decide_turn`` y la normalizacion de ToolAtoms a
function_declarations (forma plana, anidada y ``json_schema``).
"""
from __future__ import annotations

import pytest

from kb_agent.agent import DEFAULT_FALLBACK_MESSAGE, build_function_declarations, decide_turn

RESERVA_TOOL = {
    "name": "crear_reserva",
    "parameters": {
        "type": "object",
        "properties": {
            "fecha": {"type": "string"},
            "hora": {"type": "string"},
            "personas": {"type": "integer"},
            "nombre": {"type": "string"},
        },
        "required": ["fecha", "hora", "personas"],
    },
}
GROUNDED = {"rules": [], "domain_facts": [{"id": "d", "body": "x"}], "is_empty": False}


def test_fallback_when_context_is_empty() -> None:
    assert decide_turn({"question": "¿Qué promociones tienen?", "rules": [], "domain_facts": [], "is_empty": True}) == {"kind": "fallback"}


def test_fallback_when_no_grounding_even_if_not_flagged_empty() -> None:
    assert decide_turn({"question": "algo", "rules": [], "domain_facts": [], "is_empty": False}) == {"kind": "fallback"}


def test_nl_when_grounding_exists() -> None:
    assert decide_turn({"question": "¿Cuál es el horario?", **GROUNDED}) == {"kind": "nl"}


def test_nl_when_tools_exist_but_no_tool_intent() -> None:
    decision = decide_turn({"question": "¿cuánto cuesta la margherita?", "tools": [RESERVA_TOOL], **GROUNDED})
    assert decision == {"kind": "nl"}


def test_tool_call_when_intent_and_required_args_complete() -> None:
    decision = decide_turn({
        "question": "quiero reservar mesa el 2026-09-10 a las 20:00 para 4 a nombre de Ana",
        "tools": [RESERVA_TOOL],
        **GROUNDED,
    })
    assert decision["kind"] == "tool_call"
    assert decision["function_call"] == {
        "name": "crear_reserva",
        "args": {"fecha": "2026-09-10", "hora": "20:00", "personas": 4, "nombre": "Ana"},
    }
    assert isinstance(decision["function_call"]["args"]["personas"], int)


def test_weekday_time_and_name_extraction_from_natural_phrase() -> None:
    decision = decide_turn({
        "question": "Quiero reservar mesa para 4 personas el viernes a las 20:00 a nombre de Rojas",
        "tools": [RESERVA_TOOL],
        **GROUNDED,
    })
    assert decision["function_call"]["args"] == {"fecha": "viernes", "hora": "20:00", "personas": 4, "nombre": "Rojas"}


def test_nl_when_tool_intent_but_required_args_incomplete() -> None:
    # Intencion de reserva pero faltan datos: el conversador (nl) debe pedirlos, no fallback.
    decision = decide_turn({"question": "quiero reservar una mesa", "tools": [RESERVA_TOOL], **GROUNDED})
    assert decision == {"kind": "nl"}


def test_tool_call_takes_precedence_over_empty_context() -> None:
    decision = decide_turn({
        "question": "reserva mañana",
        "rules": [], "domain_facts": [], "is_empty": True,
        "tools": [{"id": "atom-tool-calendar", "json_schema": {"type": "object", "properties": {"date": {"type": "string"}}, "required": ["date"]}}],
    })
    assert decision == {"kind": "tool_call", "function_call": {"name": "atom-tool-calendar", "args": {"date": "mañana"}}}


def test_dia_and_hora_args_support_reminder_tools() -> None:
    """Tools con argumento ``dia`` (KB Antonia: agendar_recordatorio)."""
    tool = {"name": "agendar_recordatorio", "parameters": {"type": "object", "properties": {"dia": {"type": "string"}, "hora": {"type": "string"}, "nombre": {"type": "string"}}, "required": ["dia", "hora"]}}
    decision = decide_turn({"question": "quiero agendar un recordatorio los martes a las 9:00", "tools": [tool], **GROUNDED})
    assert decision["kind"] == "tool_call"
    assert decision["function_call"]["args"] == {"dia": "martes", "hora": "9:00"}


@pytest.mark.parametrize(
    "raw_tool",
    [
        pytest.param({"name": "crear_reserva", "parameters": RESERVA_TOOL["parameters"]}, id="nested-kb-form"),
        pytest.param({"id": "crear_reserva", "body": "Crea una reserva", "json_schema": {"name": "crear_reserva", "parameters": RESERVA_TOOL["parameters"]}}, id="json_schema-nested"),
        pytest.param({"id": "crear_reserva", "json_schema": {"type": "object", "description": "Crea una reserva.", **RESERVA_TOOL["parameters"]}}, id="json_schema-flat"),
    ],
)
def test_function_declarations_normalize_all_toolatom_shapes(raw_tool: dict) -> None:
    [declaration] = build_function_declarations({"tools": [raw_tool]})
    assert declaration["name"] == "crear_reserva"
    assert set(declaration["parameters"]["properties"]) == {"fecha", "hora", "personas", "nombre"}
    assert declaration["parameters"]["required"] == ["fecha", "hora", "personas"]
    # regresion: el schema anidado no debe quedar doblemente anidado
    assert "parameters" not in declaration["parameters"]


def test_function_declarations_ignore_garbage() -> None:
    assert build_function_declarations(None) == []
    assert build_function_declarations({"tools": "no-es-lista"}) == []
    assert build_function_declarations({"tools": [None, 3, {"sin": "nombre"}]}) == []


def test_default_fallback_message_is_a_last_resort_constant() -> None:
    assert isinstance(DEFAULT_FALLBACK_MESSAGE, str) and DEFAULT_FALLBACK_MESSAGE
