"""Exportacion del diagrama de conversacion (ConversationStep -> flow.json) para el editor."""
from __future__ import annotations

from pathlib import Path

from frontends.flow_editor.export_flow import export


def test_donpeppe_flow_nodes_edges_and_step_tags(donpeppe_kb: Path) -> None:
    flow = export(str(donpeppe_kb))
    by_id = {n["id"]: n for n in flow["nodes"]}
    assert set(by_id) == {"step-donpeppe-onboarding", "step-donpeppe-booking"}
    assert by_id["step-donpeppe-booking"]["step_tag"] == "conversation:steps.booking"
    assert by_id["step-donpeppe-booking"]["kind"] == "llamado_tool"
    assert by_id["step-donpeppe-booking"]["required_slots"] == ["fecha", "hora", "personas", "nombre"]
    assert {(e["source"], e["target"]) for e in flow["edges"]} == {
        ("step-donpeppe-onboarding", "step-donpeppe-booking"),
        ("step-donpeppe-booking", "step-donpeppe-onboarding"),
    }


def test_antonia_flow_is_a_graph_with_terminal_step(antonia_kb: Path) -> None:
    flow = export(str(antonia_kb))
    by_id = {n["id"]: n for n in flow["nodes"]}
    # 12 steps: los 11 previos + step-antonia-enrolamiento (fase 4, enrolamiento
    # de pacientes no inscritos).
    assert len(by_id) == 12
    assert by_id["step-antonia-despedida"]["allowed_transitions"] == []  # "ninguna (paso terminal)"
    assert all(n["step_tag"] and n["step_tag"].startswith("conversation:steps.") for n in flow["nodes"])
    targets = {e["source"] for e in flow["edges"] if e["target"] == "step-antonia-despedida"}
    assert {
        "step-antonia-recompra",
        "step-antonia-evento-adverso",
        "step-antonia-derivacion-medinfo",
        "step-antonia-revision-humana",
        "step-antonia-journey-operativo",
    } <= targets
    assert "step-antonia-validacion-policy-gate" not in {e["target"] for e in flow["edges"]}

    # step-antonia-enrolamiento: llega desde saludo y sale hacia derivacion
    # medinfo (derivar a un doctor) u onboarding (queda inscrito).
    assert by_id["step-antonia-enrolamiento"]["step_tag"] == "conversation:steps.enrolamiento"
    assert by_id["step-antonia-enrolamiento"]["kind"] == "llamado_tool"
    assert set(by_id["step-antonia-enrolamiento"]["allowed_transitions"]) == {
        "conversation:steps.derivacion_medinfo",
        "conversation:steps.onboarding",
    }
    edge_sources_by_target = {}
    for e in flow["edges"]:
        edge_sources_by_target.setdefault(e["target"], set()).add(e["source"])
    assert "step-antonia-saludo" in edge_sources_by_target["step-antonia-enrolamiento"]
