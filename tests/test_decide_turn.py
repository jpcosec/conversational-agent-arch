"""Policy pura de decision del tipo de turno (brecha #1).

decide_turn separa DECIDIR de REDACTAR: es deterministica, no llama a Gemini,
y solo devuelve que clase de turno corresponde. El orquestador la invoca para
conducir la accion (ejecutar tool / usar conversation:fallback / draft_nl).
"""
from kb_agent.agent import decide_turn


def test_decide_turn_fallback_when_empty() -> None:
    decision = decide_turn(
        {
            "question": "¿Qué promociones tienen?",
            "rules": [],
            "domain_facts": [],
            "is_empty": True,
        }
    )
    assert decision == {"kind": "fallback"}


def test_decide_turn_fallback_when_no_grounding() -> None:
    decision = decide_turn(
        {
            "question": "algo random",
            "rules": [],
            "domain_facts": [],
            "is_empty": False,
        }
    )
    assert decision == {"kind": "fallback"}


def test_decide_turn_nl_when_grounding_exists() -> None:
    decision = decide_turn(
        {
            "question": "¿Cuál es el horario?",
            "rules": [],
            "domain_facts": [{"id": "domain-horarios", "body": "12:00 a 23:00."}],
            "is_empty": False,
        }
    )
    assert decision == {"kind": "nl"}


def test_decide_turn_tool_call_when_intent_and_args_complete() -> None:
    decision = decide_turn(
        {
            "question": "quiero reservar mesa el 2026-09-10 a las 20:00 para 4 a nombre de Ana",
            "rules": [],
            "domain_facts": [{"id": "d", "body": "x"}],
            "is_empty": False,
            "tools": [
                {
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
            ],
        }
    )
    assert decision["kind"] == "tool_call"
    assert decision["function_call"]["name"] == "crear_reserva"
    args = decision["function_call"]["args"]
    assert args["fecha"] == "2026-09-10"
    assert args["hora"] == "20:00"
    assert isinstance(args["personas"], int)


def test_decide_turn_nl_when_tool_intent_but_args_incomplete() -> None:
    # Intencion de reserva pero faltan datos: no es tool_call; el conversador
    # debera pedir los datos (kind=nl), no fallback.
    decision = decide_turn(
        {
            "question": "quiero reservar una mesa",
            "rules": [],
            "domain_facts": [{"id": "d", "body": "x"}],
            "is_empty": False,
            "tools": [
                {
                    "name": "crear_reserva",
                    "parameters": {
                        "type": "object",
                        "properties": {"fecha": {"type": "string"}},
                        "required": ["fecha"],
                    },
                }
            ],
        }
    )
    assert decision["kind"] == "nl"
