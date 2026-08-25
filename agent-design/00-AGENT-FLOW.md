# Agente de conocimiento tipado — flujo

El agente NO sabe en sus pesos. Sabe en un grafo tipado externo, versionado y auditable.
El LLM es un **traductor** (NL → lenguaje tipado), no la fuente de verdad.

## Loop principal (G-first)

```
                        ┌──────────────────────────────┐
                        │        input (NL)            │
                        └───────────────┬──────────────┘
                                        │
                         ┌──────────────▼──────────────┐
                         │  1. PARSE → StructuredQuery  │   (typed, no grep)
                         └──────────────┬──────────────┘
                                        │
                         ┌──────────────▼──────────────┐
                         │  2. ASK GRAPH (kgdb)         │
                         └──────┬────────────────┬──────┘
                          hit   │                │ miss
                    ┌───────────▼───┐   ┌────────▼─────────────────────┐
                    │ respond from  │   │ 3. LLM (traductor)           │
                    │ typed store   │   │   forced typed output:       │
                    │ (cheap/det.)  │   │   (rel …) (command …) (think)│
                    └───────┬───────┘   └────────┬─────────────────────┘
                            │                    │
                            │           ┌────────▼─────────────────────┐
                            │           │ 4. GATE  S_i / V_i           │
                            │           │  unsinnig? → reject (no store)│
                            │           │  sinnlos?  → flag             │
                            │           │  sinnvoll? → continue         │
                            │           └────────┬─────────────────────┘
                            │                    │
                            │           ┌────────▼─────────────────────┐
                            │           │ 5. MATERIALIZE               │
                            │           │  rel → edge                  │
                            │           │  command → tool call         │
                            │           │  atom → sldb doc + provenance│
                            │           └────────┬─────────────────────┘
                            │                    │
                            └─────────┬──────────┘
                                      │
                        ┌─────────────▼──────────────┐
                        │  6. RESPOND + log energy    │  (g_hits / llm_calls)
                        └─────────────────────────────┘
```

## Los 3 elementos que lo hacen "agente" (no wiki)
1. **G-first**: consultar el grafo tipado ANTES que el LLM (paso 2).
2. **Contrato de salida tipado**: el LLM solo puede emitir `(rel/command/think)` (paso 3).
3. **Gate S_i/V_i**: distinguir *falso* de *unsinnig* antes de guardar (paso 4).

Sin esos 3 = una KB bonita. Con ellos = un agente que crece auditable.

## Mapa a los repos existentes
| Paso | Pieza | Repo |
|---|---|---|
| 1 parse→query | StructuredQuery DSL | `tools/kgdb/query/language.py` |
| 2 ask graph | kgdb executor | `tools/kgdb` |
| 3 typed output | s-expr kinds | `hum/agent/ir.lisp` |
| 4 gate | proposition lifecycle | `Matrix/spec/proposition_lifecycle.yaml` |
| 5 materialize | sldb doc + Source→Sample→Atom | `tools/sldb`, `knowledge/spec/KB_SYSTEM_SPEC.md` |
| 6 energy | g_hits/llm_calls | `hum/agent/core.lisp` |

## Principio de crecimiento
Cada cosa aprendida = átomo tipado con provenance, NO parámetro opaco.
`Source (path+hash) → Sample (cut) → Atom (5WH1+, S_i/V_i, grounding)`.
El grafo es la memoria; el LLM nunca es la fuente de verdad.
