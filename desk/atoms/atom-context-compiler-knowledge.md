---
id: atom-context-compiler-knowledge
title: Context Compiler (knowledge)
five_wh_one_plus: what
tags:
- layer:runtime
- role:engine
provenance: architecture-audit
---

# Context Compiler (knowledge)

## Answer

Motor de compilacion determinista del paquete kb_agent/knowledge. La clase ContextCompiler lee TODA la base de conocimiento tipada (los 10 modelos) desde SLDB via SLDBReader y extrae el nodo actual del grafo de ConversationStep (desde KGDB via kgdb_reader) para ensamblar el CompiledDocument que representa el estado exacto y los hechos relevantes para el turno. La seleccion semantica de atoms (_semantic_candidates) rankea por similitud coseno reusando el embedder cacheado del proceso; el mismo patron lo reusa el Perfilador para su pre-filtro top-k.
