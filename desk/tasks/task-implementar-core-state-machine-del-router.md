---
id: task-implementar-core-state-machine-del-router
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-core-state-machine-del-router
current_node: checklist-task-implementar-core-state-machine-del-router-execution-ready
history: []
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-implementar-core-state-machine-del-router-execution-ready
- checklist-task-implementar-core-state-machine-del-router-testing-ready
- checklist-task-implementar-core-state-machine-del-router-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-api-gateway-y-state-router
- atom-trigger-sintetico-cron
---

# Implementar Core State Machine del Router

## Rationale

Es el esqueleto de orquestación. Sin la SM base, ni debounce ni pausa de tools tienen dónde engancharse.

## Goal

_Describe the concrete result this task must produce._

Conectar las transiciones básicas idle -> eval -> draft -> idle.

## Scope

EN: Definición de nodos y transiciones base + enganche del trigger sintético (CRON).
FUERA: buffering (debounce) y pausa por tools (tareas hijas).

## Implementation Path

`kb_chat_ui/state_machine.py`

Ambigüedad resuelta — definición exacta de nodos (enum canónico compartido con SessionState.current_node):
- `idle`: sin turno activo; único nodo que acepta trigger sintético CRON.
- `buffering`: reteniendo mensajes en ventana debounce (definido en su tarea hija).
- `evaluating_context` (eval): invoca al Ontologizador para compilar contexto.
- `drafting_response` (draft): invoca al Conversador con el contexto compilado.
- `waiting_tool`: pausa por function_call (definido en su tarea hija).
- `breakpoint_miss`: nodo de quiebre cuando el contexto compilado llega con is_empty=true; el Conversador admite desconocimiento y NO alucina. Se entra desde evaluating_context (is_empty=true) y se sale a drafting_response para emitir la respuesta de desconocimiento.
Transiciones base: idle -> [buffering] -> evaluating_context -> (drafting_response | breakpoint_miss -> drafting_response) -> idle.
El input de usuario entra a `buffering` cuando la tarea de debounce está activa; si no, va directo a evaluating_context.
El trigger CRON entra SOLO en idle y fuerza evaluating_context con un escenario proactivo.

Nota: este enum de 6 nodos es la fuente de verdad; SessionState.current_node debe incluir buffering, waiting_tool y breakpoint_miss.

## Validation

- `pytest`: simular input de usuario en idle y afirmar la secuencia idle->eval->draft->idle.
- Afirmar que un trigger CRON en un nodo distinto de idle es ignorado/encolado (no interrumpe turno activo).

## Done When

Las 3 transiciones base pasan y el trigger CRON respeta la regla de solo-idle.
