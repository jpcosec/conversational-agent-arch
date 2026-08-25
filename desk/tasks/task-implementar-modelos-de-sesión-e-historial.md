---
id: task-implementar-modelos-de-sesión-e-historial
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-modelos-de-sesión-e-historial
current_node: checklist-task-implementar-modelos-de-sesión-e-historial-execution-ready
history: []
references: []
depends_on:
- task-implementar-modelos-de-identidad-sql
pills: []
files: []
checklists:
- checklist-task-implementar-modelos-de-sesión-e-historial-execution-ready
- checklist-task-implementar-modelos-de-sesión-e-historial-testing-ready
- checklist-task-implementar-modelos-de-sesión-e-historial-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-sql-capa-identidad-y-estado
- atom-historial-de-conversacion-sin-pii
- atom-aislamiento-estricto-de-pii
---

# Implementar Modelos de Sesión e Historial

## Rationale

Persiste el estado del nodo de la máquina de estados por usuario y el historial de turnos que alimenta al Reflector.

## Goal

_Describe the concrete result this task must produce._

Tablas SessionState y ChatHistory.

## Scope

EN: Modelos `SessionState` y `ChatHistory`.
FUERA: la lógica de scrubbing de PII (tarea aparte), lectura batch.

## Implementation Path

`kb_agent/models_sql/session.py`

Contrato de esquema:
- `SessionState`: user_id (FK->Users.id, unique), current_node (str — uno de: idle, buffering, evaluating_context, drafting_response, waiting_tool, breakpoint_miss), buffer (JSON — mensajes retenidos por debounce), updated_at.
- `ChatHistory`: id (PK), user_id (FK->Users.id), role (str: user|assistant|system), content (str), pii_scrubbed (bool, default False), created_at. Indice por (user_id, created_at).

Ambigüedad resuelta: `current_node` usa exactamente los nombres de nodo de la SM del router; `pii_scrubbed` marca si la fila ya pasó por el scrubber (el Reflector SOLO lee filas con pii_scrubbed=True).

## Validation

- `pytest` en SQLite `:memory:`: crear sesión, transicionar current_node y afirmar persistencia.
- Afirmar que ChatHistory por defecto nace con pii_scrubbed=False.

## Done When

Ambas tablas crean schema; los tests de transición de nodo y default de pii_scrubbed pasan.
