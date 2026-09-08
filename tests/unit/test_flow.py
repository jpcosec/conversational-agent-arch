"""El diagrama de conversacion leido del grafo tipado de kgdb (kb_agent.knowledge.flow)."""
from __future__ import annotations

from pathlib import Path

import pytest

from knowledge_base.operations import KnowledgeOperations


@pytest.fixture(scope="module")
def ops(negocio_kb: Path) -> KnowledgeOperations:
    return KnowledgeOperations(kb_root=negocio_kb)


def test_steps_transitions_and_entry_come_from_typed_edges(ops: KnowledgeOperations) -> None:
    flow = ops.flow
    assert flow.tags() == ["conversation:steps.booking", "conversation:steps.onboarding"]
    assert flow.entry() == "conversation:steps.onboarding"
    assert flow.transitions("conversation:steps.onboarding") == ["conversation:steps.booking"]
    assert flow.transitions("conversation:steps.booking") == ["conversation:steps.onboarding"]
    assert flow.edges() == [("step-booking", "step-onboarding"), ("step-onboarding", "step-booking")]
    assert flow.step("conversation:steps.booking").tool == "tool-reserva"
    assert flow.step("conversation:steps.nope") is None and flow.transitions("conversation:steps.nope") == []


def test_grounding_unites_tagged_documents_and_grounded_by_edges(ops: KnowledgeOperations) -> None:
    booking = ops.flow.grounding("conversation:steps.booking")
    assert {"step-booking", "tool-reserva", "rule-reservas", "domain-promos"} <= set(booking)
    assert len(booking) == len(set(booking))
    onboarding = ops.flow.grounding("conversation:steps.onboarding")
    assert {"step-onboarding", "domain-menu", "domain-horarios", "domain-ubicacion", "self-negocio"} <= set(onboarding)


def test_tag_navigation_and_siblings_over_the_graph(ops: KnowledgeOperations) -> None:
    root = ops.explore()
    # el DAG de sldb parte los tags por ".", no por ":": "conversation:steps" es raiz
    assert root["mode"] == "root" and {"conversation:steps", "domain:reglas", "self:tools"} <= {r["tag"] for r in root["root_tags"]}
    steps = ops.explore(tag="conversation:steps")
    assert steps["parent"] is None
    assert ops.explore(tag="conversation:steps.booking")["parent"] == "conversation:steps"
    assert steps["children"] == ["conversation:steps.booking", "conversation:steps.onboarding"]
    assert {"step-booking", "tool-reserva"} <= set(ops.docs_for_tag("conversation:steps.booking"))
    tags = ops.tags_for_doc("domain-menu")
    assert "domain:catalogo" in tags and "conversation:steps.onboarding" in tags
    assert not any(t.startswith(("type.", "workspace.")) for t in tags)
    assert any(t.startswith("type.") for t in ops.tags_for_doc("domain-menu", include_meta=True))
    assert "domain-horarios" in ops.siblings("domain-menu")
    assert ops.docs_for_tag("no:existe") == [] and ops.tags_for_doc("no-existe") == []
