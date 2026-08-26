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

Múltiples interfaces de conexión que convergen en el Orquestador. Incluyen el endpoint principal FastAPI (`POST /api/chat`), el webhook de WhatsApp/SMS de Twilio, y el intérprete local interactivo CLI. Todo canal expone un `external_id`.
