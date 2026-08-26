---
id: atom-ontologizador-context-compiler
title: Ontologizador (Context Compiler)
five_wh_one_plus: what
tags:
- layer:runtime
- role:engine
provenance: architecture-audit
---

# Ontologizador (Context Compiler)

## Answer

Motor de compilación determinista. Lee TODA la base de conocimiento tipada (los 10 modelos) desde SLDB, y extrae el nodo actual del grafo de ConversationStep (desde KGDB) para ensamblar el `CompiledDocument` que representa el estado exacto y los hechos relevantes para el turno.
