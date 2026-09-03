---
id: atom-persistencia-sql
title: 'SQL: Identidad y Estado'
five_wh_one_plus: what
tags:
- layer:knowledge
- role:data
provenance: architecture-audit
---

# SQL: Identidad y Estado

## Answer

Capa de persistencia relacional transaccional (vía SQLAlchemy). Almacena los `Users`, la máquina de estados persistente (`SessionState`), el `ChatHistory` (ya scrubbeado de PII), los mapeos relacionales de `UserTraits`, y las tablas de negocio como Reservas. La identidad se unifica por teléfono cuando el proyecto usa `identity_key='phone'` (Antonia lo usa): `Users.phone` (E.164 normalizado, indexado) es la clave canónica de persona y el mismo teléfono en otro canal reusa el mismo `Users`; el `external_id` sigue único por canal y queda como alias. La entidad `Conversation` (estados `open`/`closed`) agrupa los turnos de un usuario en un tramo temporal acotado: un `Users` tiene una lista de conversaciones, cada `Conversation` una lista de turnos, y el historial que va al prompt no cruza el límite de una conversación cerrada (antes se infería "conversación" por día calendario y se mezclaba todo el `chat_history` del usuario). La tabla `Turns` guarda el trail auditable de cada turno (decision, bundle, draft, gate, tool) con PK `id` autoincremental, `turn_id` único solo dentro de `session_id`, `conversation_id` y `kind` (`TurnKind`: `user`/`agent`/`override`). La tabla `InboundMessage` (`inbound_messages`) es el source de cada turno que entra por un proveedor externo: proveedor, id del mensaje en el proveedor (UNIQUE por proveedor, idempotencia), canal, teléfono, payload crudo, `user_id`, `conversation_id`, `turn_id`, respuesta, id del mensaje saliente y estado `received`/`replied`/`failed`.
