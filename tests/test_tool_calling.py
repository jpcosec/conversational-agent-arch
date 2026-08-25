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
