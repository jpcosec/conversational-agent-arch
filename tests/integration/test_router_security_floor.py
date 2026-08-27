"""Piso de seguridad y fallback deterministico del ruteador de contexto (fase
2.2), contra la KB REAL (``knowledge/``, fixture ``antonia_kb``).

Dos garantias no negociables del plan:
  1. Las 6 ``RuleAtom conversation:security`` (farmacovigilancia) entran al
     bundle SIEMPRE, decida lo que decida el ``RouterAgent`` -- incluso si
     devuelve un bundle vacio. Se prueba con ``FakeRouterAgent`` (no hay
     LLM real en esta capa de tests, ver ``tests/conftest.py``).
  2. Si el ``RouterAgent`` falla (LLM caido, cuota, lo que sea),
     ``ContextCompiler`` cae al bundle deterministico
     (``ContextCompiler._build_bundle``, sin tocar) y el turno no se rompe.

``ContextCompiler`` se ejercita directamente (sin ``Orchestrator`` completo)
para aislar el comportamiento del bundle; el cableado end-to-end (turno
completo, ``decisions.ruteador.source`` en el rastro) se prueba aparte en
``test_router_agent_orchestrator_wiring`` mas abajo.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from kb_agent.ontologizador.compiler import ContextCompiler
from kb_agent.ontologizador.sldb_reader import SLDBReader
from tests.support.fakes import FakeRouterAgent, offline_orchestrator

SECURITY_RULE_IDS = {
    "rule-antonia-anti-alucinacion",
    "rule-antonia-no-contraindicaciones",
    "rule-antonia-no-deducir",
    "rule-antonia-no-extrapolar",
    "rule-antonia-no-farmacologia",
    "rule-antonia-no-inventar",
}


@pytest.fixture()
def compiler(antonia_kb: Path) -> ContextCompiler:
    return ContextCompiler(reader=SLDBReader(kb_root=antonia_kb))


# ── 1) piso de seguridad: no negociable, aunque el agente no lo pida ─────
def test_security_floor_enters_even_when_agent_returns_empty_bundle(compiler: ContextCompiler) -> None:
    compiler.router_agent = FakeRouterAgent(raises=False)  # el agente "responde" con bundle=[]

    doc = compiler.compile(question="hola, como estas?", user_id=None)

    bundle_ids = {b["doc_id"] for b in doc.bundle}
    assert SECURITY_RULE_IDS <= bundle_ids
    for entry in doc.bundle:
        if entry["doc_id"] in SECURITY_RULE_IDS:
            assert entry["motivo"] == "piso de seguridad"
    assert doc.bundle_source == "agent"  # el agente SI respondio (no lanzo)


def test_security_floor_enters_even_when_agent_bundle_has_no_security_rules(compiler: ContextCompiler) -> None:
    """El agente elige documentos legitimos (sin ninguna regla de seguridad,
    p.ej. porque el modelo solo penso en el trait de ansiedad) -- el piso
    entra IGUAL, ademas de lo que el agente pidio."""

    def bundle_fn(**_kwargs: object) -> list[dict[str, object]]:
        return [{
            "doc_id": "trait-antonia-ansioso-aplicacion",
            "motivo": "el usuario expresa miedo a la aguja",
            "family": "user",
            "score": 0.3955,
        }]

    compiler.router_agent = FakeRouterAgent(bundle_fn)

    doc = compiler.compile(question="me da miedo la aguja, es la primera vez que me inyecto", user_id=None)

    bundle_ids = {b["doc_id"] for b in doc.bundle}
    assert SECURITY_RULE_IDS <= bundle_ids
    assert "trait-antonia-ansioso-aplicacion" in bundle_ids
    trait_entry = next(b for b in doc.bundle if b["doc_id"] == "trait-antonia-ansioso-aplicacion")
    assert trait_entry["motivo"] == "el usuario expresa miedo a la aguja"
    assert doc.bundle_source == "agent"


def test_hallucinated_doc_id_from_agent_is_dropped_but_security_floor_stays(compiler: ContextCompiler) -> None:
    """Un id que el agente devuelve pero que no existe en la KB real no se
    propaga -- se descarta en silencio -- pero el piso de seguridad sigue
    entrando (no depende de lo que el agente haya acertado)."""

    def bundle_fn(**_kwargs: object) -> list[dict[str, object]]:
        return [{"doc_id": "atom-que-no-existe-en-la-kb", "motivo": "inventado", "family": "domain", "score": 0.9}]

    compiler.router_agent = FakeRouterAgent(bundle_fn)

    doc = compiler.compile(question="cualquier cosa", user_id=None)

    bundle_ids = {b["doc_id"] for b in doc.bundle}
    assert "atom-que-no-existe-en-la-kb" not in bundle_ids
    assert SECURITY_RULE_IDS <= bundle_ids


# ── 2) fallback deterministico: si el agente lanza, el turno no se rompe ──
def test_router_agent_failure_falls_back_to_deterministic_bundle(compiler: ContextCompiler) -> None:
    compiler.router_agent = FakeRouterAgent()  # default: .route() lanza (simula "sin LLM")

    doc = compiler.compile(question="me da miedo la aguja, es la primera vez que me inyecto", user_id=None)

    assert doc.bundle_source == "deterministic"
    # el piso de seguridad tambien esta garantizado por el camino determinista
    bundle_ids = {b["doc_id"] for b in doc.bundle}
    assert SECURITY_RULE_IDS <= bundle_ids
    # y el bundle deterministico sigue produciendo grounding real (no vacio)
    assert doc.bundle
    assert doc.is_empty is False


def test_compiling_without_any_router_agent_uses_deterministic_bundle(antonia_kb: Path) -> None:
    """Sin ``router_agent`` inyectado (p.ej. ``ContextCompiler`` standalone,
    como en ``tests/unit/test_context_compiler.py``) el compilador nunca
    intenta llamar a un agente -- va directo al fallback."""
    compiler = ContextCompiler(reader=SLDBReader(kb_root=antonia_kb))

    doc = compiler.compile(question="hola", user_id=None)

    assert doc.bundle_source == "deterministic"
    bundle_ids = {b["doc_id"] for b in doc.bundle}
    assert SECURITY_RULE_IDS <= bundle_ids


# ── cableado end-to-end: el turno completo no se rompe y audita la fuente ─
def test_orchestrator_turn_survives_router_agent_failure_and_traces_source(antonia_kb: Path, tmp_db_url: str) -> None:
    orch = offline_orchestrator(antonia_kb, tmp_db_url, router_agent=FakeRouterAgent())
    try:
        turn = orch.handle_turn(external_id="wa:+56900000002", message="me da miedo la aguja")

        assert turn["reply_text"]  # el turno respondio, no se rompio
        assert turn["decisions"]["ruteador"]["source"] == "deterministic"
        bundle_ids = {b["doc_id"] for b in turn["decisions"]["ruteador"]["bundle"]}
        assert SECURITY_RULE_IDS <= bundle_ids
    finally:
        orch.close()


def test_orchestrator_turn_traces_agent_as_source_when_router_agent_answers(antonia_kb: Path, tmp_db_url: str) -> None:
    orch = offline_orchestrator(antonia_kb, tmp_db_url, router_agent=FakeRouterAgent(raises=False))
    try:
        turn = orch.handle_turn(external_id="wa:+56900000003", message="hola")

        assert turn["decisions"]["ruteador"]["source"] == "agent"
        bundle_ids = {b["doc_id"] for b in turn["decisions"]["ruteador"]["bundle"]}
        assert SECURITY_RULE_IDS <= bundle_ids
    finally:
        orch.close()
