"""Puertos LLM: el prompt del Conversador se arma SOLO desde el contexto compilado."""
from __future__ import annotations

from kb_agent.llm import GeminiConversador, GeminiTraitMapper, build_nl_prompt, parse_trait_json
from kb_agent.perfilador.extractor import TraitCandidate


class _Resp:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeClient:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[dict] = []

        class _Models:
            def generate_content(inner, **kw):
                self.calls.append(kw)
                return _Resp(self.text)

        self.models = _Models()


def test_nl_prompt_uses_kb_persona_strategy_grounding_and_traits() -> None:
    prompt = build_nl_prompt({
        "question": "¿Qué me recomiendan?",
        "persona": {"whoami": "Soy el asistente de X.", "estilo": "Breve.", "limites": "No invento."},
        "strategy": "Primero responder.",
        "domain_facts": [{"id": "a", "body": "Margherita 8900."}],
        "rules": [{"id": "r", "body": "Reservas con 1 dia de anticipacion."}],
        "user_traits": [{
            "trait_id": "trait-vegetariano",
            "title": "Cliente vegetariano",
            "description": "No consume carne.",
            "category": "dietary",
            "confidence": 0.9,
            "source": "test",
        }],
    })
    for fragment in ("Soy el asistente de X.", "Estilo: Breve.", "Limites: No invento.", "Estrategia: Primero responder.",
                     "- Margherita 8900.", "- Reservas con 1 dia de anticipacion.",
                     "PERFIL DEL CLIENTE (traits): Cliente vegetariano (No consume carne.)",
                     "PREGUNTA: ¿Qué me recomiendan?"):
        assert fragment in prompt
    assert "RESULTADO DE TOOL" not in prompt


def test_nl_prompt_includes_tool_result_when_system_turn_present() -> None:
    prompt = build_nl_prompt({"question": "reserva", "system_turn": {"role": "system", "content": '{"reserva_id": 1}'}})
    assert 'RESULTADO DE TOOL (System Turn JSON crudo):\n{"reserva_id": 1}' in prompt


def test_nl_prompt_falls_back_to_generic_identity_only_without_persona() -> None:
    prompt = build_nl_prompt({"question": "hola"})
    assert prompt.startswith("Eres un asistente.")


def test_nl_prompt_includes_history_separated_from_context_and_question() -> None:
    prompt = build_nl_prompt({
        "question": "¿y ahora que sigue?",
        "domain_facts": [{"id": "a", "body": "Margherita 8900."}],
        "history": [
            {"role": "user", "content": "hola"},
            {"role": "assistant", "content": "¡Hola! ¿En que te ayudo?"},
        ],
    })
    assert "CONVERSACION PREVIA" in prompt
    assert "- user: hola" in prompt
    assert "- assistant: ¡Hola! ¿En que te ayudo?" in prompt
    # el historial va ANTES de la pregunta actual, y la pregunta actual no se duplica ahi
    assert prompt.index("CONVERSACION PREVIA") < prompt.index("PREGUNTA: ¿y ahora que sigue?")


def test_nl_prompt_omits_history_block_when_absent_or_empty() -> None:
    assert "CONVERSACION PREVIA" not in build_nl_prompt({"question": "hola"})
    assert "CONVERSACION PREVIA" not in build_nl_prompt({"question": "hola", "history": []})


def test_nl_prompt_history_does_not_duplicate_the_just_appended_system_turn() -> None:
    # RouterStateMachine._resume_from_waiting_tool anexa el system_turn (resultado
    # de la tool) al final de ``history`` antes de redactar; build_nl_prompt ya lo
    # muestra aparte en RESULTADO DE TOOL, no debe repetirlo en CONVERSACION PREVIA.
    system_turn = {"role": "system", "content": '{"reserva_id": 1}'}
    prompt = build_nl_prompt({
        "question": "confirmame la reserva",
        "system_turn": system_turn,
        "history": [{"role": "user", "content": "hola"}, system_turn],
    })
    assert prompt.count('{"reserva_id": 1}') == 1
    assert "- user: hola" in prompt


def test_parse_trait_json_is_robust() -> None:
    assert parse_trait_json('```json\n[{"trait_id": "t", "confidence": 0.9}]\n```') == [{"trait_id": "t", "confidence": 0.9}]
    assert parse_trait_json("sin json") == []
    assert parse_trait_json("[no valido") == []
    assert parse_trait_json("") == []


def test_gemini_ports_send_configured_model() -> None:
    client = _FakeClient('[{"trait_id": "trait-x", "confidence": 0.8}]')
    assert GeminiConversador(client, "modelo-a").draft_nl({"question": "q"}) == '[{"trait_id": "trait-x", "confidence": 0.8}]'
    assert GeminiTraitMapper(client, "modelo-b").extract_traits(turn_text="t", candidates=[TraitCandidate("trait-x", "x")], instructions="") == [{"trait_id": "trait-x", "confidence": 0.8}]
    assert [c["model"] for c in client.calls] == ["modelo-a", "modelo-b"]
