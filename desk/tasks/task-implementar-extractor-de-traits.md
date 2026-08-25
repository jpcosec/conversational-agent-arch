---
id: task-implementar-extractor-de-traits
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-extractor-de-traits
current_node: checklist-task-implementar-extractor-de-traits-execution-ready
history: []
references: []
depends_on:
- task-implementar-modelos-de-identidad-sql
- task-implementar-listener-asíncrono-del-perfilador
- task-implementar-conector-sldb-del-ontologizador
pills: []
files: []
checklists:
- checklist-task-implementar-extractor-de-traits-execution-ready
- checklist-task-implementar-extractor-de-traits-testing-ready
- checklist-task-implementar-extractor-de-traits-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-trait-atom
- atom-aislamiento-estricto-de-pii
---

# Implementar Extractor de Traits

## Rationale

Convierte señales explícitas del usuario en punteros a TraitAtoms universales, sin guardar PII.

## Goal

_Describe the concrete result this task must produce._

Analizar texto y mapear a TraitAtoms en la tabla SQL.

## Scope

EN: Analizar texto de turno, mapear a trait_ids existentes y hacer UPSERT en UserTraits.
FUERA: creación de nuevos TraitAtoms (eso es del Reflector), consumo del listener.

## Implementation Path

`kb_agent/perfilador/extractor.py`

Ambigüedad resuelta — contrato de mapeo:
- Entrada: turn_text YA scrubbeado (sin PII).
- SOLO extrae características EXPLÍCITAS ("soy vegetariano"), no infiere PII ni datos sensibles.
- Fuente de candidatos: la lista de TraitAtoms candidatos (id + body) se obtiene vía `fetch(type='trait')` del conector SLDB (ver task-implementar-conector-sldb-del-ontologizador); el extractor NO lee SLDB a mano ni mantiene su propio catálogo.
- Mecanismo de mapeo (v1): LLM con salida estructurada que recibe esa lista de TraitAtoms candidatos (id + body) y devuelve `[{trait_id, confidence}]` eligiendo SOLO ids de esa lista. Si no hay match, devuelve lista vacía (no inventa traits).
- Regla de `confidence`: la asigna el LLM en rango 0-1; se descarta todo lo que venga con confidence < 0.7 (umbral `TRAIT_MIN_CONFIDENCE`). Aserción explícita usada en negocio: solo se persiste ≥ 0.7.
- Escribe en UserTraits (user_id, trait_id, confidence, source='perfilador'); UPSERT idempotente (si ya existe, actualiza confidence al máximo entre el viejo y el nuevo).

## Validation

- `pytest` con SQLite `:memory:` + `.sldb_test/` con trait-vegetariano: inyectar "soy vegetariano" y afirmar edge user_id -> trait-vegetariano.
- Afirmar que una señal sin TraitAtom correspondiente NO crea fila.
- Afirmar idempotencia (mismo input 2 veces = 1 fila).

## Done When

Mapea señales explícitas a traits existentes, es idempotente y no inventa traits.
