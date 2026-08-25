---
id: task-implementar-modelos-de-identidad-sql
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-modelos-de-identidad-sql
current_node: checklist-task-implementar-modelos-de-identidad-sql-execution-ready
history: []
references: []
depends_on: []  # base: sin dependencias
pills: []
files: []
checklists:
- checklist-task-implementar-modelos-de-identidad-sql-execution-ready
- checklist-task-implementar-modelos-de-identidad-sql-testing-ready
- checklist-task-implementar-modelos-de-identidad-sql-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-sql-capa-identidad-y-estado
---

# Implementar Modelos de Identidad SQL

## Rationale

Aísla la identidad transaccional (PII) del conocimiento semántico. Es la tabla base sobre la que se apoyan sesión, historial y perfilado.

## Goal

_Describe the concrete result this task must produce._

Tablas Users y UserTraits en SQLAlchemy.

## Scope

EN: Modelos SQLAlchemy `Users` y `UserTraits`.
FUERA: SessionState, ChatHistory (otra tarea), lógica de extracción de traits.

## Implementation Path

`kb_agent/models_sql/identity.py`

Contrato de esquema:
- `Users`: id (PK, int), external_id (str, unique — el ID del canal ej. wa:+569...), channel (str), created_at (datetime).
- `UserTraits`: tabla N:M. user_id (FK->Users.id), trait_id (str, apunta al id de un TraitAtom en SLDB, NO es FK), confidence (float 0-1), source (str), created_at. PK compuesta (user_id, trait_id).

## Validation

- `pytest` levanta SQLite `:memory:`, crea un User + 2 UserTraits al mismo user_id y afirma la relación N:M.
- Afirmar que trait_id acepta strings arbitrarios (no valida contra SLDB en esta capa).

## Done When

Los modelos crean el schema sin errores y el test N:M en memoria pasa en verde.
