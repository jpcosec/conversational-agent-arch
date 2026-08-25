---
id: task-implementar-router-de-máquina-de-estados
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-router-de-máquina-de-estados
current_node: checklist-task-implementar-router-de-máquina-de-estados-execution-ready
history: []
references: []
depends_on: []
pills:
- desk/contexts/pill-maquina-de-estados-pausa-en-tool-calling.md
files: []
checklists:
- checklist-task-implementar-router-de-máquina-de-estados-execution-ready
- checklist-task-implementar-router-de-máquina-de-estados-testing-ready
- checklist-task-implementar-router-de-máquina-de-estados-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-api-gateway-y-state-router
- atom-debounce-buffer-agrupacion
- atom-trigger-sintetico-cron
- atom-turno-de-sistema-system-turn
---

# Implementar Router de Máquina de Estados

## Rationale

_Explain why this task exists or the business driver behind it._

Para orquestar el flujo conversacional no lineal y la pausa de tools

## Goal

_Describe the concrete result this task must produce._

Construir State Router con debounce y manejo de tool-calling

## Scope

_State what is in scope and what is out of scope._

kb_chat_ui/main.py

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- 

## Done When

_Name the observable condition that makes the task complete._
- [ ] Implementar transición de Error/Timeout si una API externa se queda pegada en 'waiting_tool'.
- [ ] Manejar concurrencia: retener en cola (buffer) los mensajes del usuario si llegan mientras la máquina está bloqueada compilando o en 'waiting_tool'.
- [ ] Resolver colisiones: lógica determinista si el trigger sintético del CRON coincide en el mismo instante que un input de usuario.
