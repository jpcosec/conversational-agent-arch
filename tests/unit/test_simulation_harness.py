"""El harness de simulacion (usuario simulado, runner, juez) probado sin red.

Usa ``ScriptedJsonLLM`` y el orquestador con LLM fake: valida la mecanica del
bucle (fin por objetivo / por max_turns, mensaje inicial fijo, persistencia de
la transcripcion, relleno de criterios que el juez omite) antes de gastar
llamadas reales.
"""
from __future__ import annotations

import json
from pathlib import Path

from tests.e2e.simulation.judge import Criterion, CriterionVerdict, Judge, Verdict, build_judge_prompt
from tests.e2e.simulation.kb_truth import kb_truth_text
from tests.e2e.simulation.llm import ScriptedJsonLLM
from tests.e2e.simulation.runner import run_conversation
from tests.e2e.simulation.scenarios import ALL_SCENARIOS, mentions_any, no_tool_calls, tool_executed
from tests.e2e.simulation.simulated_user import Persona, SimulatedUser, UserMove, build_user_prompt
from tests.support.fakes import offline_orchestrator


def _scripted_user(messages: list[str]) -> ScriptedJsonLLM:
    queue = list(messages)

    def responder(prompt: str, schema):
        if schema is UserMove:
            if queue:
                return UserMove(done=False, reason="sigo", message=queue.pop(0))
            return UserMove(done=True, reason="objetivo cumplido", message="")
        raise AssertionError(f"schema inesperado {schema}")

    return ScriptedJsonLLM(responder)


def test_conversation_ends_when_user_is_done_and_records_runtime_state(donpeppe_kb: Path, tmp_path: Path) -> None:
    orch = offline_orchestrator(donpeppe_kb)
    llm = _scripted_user(["que pizzas tienen?", "soy vegetariano"])
    persona = Persona(name="X", description="d", goal="g")
    t = run_conversation(orch, SimulatedUser(llm, persona), scenario_id="s", external_id="sim:s", max_turns=5)

    assert t.ended_by == "user_done" and t.end_reason == "objetivo cumplido"
    assert [x["user"] for x in t.turns] == ["que pizzas tienen?", "soy vegetariano"]
    assert t.kinds == ["nl", "nl"]
    assert t.turns[1]["traits_after"] == ["trait-vegetariano"]
    # el prompt del usuario simulado incluye persona, objetivo y la conversacion previa
    assert "TU OBJETIVO: g" in llm.prompts[0] and "aun no empieza" in llm.prompts[0]
    assert "ASISTENTE: [nl]" in llm.prompts[1]

    saved = t.save(tmp_path / "t.json")
    payload = json.loads(saved.read_text(encoding="utf-8"))
    assert payload["scenario_id"] == "s" and len(payload["turns"]) == 2
    assert "[1] USER > que pizzas tienen?" in t.pretty()
    no_tool_calls(t, orch)
    mentions_any("margherita")(t, orch)
    orch.close()


def test_conversation_stops_at_max_turns(donpeppe_kb: Path) -> None:
    orch = offline_orchestrator(donpeppe_kb)
    t = run_conversation(orch, SimulatedUser(_scripted_user(["a", "b", "c", "d"]), Persona("X", "d", "g")), scenario_id="s", external_id="sim:s", max_turns=2)
    assert t.ended_by == "max_turns" and len(t.turns) == 2
    orch.close()


def test_opening_message_skips_llm_and_tool_checks_work(donpeppe_kb: Path) -> None:
    from kb_agent.tools import load_tool_handlers

    orch = offline_orchestrator(donpeppe_kb, tool_handlers=load_tool_handlers({"crear_reserva": "kb_agent.tools.reservas:crear_reserva"}))
    llm = _scripted_user([])
    persona = Persona("R", "d", "g", opening_message="reservar mesa para 4 el viernes a las 20:00 a nombre de Rojas")
    t = run_conversation(orch, SimulatedUser(llm, persona), scenario_id="s", external_id="sim:s", max_turns=3)
    assert len(llm.prompts) == 1  # solo la decision de terminar; el primer mensaje fue fijo
    tool_executed("crear_reserva", personas=4)(t, orch)
    orch.close()


def test_judge_prompt_and_missing_criteria_are_marked_failed(donpeppe_kb: Path) -> None:
    truth = kb_truth_text(donpeppe_kb)
    assert "Margherita 8900" in truth and "LIMITES:" in truth and "crear_reserva" in truth

    def responder(prompt, schema):
        assert schema is Verdict
        assert "BASE DE CONOCIMIENTO DEL ASISTENTE" in prompt and "[1] USUARIO: hola" in prompt
        return Verdict(criteria=[CriterionVerdict(id="a", passed=True, evidence="ok")], summary="bien")

    judge = Judge(ScriptedJsonLLM(responder), truth)
    verdict = judge.evaluate([{"user": "hola", "assistant": "hola!", "kind": "nl"}], [Criterion("a", "x"), Criterion("b", "y")])
    assert not verdict.passed and [c.id for c in verdict.failed] == ["b"]


def test_scenarios_are_well_formed() -> None:
    ids = [s.id for s in ALL_SCENARIOS]
    assert len(ids) == len(set(ids))
    for s in ALL_SCENARIOS:
        assert s.kb in {"donpeppe", "antonia"} and s.criteria and s.checks and s.max_turns >= 2
        assert isinstance(s.handlers(), dict)
        assert "TU OBJETIVO" in build_user_prompt(s.persona, [])
        assert build_judge_prompt("kb", [], list(s.criteria))
