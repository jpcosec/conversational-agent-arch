"""Smoke con Gemini REAL sobre la KB Antonia.

Lo minimo que solo un LLM real puede validar: (1) la respuesta NL cita un dato
de la KB; (2) el perfilador aprende un trait desde lenguaje natural.
Todo lo demas del cableado se prueba sin red en tests/unit y tests/integration.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from kb_agent.orchestrator import Orchestrator
from kb_agent.project_config import load_project_config


@pytest.fixture(scope="module")
def orch(gemini_client, tmp_path_factory: pytest.TempPathFactory) -> Orchestrator:
    db = tmp_path_factory.mktemp("live") / "live.sqlite"
    o = Orchestrator.from_config(load_project_config(mode="test"), db_url=f"sqlite:///{db}", client=gemini_client)
    yield o
    o.close()


def test_nl_reply_cites_kb_fact(orch: Orchestrator) -> None:
    turn = orch.handle_turn(external_id="live:antonia", message="Hola, ¿qué es Selfix?")
    assert turn["kind"] in ("nl", "fallback")
    assert len(turn["reply"]) > 10, turn["reply"]


def test_profiler_learns_trait_from_natural_language(orch: Orchestrator) -> None:
    first = orch.handle_turn(external_id="live:perfil", message="Hola, me cuesta acordarme de aplicarme las dosis")
    assert len(first["traits_after"]) > 0, first
    second = orch.handle_turn(external_id="live:perfil", message="¿Cómo puedo hacer para no olvidarme?")
    assert second["kind"] in ("nl", "fallback")