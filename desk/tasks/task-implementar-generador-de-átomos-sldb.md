---
id: task-implementar-generador-de-átomos-sldb
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-generador-de-átomos-sldb
current_node: checklist-task-implementar-generador-de-átomos-sldb-execution-ready
history: []
references: []
depends_on:
- task-implementar-batch-reader-del-reflector
- task-implementar-conector-sldb-del-ontologizador
pills: []
files: []
checklists:
- checklist-task-implementar-generador-de-átomos-sldb-execution-ready
- checklist-task-implementar-generador-de-átomos-sldb-testing-ready
- checklist-task-implementar-generador-de-átomos-sldb-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-domain-atom
- atom-rule-atom
---

# Implementar Generador de Átomos SLDB

## Rationale

Engrosa la base de conocimiento de forma autónoma materializando patrones recurrentes como átomos tipados.

## Goal

_Describe the concrete result this task must produce._

Convertir patrones históricos en archivos físicos .md.

## Scope

EN: Detectar patrones en los lotes limpios y escribir nuevos DomainAtom/RuleAtom en SLDB.
FUERA: lectura de historial (batch-reader), consumo por el Ontologizador.

## Implementation Path

`kb_agent/reflector/generator.py`

Ambigüedad resuelta:
- Escribe átomos usando la MISMA vía que el CLI (`deskops add atom` / API SLDB), respetando tag-namespaces válidos.
- Todo átomo generado nace con tag `source:reflector` y estado `proposed` (requiere revisión humana antes de activarse — no auto-publica a producción).
- Deduplicación: no crea un átomo si ya existe uno con el mismo contenido semántico.

## Validation

- `pytest`: alimentar un lote sintético con un patrón claro y afirmar que se escribió un archivo .md nuevo en `.sldb_test/` con tag source:reflector y estado proposed.
- Afirmar que reejecutar con el mismo patrón NO duplica el átomo.

## Done When

Genera átomos tipados marcados como proposed, sin duplicar, en el store de prueba.
