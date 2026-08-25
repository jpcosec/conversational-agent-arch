# agent-design

Diseño y esqueleto mínimo del agente de conocimiento tipado.

## Archivos
- `00-AGENT-FLOW.md` — diagrama de flujo + mapa a los repos existentes.
- `skeleton/kinds.py` — tipos núcleo (el "lenguaje tipado"): TypedForm, Verdict (S_i/V_i), Atom, Node, Edge.
- `skeleton/ports.py` — puertos hacia kgdb/sldb/LLM/gate (interfaces, no implementaciones).
- `skeleton/agent.py` — el loop G-first completo (~90 líneas). Es todo el agente.
- `skeleton/demo.py` — demo ejecutable con adaptadores fake.

## Correr
```
cd skeleton && python demo.py
```

## Idea en una frase
El agente sabe en un grafo tipado externo (no en pesos); el LLM solo traduce
NL → lenguaje tipado, y todo lo nuevo pasa por un gate de sentido (S_i/V_i)
antes de guardarse como átomo con provenance.

## Siguiente paso real
Reemplazar los `Fake*` de `demo.py` por adaptadores sobre los CLIs reales:
- `FakeGraph` → `kgdb query/get/ingest`
- `FakeStore` → `sldb docs/fields`
- `FakeGate` → lifecycle de `Matrix/spec/proposition_lifecycle.yaml`
- `FakeLLM` → LLM real con prompt que fuerza el grammar tipado
Los puertos ya aíslan esto: el loop de `agent.py` no cambia.
