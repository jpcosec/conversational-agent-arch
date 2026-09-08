"""KGDB reader para el compilador.

Carga un grafo KGDB (desde archivo o ingerido desde SLDB) y permite
navegar nodos de flujo conversacional, transiciones, relaciones entre
atoms, tools y traits.

Uso:
    reader = KGDBReader(graph_path=Path("knowledge.kg.json"))
    flow_node = reader.get_flow_node("reserva_pedir_personas")
    transitions = reader.get_next_transitions("reserva_pedir_personas")

O desde SLDB:
    reader = KGDBReader.from_sldb(store_path=Path("tests/knowledge/.sldb"))
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx

from kgdb.graph import add_knowledge_node, load_graph
from kgdb.ingest.sldb import sldb_semantic_export_to_snapshot
from kgdb.query.neighborhood import collect_neighborhood

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


def _resolve_store_path(store_path: Path) -> Path:
    if store_path.name == ".sldb":
        return store_path
    nested_store = store_path / ".sldb"
    if nested_store.exists():
        return nested_store
    return store_path


class KGDBReader:
    """Navega un grafo KGDB para resolver flujo conversacional."""

    def __init__(self, graph: nx.DiGraph) -> None:
        self._graph = graph
        #: indice perezoso id pelado -> node_id (ver ``_doc_node``)
        self._doc_nodes: dict[str, str] | None = None

    # ── constructores ────────────────────────────────────────────

    @classmethod
    def from_sldb(cls, store_path: str | Path, pythonpath: str | None = None) -> KGDBReader:
        """Construye el grafo desde un store SLDB via el pipeline de ingest.

        Usa el exportador de sldb (``export_kgdb_semantic_payload``), que es
        el productor oficial del contrato ``sldb_kgdb_semantic_export`` que
        consume ``sldb_semantic_export_to_snapshot``. Antes esto armaba ese
        payload a mano, caminando ``store_index -> models_index ->
        documents_index`` con ``hasattr`` a cada campo, y salia lossy:
        ``"model": "AtomDoc"`` hardcodeado para TODOS los documentos (perdiendo
        el modelo real de cada uno) y ``"sections": []`` siempre.
        """
        from sldb.cli.model_utils import resolve_model_ref
        from sldb.store.export import export_kgdb_semantic_payload

        store_path = _resolve_store_path(Path(store_path))
        payload = export_kgdb_semantic_payload(
            store_path, store_path.parent, resolve_model_ref, pythonpath,
        )
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

    # ── navegacion tag-centrica (grafo generado desde SLDB, para explore) ──
    #
    # El grafo que produce sldb_semantic_export_to_snapshot es tag-centrico:
    #   sldb://semantic_tag/<tag>              nodo de tag
    #   sldb://document/<doc>  --tagged_as-->  sldb://semantic_tag/<tag>
    #   <tag.hijo>             --semantic_parent--> <tag.padre>
    # El "diagrama de conversacion" vive en la jerarquia conversation:steps.*.

    TAG_PREFIX = "sldb://semantic_tag/"
    DOC_PREFIX = "sldb://document/"

    def _tag_node(self, tag: str) -> str:
        """Normaliza un tag a su node_id en el grafo."""
        if tag.startswith(self.TAG_PREFIX):
            return tag
        return f"{self.TAG_PREFIX}{tag}"

    def _strip_tag(self, node_id: str) -> str:
        return node_id[len(self.TAG_PREFIX):] if node_id.startswith(self.TAG_PREFIX) else node_id

    def _strip_doc(self, node_id: str) -> str:
        """node_id del grafo -> id pelado del atom.

        El exportador de sldb namespacea cada documento por su modelo
        (``DomainAtom:atom-x``) para que dos modelos puedan tener documentos
        homonimos. El contrato PUBLICO de este reader son ids pelados, porque
        el compilador los compara contra los ids de la KB (``knowledge.doc``),
        asi que el namespace se quita aca, en el borde.
        """
        bare = node_id[len(self.DOC_PREFIX):] if node_id.startswith(self.DOC_PREFIX) else node_id
        return bare.split(":", 1)[1] if ":" in bare else bare

    def _doc_node(self, doc_id: str) -> str | None:
        """id pelado del atom -> node_id del grafo (o ``None`` si no esta).

        Inverso de ``_strip_doc``. El indice se arma una vez por instancia:
        el grafo es inmutable despues del ingest.
        """
        if doc_id.startswith(self.DOC_PREFIX):
            return doc_id if doc_id in self._graph else None
        if self._doc_nodes is None:
            self._doc_nodes = {
                self._strip_doc(n): n
                for n in self._graph.nodes
                if n.startswith(self.DOC_PREFIX)
            }
        return self._doc_nodes.get(doc_id)

    def list_tags(self) -> list[str]:
        """Lista todos los tags semánticos del grafo (sin prefijo)."""
        return sorted(
            self._strip_tag(n)
            for n, d in self._graph.nodes(data=True)
            if d.get("type") == "semantic_tag"
        )

    def root_tags(self) -> list[str]:
        """Lista tags raíz (sin semantic_parent saliente)."""
        roots = []
        for n, d in self._graph.nodes(data=True):
            if d.get("type") != "semantic_tag":
                continue
            has_parent = any(
                data.get("relation") == "semantic_parent"
                for _, _, data in self._graph.out_edges(n, data=True)
            )
            if not has_parent:
                roots.append(self._strip_tag(n))
        return sorted(roots)

    def child_tags(self, tag: str) -> list[str]:
        """Lista tags hijos de un tag (via semantic_parent entrante)."""
        node = self._tag_node(tag)
        if node not in self._graph:
            return []
        children = []
        for pred, _, data in self._graph.in_edges(node, data=True):
            if data.get("relation") == "semantic_parent":
                children.append(self._strip_tag(pred))
        return sorted(children)

    def parent_tag(self, tag: str) -> str | None:
        """Devuelve el tag padre (via semantic_parent saliente)."""
        node = self._tag_node(tag)
        if node not in self._graph:
            return None
        for _, target, data in self._graph.out_edges(node, data=True):
            if data.get("relation") == "semantic_parent":
                return self._strip_tag(target)
        return None

    # meta-tags demasiado amplios para navegación útil
    _META_TAG_PREFIXES = ("type.", "workspace.")

    def docs_for_tag(self, tag: str) -> list[str]:
        """Lista documentos etiquetados con un tag (via tagged_as entrante)."""
        node = self._tag_node(tag)
        if node not in self._graph:
            return []
        docs = []
        for pred, _, data in self._graph.in_edges(node, data=True):
            if data.get("relation") == "tagged_as" and pred.startswith(self.DOC_PREFIX):
                docs.append(self._strip_doc(pred))
        return sorted(docs)

    def tags_for_doc(self, doc_id: str, include_meta: bool = False) -> list[str]:
        """Lista tags de un documento (via tagged_as saliente).

        Por defecto excluye meta-tags (type.*, workspace.*) que no sirven
        para navegación semántica.
        """
        node = self._doc_node(doc_id)
        if node is None:
            return []
        tags = []
        for _, target, data in self._graph.out_edges(node, data=True):
            if data.get("relation") == "tagged_as":
                tag = self._strip_tag(target)
                if not include_meta and tag.startswith(self._META_TAG_PREFIXES):
                    continue
                tags.append(tag)
        return sorted(tags)

    def sibling_docs(self, doc_id: str) -> list[str]:
        """Documentos que comparten al menos un tag semántico (no meta) con este doc."""
        siblings: set[str] = set()
        for tag in self.tags_for_doc(doc_id):
            for other in self.docs_for_tag(tag):
                if other != doc_id:
                    siblings.add(other)
        return sorted(siblings)

    def has_tag(self, tag: str) -> bool:
        """True si el grafo conoce el tag semantico."""
        return self._tag_node(tag) in self._graph

    def steps_under(self, root_tag: str = "conversation:steps") -> list[str]:
        """Lista los steps hijos de un tag raiz (ej. conversation:steps).

        Devuelve los tags de step completos (conversation:steps.booking, ...)
        derivados de las aristas semantic_parent del grafo real.
        """
        node = self._tag_node(root_tag)
        if node not in self._graph:
            return []
        children = []
        for pred, _, data in self._graph.in_edges(node, data=True):
            if data.get("relation") == "semantic_parent" and pred.startswith(self.TAG_PREFIX):
                children.append(self._strip_tag(pred))
        return sorted(children)

    @property
    def graph(self) -> nx.DiGraph:
        return self._graph