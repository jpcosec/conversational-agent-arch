"""Smoke con Gemini REAL sobre el negocio de project.config.yaml (KB de prueba).

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
    turn = orch.handle_turn(external_id="live:horario", message="¿A qué hora abren el sábado?")
    assert turn["kind"] == "nl"
    assert "19" in turn["reply"], turn["reply"]  # Don Peppe abre 19:00 (dato del atom horarios)
    assert "atom-donpeppe-horarios" in turn["context"]["atom_ids"]


def test_profiler_learns_trait_from_natural_language(orch: Orchestrator) -> None:
    first = orch.handle_turn(external_id="live:perfil", message="Hola, soy vegetariano, ¿qué me recomiendan?")
    assert "trait-vegetariano" in first["traits_after"], first
    second = orch.handle_turn(external_id="live:perfil", message="¿Y cuál conviene para el martes?")
    assert second["used_traits_in_context"] == ["trait-vegetariano"]
    assert second["kind"] == "nl"
