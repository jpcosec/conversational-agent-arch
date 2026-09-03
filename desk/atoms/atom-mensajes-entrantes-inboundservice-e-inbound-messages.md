---
id: atom-mensajes-entrantes-inboundservice-e-inbound-messages
title: 'Mensajes entrantes: InboundService e inbound_messages'
five_wh_one_plus: what
tags:
- layer:runtime
- role:boundary
- topic:canales
- topic:twilio
provenance: kb_agent/inbound.py
---

# Mensajes entrantes: InboundService e inbound_messages

## Answer

Capa entre el webhook HTTP y `Orchestrator.handle_turn` para todo mensaje que entra por un proveedor externo (`kb_agent/inbound.py`, clase `InboundService`). Por cada mensaje: normaliza el remitente a un `external_id` con prefijo de canal (`normalize_sender`), persiste una fila `InboundMessage` en la tabla `inbound_messages` (`kb_agent/models_sql/inbound.py`, migración `d4e5f6a7b8c9`), resuelve el usuario con `ensure_user` y corre el turno; al terminar deja en la misma fila el `user_id`, `conversation_id`, `turn_id`, el texto de la respuesta y el estado (`received`/`replied`/`failed`, con `error` si falló). La fila es el *source* del turno: proveedor (`twilio`), `provider_message_id` (el `MessageSid`), canal, teléfono canónico, destino (`to`), cuerpo, `profile_name`, `num_media` y el `payload` crudo del webhook, para auditar de dónde salió cada turno y conservar campos que hoy no se usan (media, `WaId`). `UNIQUE(provider, provider_message_id)` da idempotencia: un reintento del proveedor con el mismo id no corre un segundo turno, devuelve la respuesta ya guardada (o vacío si el turno original sigue corriendo). El webhook `POST /webhooks/twilio` en `frontends/chat/app.py` queda como capa fina: valida la firma y delega. Dos modos de respuesta: `sync` (el webhook espera el turno y responde TwiML con el texto) y `async` (persiste, responde `<Response/>` al instante, corre el turno en un background task de FastAPI y manda la respuesta por REST con un `Sender` inyectable — `twilio_rest_sender` en producción, un callable falso en tests — y guarda el sid saliente en `reply_provider_message_id`). El modo se elige con `TWILIO_REPLY_MODE=sync|async`; sin override, `async` si existe `TWILIO_ACCOUNT_SID` y `sync` si no. Los turnos de la UI (`POST /api/chat`) no pasan por aquí: su source es la sesión del navegador (`ui:<session>`).
