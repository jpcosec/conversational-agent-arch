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

Punto de entrada unificado (`Orchestrator.handle_turn`). Instancia la sesión SQL, inicializa el RouterStateMachine, delega la decisión a la policy pura, ejecuta las tool calls locales, delega la redacción al Conversador, persiste el historial purgado en SQL, y dispara asíncronamente al Perfilador a través del Event Bus.
