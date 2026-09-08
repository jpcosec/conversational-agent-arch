"""step-antonia-enrolamiento se lee de la KB real con sus transiciones (fase 4)."""
from __future__ import annotations

from pathlib import Path

from knowledge_base.operations import KnowledgeOperations


def test_enrolamiento_step_is_tracked_with_expected_transitions(antonia_kb: Path) -> None:
    reader = KnowledgeOperations(kb_root=antonia_kb)
    steps = reader.docs_by_type("step")

    assert len(steps) == 12

    by_id = {s["id"]: s for s in steps}
    enrolamiento = by_id["step-antonia-enrolamiento"]

    assert enrolamiento["kind"] == "llamado_tool"
    transitions = set(reader.flow.transitions("conversation:steps.enrolamiento"))
    assert transitions == {"conversation:steps.derivacion_medinfo", "conversation:steps.onboarding"}
    assert "telefono" in enrolamiento["required_slots"].lower() or "teléfono" in enrolamiento["required_slots"].lower()
    assert "mail" in enrolamiento["required_slots"].lower() or "correo" in enrolamiento["required_slots"].lower()


def test_saludo_step_can_transition_into_enrolamiento(antonia_kb: Path) -> None:
    reader = KnowledgeOperations(kb_root=antonia_kb)
    assert "conversation:steps.enrolamiento" in reader.flow.transitions("conversation:steps.saludo")


def test_registrar_enrolamiento_tool_is_tracked_with_matching_schema(antonia_kb: Path) -> None:
    reader = KnowledgeOperations(kb_root=antonia_kb)
    tools = reader.docs_by_type("tool")
    by_id = {t["id"]: t for t in tools}

    assert "registrar_enrolamiento" in by_id
    parameters = by_id["registrar_enrolamiento"]["parameters"]
    assert '"name": "registrar_enrolamiento"' in parameters
    for field in ("nombre", "telefono", "mail"):
        assert field in parameters
