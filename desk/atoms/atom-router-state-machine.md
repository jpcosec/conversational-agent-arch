---
id: atom-router-state-machine
title: Router State Machine
five_wh_one_plus: what
tags:
- layer:runtime
- role:boundary
provenance: architecture-audit
---

# Router State Machine

## Answer

Máquina de estados técnica (`RouterStateMachine`) con 6 nodos (IDLE, BUFFERING, EVALUATING_CONTEXT, DRAFTING_RESPONSE, WAITING_TOOL, BREAKPOINT_MISS). Rutea la petición hacia el Ontologizador y pausa la ejecución síncrona en `WAITING_TOOL` mientras el Orquestador ejecuta una herramienta.
