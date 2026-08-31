---
id: task-modo-editor-de-atoms-en-la-ui
status: deferred
summary: ''
tags:
- workspace:desk
- artifact:task
- source:decision
routine: ''
current_node: ''
history: []
references: []
depends_on: []
pills: []
files: []
checklists: []
task_type: ''
inherits_from: []
inherit_acceptance_context: false
atoms: []
---

# Modo editor de atoms en la UI (mindmap)

## Rationale

_Explain why this task exists or the business driver behind it._

Decision del owner: la UI de Vitali queda read-only por ahora, pero se quiere un modo editor persistido mas adelante. Hoy no existe capa de escritura de atoms (kb_agent solo tiene readers; PUT/PATCH/POST sobre /api/atom/{id} devuelven 405).

## Goal

_Describe the concrete result this task must produce._

Agregar un modo editor a la vista mindmap que permita editar atoms y persistirlos en el store SLDB de la KB.

## Scope

_State what is in scope and what is out of scope._

Modal de edicion en frontends/taxonomy/ + endpoint PATCH /api/atom/{id} + capa de escritura sobre el store (.sldb de la KB activa) con re-indexado. Definir antes si sldb expone API de escritura o si se escribe el Markdown fuente y se reindexa. Respetar el pipeline spec->atoms del repo: la edicion en caliente no debe romper la trazabilidad del store. Re-habilitar las acciones del toolbar (borrar, +hijo, +hermano, link) solo cuando persistan de verdad.

## Implementation Path

_Outline the expected implementation route or affected surface._



## Validation

_List the checks required before this task can close._

- tests en tests/ui/test_mindmap.py: editar -> guardar -> recargar -> persiste
- sldb stores check --store <kb>/.sldb PASS despues de editar

## Done When

_Name the observable condition that makes the task complete._

La UI permite editar un atom, el cambio persiste en el Markdown fuente y el store reindexado, y recargar muestra el atom editado; documentado en frontends/UI-GUIDE.md.
