---
id: atom-orquestador-hub
title: Orquestador (Hub Central)
five_wh_one_plus: what
tags:
- layer:runtime
- role:boundary
provenance: architecture-audit
---

# Orquestador (Hub Central)

## Answer

Punto de entrada unificado (`Orchestrator.handle_turn`). Instancia la sesión SQL, resuelve el usuario (`ensure_user`) y la conversación activa (`_resolve_conversation`), inicializa el RouterStateMachine, delega la decisión a la policy pura, ejecuta las tool calls locales, delega la redacción al Conversador, aplica el policy gate al borrador antes de emitir, persiste el historial purgado y el trail del turno en SQL (con `conversation_id`), y dispara asíncronamente al Perfilador a través del Event Bus. `ensure_user` unifica identidad por teléfono cuando `identity_key='phone'` y tolera la carrera SELECT-then-INSERT de requests concurrentes del mismo usuario nuevo (dos pestañas, doble tap, reintento de webhook): si el INSERT viola el UNIQUE de `external_id`, hace rollback y re-SELECT del ganador en vez de reventar el turno con un 500. `_resolve_conversation` reusa la conversación abierta más reciente o abre una nueva cuando la anterior superó el TTL de inactividad (`tuning.conversation_idle_ttl_s`), de modo que el historial inyectado al prompt (filtrado por `conversation_id`) no cruza el límite de una conversación vieja.
