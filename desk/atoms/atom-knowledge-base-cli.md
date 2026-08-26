---
id: atom-knowledge-base-cli
title: Knowledge Base CLI
five_wh_one_plus: what
tags:
- domain:self.architecture.backend
- layer:cli
- system:kb-agent
- topic:retrieval
provenance: null
---

# Knowledge Base CLI

## Answer

Puente semántico (knowledge_base/) que expone la KB a los agentes vía CLI y la clase KnowledgeOperations, uniendo SLDB (acceso a átomos), KGDB (traversal del grafo) y SQL (estado de sesión y traits). Comandos: explore (búsqueda), show (átomo por id), step next (siguiente ConversationStep por usuario), traits (traits del usuario), self (identidad), context (contexto compilado por usuario) y propose (materializa un átomo tipado desde YAML). Se invoca con python -m knowledge_base --kb <path>.
