"""El diagrama de conversacion leido del grafo tipado de kgdb.

Un step es un documento ``ConversationStep``; su identidad de flujo (lo que
``SessionState.flow_node`` persiste) es su tag ``conversation:steps.<x>``. Las
aristas son ``RelationDoc`` de la KB con tres tipos declarados en
``<kb>/relations/types/`` (ver ``scripts/migrate_step_relations.py``):

- ``transitions_to``  step -> step        a donde puede navegar el orquestador
- ``grounded_by``     step -> documento   que entra al bundle cuando el step esta activo
- ``uses_tool``       step -> ToolAtom    la tool de un step ``llamado_tool``

kgdb valida esas aristas al ensamblar el grafo (una referencia a un documento
inexistente es un error de ingest), asi que aca no hay parseo ni filtro
defensivo: solo lecturas sobre ``pron.graph.Graph``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pron.graph import Graph, bare, doc_id, kind, tag_id

STEP_MODEL = "ConversationStep"
STEP_TAG_PREFIX = "conversation:steps."
REL_TRANSITIONS_TO = "transitions_to"
REL_GROUNDED_BY = "grounded_by"
REL_USES_TOOL = "uses_tool"


def _doc_name(node_id: str) -> str:
    """``sldb://document/Model:name`` -> ``name`` (el id pelado que usa el runtime)."""
    b = bare(node_id)
    return b.split(":", 1)[1] if ":" in b else b


def _step_tag(graph: Graph, node_id: str) -> str | None:
    for t in graph.targets(node_id, "tagged_as"):
        tag = bare(t)
        if tag.startswith(STEP_TAG_PREFIX):
            return tag
    return None


@dataclass(frozen=True)
class FlowStep:
    id: str
    tag: str
    transitions: list[str] = field(default_factory=list)   # tags de los steps destino
    grounding: list[str] = field(default_factory=list)     # ids de documentos
    tool: str | None = None                                 # id del ToolAtom


class ConversationFlow:
    """Vista del diagrama sobre un grafo fresco. Barata: indexa una vez por instancia."""

    def __init__(self, graph: Graph) -> None:
        self.graph = graph
        self._steps: dict[str, FlowStep] | None = None   # por tag

    def _index(self) -> dict[str, FlowStep]:
        if self._steps is None:
            g = self.graph
            nodes = g.nodes_of_type(STEP_MODEL) if g.available() else []
            tag_of = {n: _step_tag(g, n) for n in nodes}
            steps: dict[str, FlowStep] = {}
            for n, tag in tag_of.items():
                if tag is None:
                    continue
                transitions = sorted(t for t in (tag_of.get(x) for x in g.targets(n, REL_TRANSITIONS_TO)) if t)
                tools = [_doc_name(x) for x in g.targets(n, REL_USES_TOOL)]
                steps[tag] = FlowStep(
                    id=_doc_name(n), tag=tag, transitions=transitions,
                    grounding=self._grounding(n, tag), tool=tools[0] if tools else None,
                )
            self._steps = steps
        return self._steps

    def _grounding(self, node_id: str, tag: str) -> list[str]:
        """Union sin duplicados: los documentos que llevan el tag del step (el propio
        step, sus ToolAtom, ...) y los que el step declara con ``grounded_by``."""
        ids: list[str] = []
        for n in self.graph.sources(tag_id(tag), "tagged_as"):
            if kind(n) == "document":
                ids.append(_doc_name(n))
        for n in self.graph.targets(node_id, REL_GROUNDED_BY):
            name = _doc_name(n)
            if name not in ids:
                ids.append(name)
        return ids

    # -- consultas -----------------------------------------------------------------
    def steps(self) -> list[FlowStep]:
        return sorted(self._index().values(), key=lambda s: s.tag)

    def tags(self) -> list[str]:
        return sorted(self._index())

    def step(self, tag: str | None) -> FlowStep | None:
        return self._index().get(tag) if tag else None

    def by_id(self, step_id: str) -> FlowStep | None:
        return next((s for s in self._index().values() if s.id == step_id), None)

    def transitions(self, tag: str) -> list[str]:
        s = self.step(tag)
        return list(s.transitions) if s else []

    def grounding(self, tag: str) -> list[str]:
        s = self.step(tag)
        return list(s.grounding) if s else []

    def entry(self) -> str | None:
        """Step de entrada: ``.onboarding`` si la KB lo declara; si no, una raiz del grafo
        de transiciones (un step al que ningun otro transiciona; la primera por tag); si
        no hay raiz (ciclo), el primer step por tag."""
        tags = self.tags()
        if not tags:
            return None
        onboarding = next((t for t in tags if t.endswith(".onboarding")), None)
        if onboarding:
            return onboarding
        targets = {t for s in self._index().values() for t in s.transitions}
        roots = [t for t in tags if t not in targets]
        return roots[0] if roots else tags[0]

    def resolve_active(self, current: str | None) -> str | None:
        """El step de la sesion si existe en el diagrama; si no, el de entrada."""
        if current and current in self._index():
            return current
        return self.entry()

    def edges(self) -> list[tuple[str, str]]:
        """``(step_id, step_id)`` por cada ``transitions_to``."""
        idx = self._index()
        return [(s.id, idx[t].id) for s in self.steps() for t in s.transitions if t in idx]


def step_node(step_id: str) -> str:
    return doc_id(f"{STEP_MODEL}:{step_id}")
