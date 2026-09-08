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

Motor de compilacion determinista del paquete kb_agent/knowledge. La clase ContextCompiler lee la base de conocimiento tipada desde el store por KnowledgeOperations (un pron.World por proceso, kb_agent/knowledge/world.py) y resuelve el step activo, sus transiciones (aristas transitions_to) y su grounding (aristas grounded_by + documentos con el tag del step) con ConversationFlow (kb_agent/knowledge/flow.py) sobre el grafo tipado de kgdb, para ensamblar el CompiledDocument del turno. La seleccion semantica de atoms (_semantic_candidates) rankea con el DocumentIndex de pron (vectores por hash_c en <kb>/.pron/, fuera del frontmatter); el mismo indice lo reusa el Perfilador (rank_among) para su pre-filtro top-k.
