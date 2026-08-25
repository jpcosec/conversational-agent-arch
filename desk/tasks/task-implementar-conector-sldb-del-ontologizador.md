---
id: task-implementar-conector-sldb-del-ontologizador
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-conector-sldb-del-ontologizador
current_node: checklist-task-implementar-conector-sldb-del-ontologizador-execution-ready
history: []
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-implementar-conector-sldb-del-ontologizador-execution-ready
- checklist-task-implementar-conector-sldb-del-ontologizador-testing-ready
- checklist-task-implementar-conector-sldb-del-ontologizador-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-ontologizador-context-compiler
- atom-sldb-base-conocimiento-semantica
- atom-tool-atom
---

# Implementar Conector SLDB del Ontologizador

## Rationale

Aisla la lectura de SLDB del resto del sistema. Es la fuente de conocimiento semántico para compilar contexto.

## Goal

_Describe the concrete result this task must produce._

Leer de forma segura rules, tools y domains desde SLDB.

## Scope

EN: Cliente de lectura que trae RuleAtoms, ToolAtoms y DomainAtoms desde SLDB.
FUERA: la lógica de filtrado/compilación del subgrafo (tarea compilador).

## Implementation Path

`kb_agent/ontologizador/sldb_reader.py`

Ambigüedad resuelta:
- Usa el CLI/API de SLDB (no lee .md a mano).
- Expone `fetch(atom_type, filters) -> list[Atom]` para type in {rule, tool, domain, trait}.
- Cada Atom retornado incluye: id, type, tags, body. Los ToolAtoms además exponen su JSON schema crudo.
- Config `KB_ROOT` parametriza el store SLDB destino (permite swap multi-dominio).

## Validation

- `pytest` contra un `.sldb_test/` sembrado: afirmar que fetch('tool') devuelve solo ToolAtoms con su JSON schema legible.
- Afirmar que cambiar KB_ROOT cambia el set de átomos leído (multi-dominio).

## Done When

fetch() lee cada tipo de átomo desde SLDB y el test contra el store sembrado pasa.
