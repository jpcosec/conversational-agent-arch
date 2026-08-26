---
id: atom-grafo-de-flujo-conversacional
title: Grafo de Flujo Conversacional
five_wh_one_plus: what
tags:
- domain:self.architecture.backend
- layer:runtime
- system:kb-agent
- topic:conversation-flow
provenance: null
---

# Grafo de Flujo Conversacional

## Answer

El flujo de conversación modelado como grafo dirigido de ConversationStep. Cada nodo declara un kind (interaccion_simple, obtencion_datos, handout, llamado_tool) que determina su tratamiento en runtime, los slots requeridos a recolectar, las transiciones permitidas (allowed_transitions vía tags conversation:steps.<x>) y los átomos que lo groundean. El Ontologizador usa el step actual para acotar el contexto compilado; el editor visual (frontends/flow_editor) materializa este grafo desde el store SLDB a flow.json.
