---
id: atom-concepto-turno-extendido
title: Turno Extendido
five_wh_one_plus: what
tags:
- layer:business
- family:concepts
provenance: architecture-audit
---

# Turno Extendido

## Answer

El ciclo de vida completo de un mensaje de usuario. A diferencia de un request/response tradicional, el turno extendido incluye pausas en la ejecución síncrona para ejecutar herramientas externas (tools) y procesos asíncronos posteriores a la respuesta (como la extracción de perfiles y la reflexión en batch). Cada turno se persiste con un `id` autoincremental como PK real (auditable e inequívoco); el `turn_id` que emite el runtime (p.ej. "t1", "t2") es un contador por-sesión y NO es globalmente único, por lo que solo es único dentro de su `session_id` (UniqueConstraint `session_id`+`turn_id`) y sirve para localizar un turno puntual en el Turn Inspector. El turno pertenece además a una Conversation (`conversation_id`), la unidad que acota qué historial entra al prompt.
