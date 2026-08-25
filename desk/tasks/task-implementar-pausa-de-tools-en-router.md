---
id: task-implementar-pausa-de-tools-en-router
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-pausa-de-tools-en-router
current_node: checklist-task-implementar-pausa-de-tools-en-router-execution-ready
history: []
references: []
depends_on:
- task-implementar-core-state-machine-del-router
pills:
- desk/contexts/pill-maquina-de-estados-pausa-en-tool-calling.md
files: []
checklists:
- checklist-task-implementar-pausa-de-tools-en-router-execution-ready
- checklist-task-implementar-pausa-de-tools-en-router-testing-ready
- checklist-task-implementar-pausa-de-tools-en-router-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-turno-de-sistema-system-turn
---

# Implementar Pausa de Tools en Router

## Rationale

Permite que el Conversador use herramientas externas (APIs) sin romper el flujo determinista de la conversación.

## Goal

_Describe the concrete result this task must produce._

Pausar la SM en waiting_tool y reanudar con System Turn.

## Scope

EN: Nodo `waiting_tool`, pausa/reanudación, reinyección del JSON como System Turn, y timeout.
FUERA: la ejecución real de las APIs (eso vive en tool-calling estructurado).

## Implementation Path

`kb_chat_ui/state_machine.py` (extiende la SM base)

Ambigüedad resuelta:
- Al emitir un function_call, drafting_response -> waiting_tool (SM pausada, no acepta nuevo turno de usuario: se encola).
- El retorno JSON de la tool se inserta en ChatHistory con role='system' (System Turn) y se reanuda waiting_tool -> drafting_response.
- TIMEOUT: si la tool no responde en `TOOL_TIMEOUT_MS` (default 15000), transicionar waiting_tool -> drafting_response con un System Turn de error, para que el Conversador informe la falla sin colgarse.
- Concurrencia: mensajes de usuario que lleguen en waiting_tool se guardan en SessionState.buffer, no se procesan hasta volver a idle.

## Validation

- `pytest`: simular function_call, inyectar retorno JSON y afirmar reanudación con System Turn role='system'.
- Simular tool colgada y afirmar transición por timeout a drafting_response con System Turn de error.
- Afirmar que un mensaje de usuario en waiting_tool queda encolado, no procesado.

## Done When

Pausa/reanudación, timeout y encolado de concurrencia pasan sus tests.
