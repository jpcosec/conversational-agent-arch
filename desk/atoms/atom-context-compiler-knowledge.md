---
id: atom-context-compiler-knowledge
title: Context Compiler (Knowledge)
five_wh_one_plus: what
tags:
- layer:runtime
- role:engine
provenance: architecture-audit
---

# Context Compiler (Knowledge)

## Answer

Motor de compilación determinista. Lee TODA la base de conocimiento tipada (los 10 modelos) desde SLDB, y extrae el nodo actual del grafo de ConversationStep (desde KGDB) para ensamblar el `CompiledDocument` que representa el estado exacto y los hechos relevantes para el turno.
