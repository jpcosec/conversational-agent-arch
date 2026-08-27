"""step-antonia-enrolamiento se lee de la KB real con sus transiciones (fase 4)."""
from __future__ import annotations

from pathlib import Path

from kb_agent.ontologizador.sldb_reader import SLDBReader


def test_enrolamiento_step_is_tracked_with_expected_transitions(antonia_kb: Path) -> None:
    reader = SLDBReader(kb_root=antonia_kb)
    steps = reader.find("type.knowledge.step")

    assert len(steps) == 12

    by_id = {s["id"]: s for s in steps}
    enrolamiento = by_id["step-antonia-enrolamiento"]

    assert enrolamiento["kind"] == "llamado_tool"
    transitions = {t.strip() for t in enrolamiento["allowed_transitions"].split(",")}
    assert transitions == {"conversation:steps.derivacion_medinfo", "conversation:steps.onboarding"}
    assert "telefono" in enrolamiento["required_slots"].lower() or "teléfono" in enrolamiento["required_slots"].lower()
    assert "mail" in enrolamiento["required_slots"].lower() or "correo" in enrolamiento["required_slots"].lower()


def test_saludo_step_can_transition_into_enrolamiento(antonia_kb: Path) -> None:
    reader = SLDBReader(kb_root=antonia_kb)
    steps = reader.find("type.knowledge.step")
    by_id = {s["id"]: s for s in steps}

    saludo_transitions = {t.strip() for t in by_id["step-antonia-saludo"]["allowed_transitions"].split(",")}
    assert "conversation:steps.enrolamiento" in saludo_transitions


def test_registrar_enrolamiento_tool_is_tracked_with_matching_schema(antonia_kb: Path) -> None:
    reader = SLDBReader(kb_root=antonia_kb)
    tools = reader.find("type.knowledge.tool")
    by_id = {t["id"]: t for t in tools}

    assert "registrar_enrolamiento" in by_id
    parameters = by_id["registrar_enrolamiento"]["parameters"]
    assert '"name": "registrar_enrolamiento"' in parameters
    for field in ("nombre", "telefono", "mail"):
        assert field in parameters
