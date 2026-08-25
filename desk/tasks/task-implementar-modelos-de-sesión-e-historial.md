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
- `SessionState`: user_id (FK->Users.id, unique), current_node (str — uno de: idle, buffering, evaluating_context, drafting_response, waiting_tool, breakpoint_miss), active_domain (str, nullable — tag de dominio activo de la sesión, ej. 'pizza'; null usa el default de KB_ROOT), buffer (JSON con dos claves separadas: `{"debounce": [...], "tool_wait": [...]}` — ver nota de doble propósito abajo), updated_at.
- `ChatHistory`: id (PK), user_id (FK->Users.id), role (str: user|assistant|system), content (str), pii_scrubbed (bool, default False), created_at. Indice por (user_id, created_at).

Ambigüedad resuelta: `current_node` usa exactamente los nombres de nodo de la SM del router; `pii_scrubbed` marca si la fila ya pasó por el scrubber (el Reflector SOLO lee filas con pii_scrubbed=True).

Ambigüedad resuelta — `buffer` tiene dos claves con semánticas independientes para evitar colisión entre debounce y pausa de tools:
- `buffer.debounce` (lista): mensajes de usuario retenidos durante la ventana de debounce en el nodo `buffering` (ver task-implementar-debounce-buffer-en-router).
- `buffer.tool_wait` (lista): mensajes de usuario encolados mientras la SM está en `waiting_tool` (ver task-implementar-pausa-de-tools-en-router).
Ambas claves nacen como listas vacías; ningún consumidor escribe en la clave del otro.

Ambigüedad resuelta — `active_domain` es el origen del `scenario` que consume el Compilador de Contexto (ver task-implementar-compilador-de-contexto): en turno normal el compilador toma `SessionState.active_domain`; si es null usa el default de KB_ROOT.

## Validation

- `pytest` en SQLite `:memory:`: crear sesión, transicionar current_node y afirmar persistencia.
- Afirmar que `active_domain` acepta null y un string de dominio, y persiste correctamente.
- Afirmar que `buffer` nace como `{"debounce": [], "tool_wait": []}` y que escribir en una clave no afecta la otra.
- Afirmar que ChatHistory por defecto nace con pii_scrubbed=False.

## Done When

Ambas tablas crean schema; los tests de transición de nodo y default de pii_scrubbed pasan.
