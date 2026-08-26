---
id: atom-kgdb-grafo-de-flujo
title: 'KGDB: Grafo de Flujo'
five_wh_one_plus: what
tags:
- layer:knowledge
- role:data
- family:conversation
provenance: architecture-audit
---

# KGDB: Grafo de Flujo

## Answer

Capa de base de datos de grafo en memoria (NetworkX persistido). Indexa las relaciones semánticas entre los nodos de `ConversationStep` (ej. `flows_to`, `grounded_by`), permitiendo al Ontologizador trazar la ruta de la conversación de forma programática.
