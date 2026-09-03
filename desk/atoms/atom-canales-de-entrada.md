---
id: atom-canales-de-entrada
title: Canales de Entrada
five_wh_one_plus: what
tags:
- layer:frontend
- role:boundary
provenance: architecture-audit
---

# Canales de Entrada

## Answer

Múltiples interfaces de conexión que convergen en el Orquestador. Incluyen el endpoint principal FastAPI (`POST /api/chat`), el webhook de WhatsApp/SMS de Twilio (`POST /webhooks/twilio`) y el intérprete local interactivo CLI. Todo canal expone un `external_id` con prefijo de canal (`ui:<session>`, `whatsapp:+569...`, `sms:+569...`), del que el orquestador deriva `channel`. El webhook de Twilio no llama al orquestador directo: valida la firma `X-Twilio-Signature` con el Auth Token de la cuenta y delega en `InboundService` (`kb_agent/inbound.py`), que normaliza el remitente, persiste el mensaje como `InboundMessage` con su `MessageSid` (source del turno e idempotencia frente a reintentos) y corre el turno en modo `sync` (TwiML con el texto) o `async` (`<Response/>` inmediato, turno en background y respuesta por la API REST de Twilio, porque Twilio corta el webhook a los 15 s). Sin `TWILIO_AUTH_TOKEN` la ruta responde 503.
