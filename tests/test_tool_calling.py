from __future__ import annotations

from kb_agent.agent import build_function_declarations, draft_conversador_response


def test_conversador_emits_structured_function_call_when_tool_is_relevant() -> None:
    compiled_context = {
        "scenario": "calendar",
        "question": "reserva mañana",
        "rules": [],
        "domain_facts": [],
        "tools": [
            {
                "id": "atom-tool-calendar",
                "json_schema": {
                    "type": "object",
                    "description": "Reserva citas en el calendario.",
                    "properties": {
                        "date": {"type": "string"},
                    },
                    "required": ["date"],
                },
            }
        ],
        "is_empty": True,
    }

    declarations = build_function_declarations(compiled_context)
    response = draft_conversador_response(compiled_context)

    assert declarations == [
        {
            "name": "atom-tool-calendar",
            "description": "Reserva citas en el calendario.",
            "parameters": {
                "type": "object",
                "description": "Reserva citas en el calendario.",
                "properties": {"date": {"type": "string"}},
                "required": ["date"],
            },
        }
    ]
    assert isinstance(response, dict)
    assert response == {
        "function_call": {
            "name": "atom-tool-calendar",
            "args": {"date": "mañana"},
        }
    }


def test_conversador_asks_for_missing_required_arg_instead_of_emitting_function_call() -> None:
    compiled_context = {
        "scenario": "calendar",
        "question": "reserva",
        "rules": [],
        "domain_facts": [],
        "tools": [
            {
                "id": "atom-tool-calendar",
                "json_schema": {
                    "type": "object",
                    "description": "Reserva citas en el calendario.",
                    "properties": {
                        "date": {"type": "string"},
                    },
                    "required": ["date"],
                },
            }
        ],
        "is_empty": True,
    }

    response = draft_conversador_response(compiled_context)

    assert isinstance(response, str)
    assert response == "¿Qué fecha necesitas?"
    assert "function_call" not in response



def test_conversador_extracts_integer_time_and_name_for_real_reservation_schema() -> None:
    compiled_context = {
        "scenario": "calendar",
        "question": "Quiero reservar mesa para 4 personas el viernes a las 20:00 a nombre de Rojas",
        "rules": [],
        "domain_facts": [],
        "tools": [
            {
                "id": "crear_reserva",
                "json_schema": {
                    "type": "object",
                    "description": "Crea una reserva de mesa.",
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
        "is_empty": True,
    }

    response = draft_conversador_response(compiled_context)

    assert response == {
        "function_call": {
            "name": "crear_reserva",
            "args": {
                "fecha": "viernes",
                "hora": "20:00",
                "personas": 4,
                "nombre": "Rojas",
            },
        }
    }
    assert isinstance(response["function_call"]["args"]["personas"], int)


def test_nested_kb_toolatom_schema_extracts_args():
    """Regression: ToolAtom del KB viene con schema anidado bajo 'parameters'.

    Bug real detectado en la corrida E2E Don Peppe: build_function_declarations
    dejaba parameters={parameters:{...}} (doble anidado) y _extract_function_args
    devolvia args={}. Este test usa el FORMATO REAL del KB.
    """
    from kb_agent.agent import draft_conversador_response

    compiled = {
        "question": "Quiero reservar mesa para 4 personas el viernes a las 20:00 a nombre de Rojas",
        "is_empty": False,
        "rules": [],
        "domain_facts": [],
        "tools": [
            {
                "id": "crear_reserva",
                "body": "Crea una reserva",
                "json_schema": {
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
                },
            }
        ],
    }
    result = draft_conversador_response(compiled)
    assert isinstance(result, dict) and "function_call" in result
    fc = result["function_call"]
    assert fc["name"] == "crear_reserva"
    assert fc["args"]["personas"] == 4
    assert fc["args"]["hora"] == "20:00"
