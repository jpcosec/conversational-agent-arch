"""El loop G-first. ~60 lineas. Es TODO el agente.

Refleja 1:1 el diagrama de 00-AGENT-FLOW.md.
Los puertos son inyectados: aqui no hay ni kgdb ni LLM reales.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ports import GatePort, GraphPort, LLMPort, StorePort
from kinds import AgentResult, Edge, Node, Sense, TypedForm


@dataclass
class Energy:
    """Metrica de salud: cuanto respondio el grafo vs el LLM."""
    g_hits: int = 0
    llm_calls: int = 0

    @property
    def ratio(self) -> float:
        total = self.g_hits + self.llm_calls
        return self.g_hits / total if total else 0.0


@dataclass
class Agent:
    graph: GraphPort
    llm: LLMPort
    gate: GatePort
    store: StorePort
    energy: Energy = field(default_factory=Energy)

    def ask(self, nl_input: str) -> AgentResult:
        # 1 + 2: parse -> query -> preguntar al grafo tipado (barato).
        hits = self.graph.ask(nl_input)
        if hits:
            self.energy.g_hits += 1
            return AgentResult(answer=self._render(hits), source="graph")

        # 3: miss -> LLM como TRADUCTOR, salida tipada obligatoria.
        self.energy.llm_calls += 1
        forms = self.llm.translate(nl_input, context=hits)

        new_nodes: list[Node] = []
        new_edges: list[Edge] = []
        rejected: list[TypedForm] = []

        for form in forms:
            # 4: gate S_i / V_i. unsinnig no se guarda.
            verdict = self.gate.judge(form, context=hits)
            if verdict.sense is Sense.UNSINNIG:
                rejected.append(form)
                continue

            # 5: materializar segun el tipo.
            #   rel     -> arista
            #   command -> (aqui) se registraria una tool call
            #   think   -> se persiste como atomo
            if form.kind == "rel" and len(form.args) >= 2:
                new_edges.append(
                    Edge(src=form.args[0], dst=form.args[1],
                         relation_type=form.head,
                         facets={"sense": verdict.sense.value})
                )
            elif form.kind in ("think", "model"):
                new_nodes.append(
                    Node(node_id=form.head, node_type=form.kind,
                         facets={"raw": form.raw, "sense": verdict.sense.value})
                )
            # command -> integrar con un registry de tools (fuera de scope)

        # 6: persistir + responder.
        for n in new_nodes:
            self.graph.add_node(n)
        for e in new_edges:
            self.graph.add_edge(e)

        return AgentResult(
            answer=self._render_forms(forms, rejected),
            source="llm",
            new_nodes=new_nodes,
            new_edges=new_edges,
            rejected=rejected,
        )

    def _render(self, nodes: list[Node]) -> str:
        return "; ".join(f"{n.node_type}:{n.node_id}" for n in nodes)

    def _render_forms(self, forms: list[TypedForm], rejected: list[TypedForm]) -> str:
        kept = [f for f in forms if f not in rejected]
        out = "; ".join(f.raw for f in kept)
        if rejected:
            out += f"  [rechazadas (unsinnig): {len(rejected)}]"
        return out
