---
id: task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo
status: ready_for_testing
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo
current_node: checklist-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-closeout-ready
history:
- operator-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-activate
- operator-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-ready-for-testing
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-execution-ready
- checklist-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-testing-ready
- checklist-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms: []
closeout_evidence_verified: false
pill_graduation_verified: true
---

# Chat: nueva conversacion, ficha del lead y stepper del flujo

## Rationale

_Explain why this task exists or the business driver behind it._

El equipo de Vitali prueba el chat web y ve badges de runtime en vez del estado de negocio; la sesion vive en localStorage sin forma de reiniciarla (queja del 03/09: 'se queda pegado con el contexto').

## Goal

_Describe the concrete result this task must produce._

En frontends/chat: boton 'Nueva conversacion' que rota la sesion; ficha del lead (para quien busca, proyecto de interes, dia y bloque preferido, modalidad, email, telefono) derivada de traits y slots del ultimo turno; stepper del flujo (saludo, calificacion, agendar, datos, cierre) con el paso activo resaltado, leido de /api/flow; badges tecnicos del timeline reemplazados por el nombre humano del paso.

## Scope

_State what is in scope and what is out of scope._

frontends/chat/index.html, frontends/shared/theme.css, frontends/chat/app.py (si hace falta exponer slots/traits resueltos en /api/chat e /api/history), frontends/UI-GUIDE.md seccion 2, tests/ui. No tocar el runtime ni la KB.

## Implementation Path

_Outline the expected implementation route or affected surface._

1) boton que borra kb_chat_session y recarga. 2) campo en /api/chat e /api/history con flow_slots + traits resueltos. 3) ficha del lead en el sidebar. 4) stepper arriba del timeline a partir de /api/flow (orden por grafo, raiz primero). 5) UI-GUIDE + tests Playwright por data-testid.

## Validation

_List the checks required before this task can close._

- SKIP_LLM_TESTS=1 python -m pytest tests/unit tests/integration -q
- python -m pytest tests/ui -q

## Done When

_Name the observable condition that makes the task complete._

Un tester abre /, pulsa Nueva conversacion, conversa hasta el cierre y ve en la ficha su dia preferido, modalidad, email y telefono, y en el stepper el paso activo en cada turno; tests/ui verdes.
