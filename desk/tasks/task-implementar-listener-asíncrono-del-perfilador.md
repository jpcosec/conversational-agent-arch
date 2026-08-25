---
id: task-implementar-listener-asíncrono-del-perfilador
status: draft
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-implementar-listener-asíncrono-del-perfilador
current_node: checklist-task-implementar-listener-asíncrono-del-perfilador-execution-ready
history: []
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-implementar-listener-asíncrono-del-perfilador-execution-ready
- checklist-task-implementar-listener-asíncrono-del-perfilador-testing-ready
- checklist-task-implementar-listener-asíncrono-del-perfilador-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-perfilador-asincrono
---

# Implementar Listener Asíncrono del Perfilador

## Rationale

Desacopla el perfilado del turno conversacional para no sumar latencia a la respuesta del usuario.

## Goal

_Describe the concrete result this task must produce._

Conectar un worker que consuma eventos de turnos en background.

## Scope

EN: Worker asincrónico que consume eventos de "turno cerrado" y despacha al extractor.
FUERA: la lógica de extracción de traits (tarea aparte).

## Implementation Path

`kb_agent/perfilador/listener.py`

Ambigüedad resuelta:
- Mecanismo de disparo: cola en proceso (`asyncio.Queue`) para v1; interfaz abstracta `EventBus` para permitir swap a Redis después sin tocar el extractor.
- Evento publicado por el router al cerrar un turno (drafting_response -> idle): `{user_id, turn_text}`.
- El worker NUNCA bloquea el hilo de respuesta; si falla, reintenta con backoff y loguea.

## Validation

- `pytest` async: publicar un evento en la cola y afirmar que el handler del extractor fue invocado con el user_id/turn_text correctos.
- Afirmar que una excepción en el handler no propaga al productor.

## Done When

El worker consume eventos de forma no bloqueante y aisla fallos del hilo principal.
