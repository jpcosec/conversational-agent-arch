from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from kb_agent.ontologizador.kgdb_reader import KGDBReader

STORE_ROOT = PROJECT_ROOT / "tests/knowledge"


def test_kgdb_reader_builds_navigable_graph_from_real_sldb_store(tmp_path: Path) -> None:
    copied_root = tmp_path / "donpeppe-copy"
    shutil.copytree(STORE_ROOT, copied_root)

    reader = KGDBReader.from_sldb(copied_root / ".sldb")
    graph = reader.graph

    semantic_tags = reader.find_nodes_by_type("semantic_tag")
    documents = reader.find_nodes_by_type("sldb_document")

    assert graph.number_of_nodes() > 0
    assert semantic_tags
    assert documents

    # Doctrina nueva (KB-DOCTRINE.md): el escenario ya no es un tag monolitico
    # domain:pizzeria. El diagrama de conversacion vive en conversation:steps.*.
    # Navegamos el step de reserva y verificamos que alcanza sus documentos
    # grounding via el traversal tag -> documento del grafo KGDB.
    booking_tag = next(
        node_id for node_id in semantic_tags if "conversation:steps.booking" in node_id
    )
    neighborhood = reader.get_neighborhood(booking_tag, depth=1)
    reachable_documents = sorted(
        node_id for node_id in neighborhood if node_id in documents
    )

    # El helper tag-centrico debe resolver los mismos documentos por id corto.
    grounded_docs = reader.docs_for_tag("conversation:steps.booking")

    evidence_path = PROJECT_ROOT / "runs" / "e2e" / "kgdb-navigation.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "copied_store": str(copied_root),
                "nodes_total": graph.number_of_nodes(),
                "edges_total": graph.number_of_edges(),
                "semantic_tag_count": len(semantic_tags),
                "document_count": len(documents),
                "booking_tag": booking_tag,
                "reachable_documents_from_booking": reachable_documents,
                "grounded_docs_for_booking": grounded_docs,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    assert reachable_documents, "conversation:steps.booking must reach at least one document via KGDB neighborhood traversal"
    assert "conversation-steps-booking" in grounded_docs
    assert "atom-donpeppe-tool-reserva" in grounded_docs
