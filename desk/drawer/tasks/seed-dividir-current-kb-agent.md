---
id: seed-dividir-current-kb-agent
title: Dividir current-kb-agent en runtime + knowledge
status: open
tags:
- seed
- spec2viz
- diagramas
---

## Semilla

Hoy `current-kb-agent` mezcla dos mundos en un solo diagrama, y por eso la
sección "Backend · Knowledge" del catálogo quedó con una sola vista.

Partir el spec en dos vistas honestas:

- `current-runtime` → motor conversacional: orchestrator, agent (decide_turn
  policy), state_machine, llm (Conversador/TraitMapper), perfilador, tools,
  project_config, cli, pii.
- `current-knowledge` → subsistema de conocimiento: ontologizador
  (compiler + sldb_reader + kgdb_reader + compiled_document), reflector
  (reader + generator), models/knowledge (10 modelos tipados), models_sql.

Reasignar categorías en `desk/spec2viz/catalog.yml`:
- `current-runtime` -> Backend · Runtime
- `current-knowledge` -> Backend · Knowledge

## Nota

Deriva de la Fase A de seed-recomponer-spec2viz-y-atoms.
Scope acotado; hacer cuando se retome spec2viz.
