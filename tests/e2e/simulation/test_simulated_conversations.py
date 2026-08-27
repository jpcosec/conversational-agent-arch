"""Prueba el agente conversacional CON un agente conversacional.

Por escenario:
  1. un usuario simulado (LLM con persona/objetivo) conversa con el orquestador REAL
     (Gemini + SLDB + SQL + tools) hasta cumplir su objetivo o agotar turnos;
  2. checks deterministas sobre el runtime (tools ejecutadas, filas en SQL,
     traits aprendidos, ausencia de tool_call/fallback, largo de respuestas);
  3. un juez LLM evalua la transcripcion contra la KB compilada (alucinaciones,
     limites, adecuacion).

La transcripcion completa se guarda en runs/simulation/<escenario>.json y se
imprime en el mensaje de fallo. Escenarios con ``known_gap`` son xfail estricto
(salvo ``known_gap_strict=False``, para gaps cuyo resultado varia con el LLM).

Correr:  pytest tests/e2e/simulation -m simulation   (o -k donpeppe / -k antonia)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from kb_agent.orchestrator import Orchestrator
from kb_agent.project_config import load_project_config
from tests.conftest import ANTONIA_KB, DONPEPPE_KB

from .judge import Judge
from .kb_truth import kb_truth_text
from .runner import run_conversation
from .scenarios import ALL_SCENARIOS, Scenario
from .simulated_user import SimulatedUser

pytestmark = [pytest.mark.llm, pytest.mark.simulation]

KB_ROOTS = {"donpeppe": DONPEPPE_KB, "antonia": ANTONIA_KB}


def _params() -> list:
    params = []
    for s in ALL_SCENARIOS:
        marks = []
        if s.known_gap:
            reason = f"known_gap: {s.known_gap}"
            if not s.known_gap_strict:
                reason += f" [no estricto: {s.known_gap_variance}]"
            marks = [pytest.mark.known_gap, pytest.mark.xfail(strict=s.known_gap_strict, reason=reason)]
        params.append(pytest.param(s, id=s.id, marks=marks))
    return params


@pytest.fixture(scope="module")
def kb_truths() -> dict[str, str]:
    return {name: kb_truth_text(root) for name, root in KB_ROOTS.items()}


@pytest.mark.parametrize("scenario", _params())
def test_simulated_conversation(scenario: Scenario, gemini_client, json_llm, kb_truths: dict[str, str], sim_reports_dir: Path, tmp_path: Path) -> None:
    kb_root = KB_ROOTS[scenario.kb]
    cfg = load_project_config(mode="test")
    orch = Orchestrator(
        kb_root=kb_root,
        db_url=f"sqlite:///{tmp_path / 'sim.sqlite'}",
        model=cfg.model,
        client=gemini_client,
        tool_handlers=scenario.handlers(),
    )
    try:
        transcript = run_conversation(
            orch,
            SimulatedUser(json_llm, scenario.persona),
            scenario_id=scenario.id,
            external_id=f"sim:{scenario.id}",
            max_turns=scenario.max_turns,
        )
        report = transcript.save(sim_reports_dir / f"{scenario.id}.json")

        failures: list[str] = []
        for check in scenario.checks:
            try:
                check(transcript, orch)
            except AssertionError as exc:
                failures.append(f"check {getattr(check, '__name__', check)}: {exc}")

        verdict = Judge(json_llm, kb_truths[scenario.kb]).evaluate(transcript.for_llm(), list(scenario.criteria))
        failures.extend(f"juez[{c.id}]: {c.evidence}" for c in verdict.failed)

        assert transcript.turns, "el usuario simulado no envio ningun mensaje"
        assert not failures, (
            "\n".join(failures)
            + f"\n\n{transcript.pretty()}\n\njuez: {verdict.summary}\nreporte: {report}"
        )
    finally:
        orch.close()
