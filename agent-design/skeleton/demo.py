"""Demo ejecutable del loop, con adaptadores fake (sin kgdb/LLM reales).

Prueba que el flujo G-first funciona end-to-end:
  - primera pregunta: miss -> LLM -> gate -> materializa -> guarda
  - segunda pregunta igual: hit -> responde desde el grafo (barato)
  - forma unsinnig: se rechaza, NO se guarda

Ejecutar:  python demo.py
"""
from __future__ import annotations

from agent import Agent, Energy
from kinds import Atom, Edge, Node, Sense, TypedForm, Verdict


# --- Adaptadores fake ---------------------------------------------------

class FakeGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []

    def ask(self, query: str) -> list[Node]:
        # match tonto: devuelve nodos cuyo id aparece en el texto.
        return [n for nid, n in self.nodes.items() if nid in query]

    def add_node(self, node: Node) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)


class FakeLLM:
    """Traductor NL -> formas tipadas. Aqui hardcodeado por demo."""
    def translate(self, nl_input: str, context):
        if "gato" in nl_input:
            return [
                TypedForm(kind="rel", head="es_un", args=["gato", "mamifero"],
                          raw="(rel es_un gato mamifero)"),
                TypedForm(kind="think", head="gato", args=[],
                          raw="(think gato: felino domestico)"),
            ]
        if "color de la lunes" in nl_input:
            # sin sentido: categoria mal formada
            return [TypedForm(kind="rel", head="color_de", args=["lunes", "azul"],
                              raw="(rel color_de lunes azul)")]
        return [TypedForm(kind="think", head="desconocido", args=[],
                          raw="(think sin_datos)")]


class FakeGate:
    def judge(self, form: TypedForm, context) -> Verdict:
        # S_i: 'lunes' no es cosa coloreable -> unsinnig.
        if form.head == "color_de" and "lunes" in form.args:
            return Verdict(sense=Sense.UNSINNIG, truth=None,
                           reason="'lunes' no admite el predicado color_de")
        return Verdict(sense=Sense.SINNVOLL, truth=True, reason="bien tipado")


class FakeStore:
    def __init__(self) -> None:
        self.atoms: dict[str, Atom] = {}

    def save_atom(self, atom: Atom) -> str:
        self.atoms[atom.id] = atom
        return atom.id


# --- Demo ---------------------------------------------------------------

def main() -> None:
    agent = Agent(graph=FakeGraph(), llm=FakeLLM(),
                  gate=FakeGate(), store=FakeStore(), energy=Energy())

    print("== 1) pregunta nueva (miss -> LLM) ==")
    r = agent.ask("cuentame del gato")
    print(f"  source={r.source}  answer={r.answer}")
    print(f"  nuevas aristas={len(r.new_edges)} nodos={len(r.new_nodes)}")

    print("== 2) misma info ya en grafo (hit -> barato) ==")
    r = agent.ask("dime del gato")
    print(f"  source={r.source}  answer={r.answer}")

    print("== 3) forma unsinnig (se rechaza) ==")
    r = agent.ask("cual es el color de la lunes")
    print(f"  source={r.source}  answer={r.answer}")
    print(f"  rechazadas={len(r.rejected)}")

    print(f"\n== energy: g_hits={agent.energy.g_hits} "
          f"llm_calls={agent.energy.llm_calls} ratio={agent.energy.ratio:.2f} ==")


if __name__ == "__main__":
    main()
