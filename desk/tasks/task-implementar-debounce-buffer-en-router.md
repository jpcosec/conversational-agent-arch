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

EN: Nodo `buffering` + ventana de debounce que agrupa mensajes.
FUERA: transiciones base (ya existen), pausa por tools.

## Implementation Path

`kb_chat_ui/state_machine.py` (extiende la SM base)

Ambigüedad resuelta:
- Ventana de debounce = 1000 ms (constante configurable `DEBOUNCE_MS`).
- Cada mensaje nuevo dentro de la ventana REINICIA el timer (trailing debounce).
- Al expirar, se concatenan los mensajes en orden y se transiciona buffering -> evaluating_context UNA sola vez.
- El buffer se persiste en SessionState.buffer para sobrevivir reinicios.

## Validation

- `pytest` con reloj mockeado: inyectar 5 mensajes en <1s y afirmar que el Ontologizador se invocó exactamente 1 vez con los 5 concatenados.
- Afirmar que un mensaje aislado (sin ráfaga) dispara tras 1s.

## Done When

El debounce agrupa ráfagas en 1 sola compilación y el test de 5-en-1 pasa.
