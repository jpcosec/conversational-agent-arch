---
id: task-implementar-batch-reader-del-reflector
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-batch-reader-del-reflector
current_node: checklist-task-implementar-batch-reader-del-reflector-execution-ready
history: []
references: []
depends_on:
- task-implementar-modelos-de-sesión-e-historial
- task-implementar-scrubber-de-pii
pills: []
files: []
checklists:
- checklist-task-implementar-batch-reader-del-reflector-execution-ready
- checklist-task-implementar-batch-reader-del-reflector-testing-ready
- checklist-task-implementar-batch-reader-del-reflector-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-reflector-batch
- atom-historial-de-conversacion-sin-pii
- atom-aislamiento-estricto-de-pii
---

# Implementar Batch Reader del Reflector

## Rationale

Alimenta al Reflector con historial limpio en lotes, sin exponer PII ni bloquear el runtime.

## Goal

_Describe the concrete result this task must produce._

Leer lotes históricos limpios desde SQL.

## Scope

EN: Job que lee ChatHistory en lotes filtrando pii_scrubbed=True.
FUERA: detección de patrones y escritura de átomos (tarea generador).

## Implementation Path

`kb_agent/reflector/reader.py`

Ambigüedad resuelta:
- Query OBLIGATORIA: `WHERE pii_scrubbed = True` (nunca lee filas sin scrubbear).
- Paginación por lotes (`BATCH_SIZE`, default 500) para no cargar todo en memoria.
- Marca un checkpoint (último created_at procesado) para no reprocesar.
- Disparo por CRON (no en el hilo de respuesta).

## Validation

- `pytest` SQLite `:memory:`: sembrar filas mixtas (scrubbed y no) y afirmar que el reader devuelve SOLO las scrubbed.
- Afirmar que el checkpoint evita reprocesar en una 2ª corrida.

## Done When

El reader entrega solo historial limpio, paginado, y respeta el checkpoint.
