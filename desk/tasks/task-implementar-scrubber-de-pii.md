---
id: task-implementar-scrubber-de-pii
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-scrubber-de-pii
current_node: checklist-task-implementar-scrubber-de-pii-execution-ready
history: []
references: []
depends_on:
- task-implementar-modelos-de-sesión-e-historial
pills: []
files: []
checklists:
- checklist-task-implementar-scrubber-de-pii-execution-ready
- checklist-task-implementar-scrubber-de-pii-testing-ready
- checklist-task-implementar-scrubber-de-pii-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-aislamiento-estricto-de-pii
- atom-historial-de-conversacion-sin-pii
---

# Implementar Scrubber de PII

## Rationale

Garantiza que ningún PII salga de la capa de identidad hacia motores cognitivos. Es el gate de privacidad del sistema.

## Goal

_Describe the concrete result this task must produce._

Filtro que limpia ChatHistory antes de exponerlo a otros motores.

## Scope

EN: Función `scrub(text) -> text` (síncrona, pura, reutilizable inline por otros motores) y worker que marca ChatHistory.pii_scrubbed=True.
FUERA: definición de tablas (ya existen), consumo por Reflector.

## Implementation Path

`kb_agent/pii/scrubber.py`

Contrato / ambigüedad resuelta:
- Categorías PII a enmascarar (mínimo): teléfono, email, nombre propio, dirección, RUT/ID nacional, número de tarjeta.
- Estrategia: tokenización reemplazando por placeholders estables (`<PHONE_1>`, `<EMAIL_1>`) NO borrado, para preservar co-referencia dentro del turno.
- Dos consumidores de la MISMA función `scrub(text)`:
  1. Inline/síncrono: otros motores (ej. el listener del Perfilador) importan y llaman `scrub(text)` directamente antes de publicar, sin pasar por la tabla. `scrub(text)` no debe tener efectos secundarios ni tocar la BD.
  2. Worker/barrido: recorre filas de ChatHistory con pii_scrubbed=False, reescribe content aplicando `scrub` y setea pii_scrubbed=True.
- El worker recorre filas con pii_scrubbed=False, reescribe content y setea pii_scrubbed=True.

## Validation

- `pytest`: dar un string con teléfono+email+nombre y afirmar que el output no contiene ninguno de los 3 valores originales.
- Afirmar idempotencia: correr scrub 2 veces produce el mismo resultado.
- Afirmar que tras el worker, la fila queda pii_scrubbed=True.

## Done When

El scrubber enmascara las 6 categorías, es idempotente, y marca las filas procesadas.
