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

Ambigüedad resuelta — contrato del trigger sintético CRON (ver atom-trigger-sintetico-cron): el CRON inyecta el payload `{scenario: str, user_id: int}` donde `scenario` es un tag de dominio válido. Al entrar en `idle`, ese `scenario` se propaga al Compilador de Contexto como el escenario proactivo del turno (mismo campo que consume el compilador).

Ambigüedad resuelta — conducta determinista del CRON en nodo no-idle: si el trigger CRON llega cuando `current_node` != `idle`, se DESCARTA (drop silencioso con log de nivel info); NO se encola ni se reintenta. Un turno activo nunca es interrumpido por un trigger proactivo.

Nota: este enum de 6 nodos es la fuente de verdad; SessionState.current_node debe incluir buffering, waiting_tool y breakpoint_miss.

## Validation

- `pytest`: simular input de usuario en idle y afirmar la secuencia idle->eval->draft->idle.
- Afirmar que un trigger CRON con payload `{scenario, user_id}` en `idle` propaga `scenario` al compilador y arranca el turno proactivo.
- Afirmar que un trigger CRON recibido en un nodo != idle es DESCARTADO (drop silencioso): no cambia current_node, no se encola, y el turno activo sigue intacto.

## Done When

Las 3 transiciones base pasan y el trigger CRON respeta la regla de solo-idle.
