"""Integracion del ``GateAgent`` en ``Orchestrator._policy_gate`` (fase 2.3).

Sin red: el orquestador se arma con ``offline_orchestrator`` (LLM fakes) y un
``FakeGate`` inyectado (ver ``tests/support/fakes.py``), que reemplaza al
``GateAgent`` real -- asi se prueba el CABLEADO (que rechazo => "derived",
que un juez caido no rompe el turno) sin ejercer heuristicas de texto ni LLM
real (eso vive en ``tests/unit/test_gate_agent.py``).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from kb_agent.orchestrator import Orchestrator
from tests.support.fakes import FakeGate, offline_orchestrator

QUESTION = "que pizzas tienen?"


@pytest.fixture()
def orch_factory(donpeppe_kb: Path, tmp_db_url: str):
    made: list[Orchestrator] = []

    def _make(gate: FakeGate) -> Orchestrator:
        o = offline_orchestrator(donpeppe_kb, tmp_db_url, gate=gate)
        made.append(o)
        return o

    yield _make
    for o in made:
        o.close()


def test_gate_rejection_replaces_response_with_handoff(orch_factory) -> None:
    def verdict_fn(_response: str, **_kwargs):
        return {
            "approved": False,
            "reasons": ["violó gate-antonia-dosis"],
            "action": "handoff",
            "criterion_ids": ["gate-antonia-dosis"],
        }

    gate = FakeGate(verdict_fn)
    orch = orch_factory(gate)

    turn = orch.handle_turn(external_id="ui:gate-reject", message=QUESTION)

    assert turn["kind"] == "derived"
    assert "profesional" in turn["reply"]  # el texto de handoff, no el borrador del conversador
    assert turn["decisions"]["gate"]["approved"] is False
    assert turn["decisions"]["gate"]["reasons"] == ["violó gate-antonia-dosis"]
    assert turn["decisions"]["gate"]["action"] == "handoff"
    assert turn["decisions"]["gate"]["criterion_ids"] == ["gate-antonia-dosis"]
    # el borrador original se conserva en el rastro del conversador aunque el gate lo reemplace
    assert turn["decisions"]["conversador"]["draft"] != turn["reply"]

    assert len(gate.calls) == 1
    assert gate.calls[0]["tool_called"] is False  # turno nl sin system_turn


def test_gate_approval_keeps_conversador_response(orch_factory) -> None:
    gate = FakeGate()  # aprueba todo por defecto
    orch = orch_factory(gate)

    turn = orch.handle_turn(external_id="ui:gate-approve", message=QUESTION)

    assert turn["kind"] == "nl"
    assert turn["reply"] == turn["decisions"]["conversador"]["draft"]
    assert turn["decisions"]["gate"] == {"approved": True, "reasons": [], "action": "pass", "criterion_ids": []}
    assert len(gate.calls) == 1


def test_gate_exception_fails_open_and_does_not_break_turn(orch_factory) -> None:
    gate = FakeGate(raises=True)
    orch = orch_factory(gate)

    turn = orch.handle_turn(external_id="ui:gate-boom", message=QUESTION)

    # fail-open: el turno sigue, la respuesta del conversador NO se reemplaza
    assert turn["kind"] == "nl"
    assert turn["reply"] == turn["decisions"]["conversador"]["draft"]
    assert turn["decisions"]["gate"]["approved"] is True
    assert turn["decisions"]["gate"].get("fail_open") is True
    assert len(gate.calls) == 1  # se intento llamar al juez, no se lo salteo


def test_empty_response_skips_gate_call_entirely(orch_factory) -> None:
    """Guardia existente conservada: si no hay respuesta de texto, ni se llama al gate."""
    gate = FakeGate()
    orch = orch_factory(gate)

    # "que pizzas tienen?" siempre produce texto con el FakeConversador (ver
    # tests/support/fakes.py); no hay forma facil de forzar respuesta vacia
    # sin tocar knowledge_base/*, asi que este test ejercita la guardia via
    # _policy_gate directamente en vez de un turno completo.
    result = orch._policy_gate("   ", {})
    assert result == {"approved": True, "reasons": [], "action": "pass", "criterion_ids": []}
    assert gate.calls == []
