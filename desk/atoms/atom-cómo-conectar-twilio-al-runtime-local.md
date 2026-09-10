---
id: atom-cómo-conectar-twilio-al-runtime-local
title: Cómo conectar Twilio al runtime local
five_wh_one_plus: how
tags:
- layer:ops
- role:boundary
- topic:twilio
- topic:canales
provenance: deploy/launch_twilio_local.sh
---

# Cómo conectar Twilio al runtime local

## Answer

`deploy/launch_twilio_local.sh` empaqueta la prueba local del canal con tres subcomandos. `up`: carga `.env` (exige `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` y al menos uno de `TWILIO_SMS_FROM` / `TWILIO_WHATSAPP_FROM`), lleva el sqlite a `head` con alembic (si la base no tiene `alembic_version` la respalda como `.bak-<timestamp>` y la recrea, porque una base híbrida de `create_all()` no se migra de forma confiable), levanta uvicorn con `frontends.chat.server:app` si el puerto está libre, hace un POST firmado de smoke contra `/webhooks/twilio` (sin `To`, para que en modo async no intente enviar nada por REST), abre `ngrok http 8000` y apunta los webhooks al túnel: el de SMS vive en el número (`IncomingPhoneNumber.sms_url`, se actualiza por API) y el de WhatsApp vive en el *sender* (Messaging v2 Channels Senders, se actualiza por API si la cuenta lo permite). `down` restaura los webhooks originales guardados en `runs/logs/twilio_local/prev_webhooks.json` y mata uvicorn/ngrok; `status` muestra procesos, túnel, cuenta, sender y últimos mensajes. Cuentas: la cuenta Full "Laboratorios Chile" es dueña del número chileno +56229149113 con SMS y voz, sin sender de WhatsApp registrado; registrar el número como WhatsApp Sender requiere Meta Business y verificación en Console > Messaging > Senders. La cuenta Trial "My First Twilio Account" trae un sender WhatsApp de prueba (+17372212163, la persona se une mandando `join twilio-trial`), pero en Trial la API de senders, Content y balance responde 401 y el webhook sólo se configura a mano en la consola (Messaging > Try it out > Send a WhatsApp message > Sandbox settings > "When a message comes in"); el script detecta ese caso e imprime la URL a pegar. `.env` mantiene los dos perfiles y sólo uno activo. Verificado de punta a punta el 2026-09-02: POST firmado vía ngrok con URL `https` → 200, y la firma valida porque uvicorn honra `X-Forwarded-Proto` desde 127.0.0.1, que es donde corre el agente de ngrok. En Modal no hay túnel: el webhook es `https://<app>.modal.run/webhooks/twilio` fijo y las credenciales van en el secret `kb-agent-runtime-twilio`.
