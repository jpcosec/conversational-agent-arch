from kb_agent.agent import (
    CANONICAL_FALLBACK_RESPONSE,
    build_conversador_system_instruction,
    draft_conversador_response,
)


def test_conversador_emits_canonical_fallback_when_compiled_context_is_empty() -> None:
    compiled_context = {
        "scenario": "biblioteca",
        "question": "¿Qué promociones tienen?",
        "rules": [],
        "domain_facts": [],
        "is_empty": True,
    }

    response = draft_conversador_response(compiled_context)

    assert response == CANONICAL_FALLBACK_RESPONSE
    assert response == "No tengo esa información a mano, la averiguaré."
    assert "promociones" not in response.casefold()



def test_conversador_uses_grounding_when_domain_facts_exist() -> None:
    compiled_context = {
        "scenario": "pizza",
        "question": "¿Cuál es el horario y cuánto cuesta la margarita?",
        "rules": [
            {
                "id": "rule-pizza-respuesta-breve",
                "body": "Responde solo con información confirmada del local.",
            }
        ],
        "domain_facts": [
            {"id": "domain-pizza-horarios", "body": "Atendemos de 12:00 a 23:00."},
            {"id": "domain-pizza-menu", "body": "La pizza margarita cuesta 10."},
        ],
        "is_empty": False,
    }

    response = draft_conversador_response(compiled_context)

    assert response != CANONICAL_FALLBACK_RESPONSE
    assert "Responde solo con información confirmada del local." in response
    assert "Atendemos de 12:00 a 23:00." in response
    assert "La pizza margarita cuesta 10." in response



def test_conversador_system_prompt_forbids_answering_outside_rules_and_domain_facts() -> None:
    prompt = build_conversador_system_instruction()

    assert "Está PROHIBIDO responder con conocimiento paramétrico" in prompt
    assert "SOLO puedes usar los `domain_facts` y `rules`" in prompt
    assert CANONICAL_FALLBACK_RESPONSE in prompt
