---
id: task-implementar-perfilador-asincrono
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-perfilador-asincrono
current_node: checklist-task-implementar-perfilador-asincrono-execution-ready
history: []
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-implementar-perfilador-asincrono-execution-ready
- checklist-task-implementar-perfilador-asincrono-testing-ready
- checklist-task-implementar-perfilador-asincrono-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-perfilador-asincrono
- atom-trait-atom
---

# Implementar Perfilador Asincrono

## Rationale

_Explain why this task exists or the business driver behind it._

Para enriquecer perfiles mediante traits sin sumar latencia

## Goal

_Describe the concrete result this task must produce._

Crear worker background que extrae traits y los guarda en SQL

## Scope

_State what is in scope and what is out of scope._

kb_agent/perfilador.py

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- 

## Done When

_Name the observable condition that makes the task complete._
- [ ] Definir y configurar el mecanismo exacto de disparo asíncrono (ej. Event Bus o Redis Queue).

## Estrategia de Testing Asignada
- [ ] **Test de Extracción Asíncrona**: Inyectar un *Golden Transcript* (log simulado) donde el usuario revela una característica explícita (ej. 'soy vegetariano').
- [ ] Ejecutar el worker del Perfilador sobre el log.
- [ ] Realizar una consulta SQL para afirmar (`assert`) que el grafo relacional creó exitosamente el edge `user_id -> trait-vegetariano`.
