"""KGDBReader: grafo tag-centrico ingerido desde el store SLDB real de Don Peppe."""
from __future__ import annotations

from pathlib import Path

import pytest

from kb_agent.ontologizador.kgdb_reader import KGDBReader


@pytest.fixture(scope="module")
def reader(donpeppe_kb: Path) -> KGDBReader:
    return KGDBReader.from_sldb(donpeppe_kb / ".sldb")


def test_graph_has_tags_and_documents(reader: KGDBReader) -> None:
    assert reader.graph.number_of_nodes() > 0
    assert reader.find_nodes_by_type("semantic_tag")
    assert reader.find_nodes_by_type("sldb_document")


def test_conversation_steps_hierarchy(reader: KGDBReader) -> None:
    assert reader.steps_under("conversation:steps") == ["conversation:steps.booking", "conversation:steps.onboarding"]
    assert reader.parent_tag("conversation:steps.booking") == "conversation:steps"
    assert reader.child_tags("conversation:steps") == ["conversation:steps.booking", "conversation:steps.onboarding"]
    assert reader.has_tag("conversation:steps.booking") and not reader.has_tag("conversation:steps.nope")


def test_step_grounding_documents_are_reachable(reader: KGDBReader) -> None:
    booking_docs = reader.docs_for_tag("conversation:steps.booking")
    assert {"step-donpeppe-booking", "atom-donpeppe-tool-reserva", "atom-donpeppe-regla-reservas", "atom-donpeppe-promos"} <= set(booking_docs)

    tag_node = reader._tag_node("conversation:steps.booking")
    documents = set(reader.find_nodes_by_type("sldb_document"))
    assert reader.get_neighborhood(tag_node, depth=1) & documents


def test_document_tags_exclude_meta_axes_and_siblings_share_tags(reader: KGDBReader) -> None:
    tags = reader.tags_for_doc("atom-donpeppe-carta")
    assert "domain:catalogo" in tags and "conversation:steps.onboarding" in tags
    assert not any(t.startswith(("type.", "workspace.")) for t in tags)
    assert any(t.startswith("type.") for t in reader.tags_for_doc("atom-donpeppe-carta", include_meta=True))
    assert "atom-donpeppe-horarios" in reader.sibling_docs("atom-donpeppe-carta")
    assert reader.docs_for_tag("no:existe") == [] and reader.tags_for_doc("no-existe") == []
