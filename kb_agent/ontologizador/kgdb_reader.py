"""KGDB reader para el compilador.

Carga un grafo KGDB (desde archivo o ingerido desde SLDB) y permite
navegar nodos de flujo conversacional, transiciones, relaciones entre
atoms, tools y traits.

Uso:
    reader = KGDBReader(graph_path=Path("knowledge.kg.json"))
    flow_node = reader.get_flow_node("reserva_pedir_personas")
    transitions = reader.get_next_transitions("reserva_pedir_personas")

O desde SLDB:
    reader = KGDBReader.from_sldb(store_path=Path(".sldb_e2e_donpeppe/.sldb"))
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx

from kgdb.graph import add_knowledge_node, load_graph, save_graph
from kgdb.graph.utils import load_knowledge_node
from kgdb.ingest.sldb import sldb_semantic_export_to_snapshot
from kgdb.query.neighborhood import collect_neighborhood, collect_neighborhood_by_direction

# ───────────────── relaciones de flujo conversacional ─────────────────
REL_FLOWS_TO = "flows_to"
REL_GROUNDED_BY = "grounded_by"
REL_USES_TOOL = "uses_tool"
REL_REQUIRES_SLOT = "requires_slot"
REL_ADAPTS_TO_TRAIT = "adapts_to_trait"
REL_FALLBACKS_TO = "falls_back_to"

NODE_KIND_FLOW = "conversation_flow_node"
NODE_KIND_SLOT = "slot"
NODE_KIND_TOOL = "tool"
NODE_KIND_TRAIT = "trait"
NODE_KIND_ATOM = "atom"


class KGDBReader:
    """Navega un grafo KGDB para resolver flujo conversacional."""

    def __init__(self, graph: nx.DiGraph) -> None:
        self._graph = graph

    # ── constructores ────────────────────────────────────────────

    @classmethod
    def from_sldb(cls, store_path: str | Path, pythonpath: str | None = None) -> KGDBReader:
        """Construye un grafo desde un store SLDB via el pipeline de ingest."""
        from sldb.store.io import load_store_index
        from sldb.store.io import load_models_index as _load_midx
        from sldb.store.io import load_documents_index as _load_didx

        store_path = Path(store_path)
        root = store_path.parent
        store_idx = load_store_index(store_path)

        # Cargar índices de cada modelo
        documents_rows = []
        model_rows = []
        for m in store_idx.models:
            if not hasattr(m, "models_index"):
                continue
            m_idx_path = root / m.models_index
            if not m_idx_path.exists():
                continue
            m_idx = _load_midx(m_idx_path)
            model_rows.append(m_idx)
            d_idx_path = root / m_idx.documents_index
            if d_idx_path.exists():
                d_idx = _load_didx(d_idx_path)
                documents_rows.extend(d_idx.documents)

        payload = {
            "contract": {
                "name": "sldb_kgdb_semantic_export",
                "version": 1,
                "generated_at": "now",
            },
            "producer": {"name": "sldb", "version": "0.1.0", "command": ["sldb", "semantic", "export", "--format", "kgdb"]},
            "store": {
                "root": str(root),
                "store_path": str(store_path),
                "hash_a": store_idx.hash_a or "",
                "runtime_sources": {},
            },
            "models": [
                {
                    "name": m.name,
                    "model_ref": m.model_ref if hasattr(m, "model_ref") else "",
                    "path": m.path if hasattr(m, "path") else "",
                    "models_index": m.models_index if hasattr(m, "models_index") else "",
                    "version": m.version if hasattr(m, "version") else 1,
                    "canonical": m.canonical if hasattr(m, "canonical") else False,
                    "family": m.family if hasattr(m, "family") else None,
                    "semantics": m.semantics if hasattr(m, "semantics") else [],
                }
                for m in model_rows
            ],
            "documents": [
                {
                    "id": d.name,
                    "name": d.name,
                    "model": "AtomDoc",
                    "path": d.path,
                    "hash_c": d.hash_c or "",
                    "hash_d": d.hash_d or "",
                    "semantic_tags": d.semantic_tags or [],
                }
                for d in documents_rows
            ],
            "sections": [],
        }

        snapshot = sldb_semantic_export_to_snapshot(payload)
        graph = nx.DiGraph()
        for node in snapshot.nodes:
            add_knowledge_node(graph, node)
        return cls(graph)

    @classmethod
    def from_file(cls, path: str | Path) -> KGDBReader:
        """Carga un grafo persistido desde un archivo JSON."""
        graph = load_graph(Path(path))
        return cls(graph)

    # ── consultas de flujo conversacional ────────────────────────

    def get_flow_node(self, node_id: str) -> dict[str, Any] | None:
        """Obtiene un nodo de flujo conversacional por su id."""
        if node_id not in self._graph:
            return None
        return self._graph.nodes[node_id].get("schema", {})

    def get_next_transitions(self, node_id: str) -> list[dict[str, Any]]:
        """Obtiene las transiciones salientes de un nodo."""
        transitions = []
        for _, target, data in self._graph.out_edges(node_id, data=True):
            if data.get("relation") == REL_FLOWS_TO:
                transitions.append({
                    "to": target,
                    "relation": data.get("relation"),
                    "metadata": data.get("metadata", {}),
                })
        return transitions

    def get_grounding_atoms(self, node_id: str) -> list[str]:
        """Obtiene los ids de atoms que groundean un nodo."""
        atoms = []
        for _, target, data in self._graph.out_edges(node_id, data=True):
            if data.get("relation") == REL_GROUNDED_BY:
                atoms.append(target)
        return atoms

    def get_tools_for_node(self, node_id: str) -> list[str]:
        """Obtiene las tools habilitadas para un nodo."""
        tools = []
        for _, target, data in self._graph.out_edges(node_id, data=True):
            if data.get("relation") == REL_USES_TOOL:
                tools.append(target)
        return tools

    def get_neighborhood(self, node_id: str, depth: int = 1) -> set[str]:
        """Obtiene todos los nodos en el vecindario de un nodo (para navegación)."""
        ids = collect_neighborhood(self._graph, [node_id], depth)
        return ids

    def find_nodes_by_type(self, node_type: str) -> list[str]:
        """Lista todos los nodos de un tipo."""
        result = []
        for node_id, data in self._graph.nodes(data=True):
            schema = data.get("schema", {})
            identity = schema.get("identity", {}) if isinstance(schema, dict) else {}
            nt = identity.get("node_type", schema.get("type"))
            if nt == node_type:
                result.append(node_id)
        return result

    @property
    def graph(self) -> nx.DiGraph:
        return self._graph