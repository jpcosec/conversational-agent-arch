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

Ambigüedad resuelta — definición exacta de nodos:
- `idle`: sin turno activo; único nodo que acepta trigger sintético CRON.
- `evaluating_context` (eval): invoca al Ontologizador para compilar contexto.
- `drafting_response` (draft): invoca al Conversador con el contexto compilado.
Transiciones: idle -> evaluating_context (por input de usuario o CRON) -> drafting_response -> idle.
El trigger CRON entra SOLO en idle y fuerza evaluating_context con un escenario proactivo.

## Validation

- `pytest`: simular input de usuario en idle y afirmar la secuencia idle->eval->draft->idle.
- Afirmar que un trigger CRON en un nodo distinto de idle es ignorado/encolado (no interrumpe turno activo).

## Done When

Las 3 transiciones base pasan y el trigger CRON respeta la regla de solo-idle.
