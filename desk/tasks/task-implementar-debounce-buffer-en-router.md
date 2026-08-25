---
id: task-implementar-debounce-buffer-en-router
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-debounce-buffer-en-router
current_node: checklist-task-implementar-debounce-buffer-en-router-execution-ready
history: []
references: []
depends_on:
- task-implementar-core-state-machine-del-router
pills: []
files: []
checklists:
- checklist-task-implementar-debounce-buffer-en-router-execution-ready
- checklist-task-implementar-debounce-buffer-en-router-testing-ready
- checklist-task-implementar-debounce-buffer-en-router-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-debounce-buffer-agrupacion
---

# Implementar Debounce Buffer en Router

## Rationale

Evita llamadas redundantes al Ontologizador cuando el usuario manda ráfagas de mensajes cortos (típico en WhatsApp).

## Goal

_Describe the concrete result this task must produce._

Retener mensajes por 1s para agrupar ráfagas antes de transicionar.

## Scope

EN: Nodo `buffering`, la transición de ENTRADA `idle -> buffering`, el self-loop de reinicio del timer, y la salida `buffering -> evaluating_context`.
FUERA: transiciones base ajenas al buffering (ya existen), pausa por tools.

## Implementation Path

`kb_chat_ui/state_machine.py` (extiende la SM base)

Ambigüedad resuelta:
- ENTRADA a buffering: un `mensaje_usuario` recibido estando en `idle` dispara la transición `idle -> buffering` (evento `mensaje_usuario`). Ese primer mensaje inicializa el buffer y ARRANCA el timer de `DEBOUNCE_MS`. Esta es la única vía de entrada a `buffering`; el trigger sintético CRON NO entra a buffering (va directo a `evaluating_context` según la SM base).
- Ventana de debounce = 1000 ms (constante configurable `DEBOUNCE_MS`).
- Mientras se está en `buffering`, cada mensaje adicional dispara el self-loop `buffering -> buffering` (evento `mensaje_adicional`): agrega el texto al buffer y REINICIA el timer a `DEBOUNCE_MS` completos (trailing debounce; NO es una ventana fija desde el primer mensaje).
- Al expirar el timer sin nuevos mensajes (evento `timeout_buffer`), se concatenan los mensajes en orden y se transiciona `buffering -> evaluating_context` UNA sola vez.
- El buffer se persiste en `SessionState.buffer["debounce"]` (lista) para sobrevivir reinicios. Esta tarea escribe SOLO en la clave `debounce`; la clave `tool_wait` es propiedad exclusiva de task-implementar-pausa-de-tools-en-router.

Consistencia con la SM base: en `task-implementar-core-state-machine-del-router` la ruta es `idle -> [buffering] -> evaluating_context`; esta tarea materializa el corchete `[buffering]` y sus tres eventos (`mensaje_usuario`, `mensaje_adicional`, `timeout_buffer`).

## Validation

- `pytest` con reloj mockeado: partir en `idle`, inyectar el 1er mensaje y afirmar la transición `idle -> buffering` con timer armado.
- Inyectar 5 mensajes en <1s y afirmar que el Ontologizador se invocó exactamente 1 vez con los 5 concatenados, y que cada mensaje reinició el timer (trailing).
- Afirmar que un mensaje aislado (sin ráfaga) dispara `buffering -> evaluating_context` tras exactamente `DEBOUNCE_MS`.

## Done When

El debounce agrupa ráfagas en 1 sola compilación y el test de 5-en-1 pasa.
