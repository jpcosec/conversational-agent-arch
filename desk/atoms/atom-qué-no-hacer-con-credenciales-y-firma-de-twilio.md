---
id: atom-qué-no-hacer-con-credenciales-y-firma-de-twilio
title: Qué no hacer con credenciales y firma de Twilio
five_wh_one_plus: how_not
tags:
- layer:ops
- role:boundary
- topic:twilio
provenance: frontends/chat/app.py
---

# Qué no hacer con credenciales y firma de Twilio

## Answer

No mezclar credenciales de cuentas Twilio distintas. `X-Twilio-Signature` se calcula con el Auth Token de la cuenta que dispara el webhook, así que `TWILIO_AUTH_TOKEN` en `.env` o en el secret de Modal tiene que ser el de la cuenta dueña del número o sender; con el token de otra cuenta todo entra como 403 "invalid twilio signature". Pasó el 2026-09-02: una API Key `SK...` generada desde el flujo de WhatsApp pertenecía a una cuenta Trial creada ese día, no a la cuenta del número; verificar siempre a qué cuenta pertenece una credencial con `GET /2010-04-01/Accounts.json` autenticando con ella antes de usarla. No usar una API Key para validar firmas: la firma sólo se verifica con el Auth Token; la key sirve para REST. No exponer el runtime detrás de un proxy que no propague `X-Forwarded-Proto`: la firma se calcula sobre la URL pública exacta (`https://...`) y si uvicorn reconstruye `http://` el 403 es inmediato (en AWS detrás de ALB o API Gateway, `--proxy-headers --forwarded-allow-ips='*'`). No responder el webhook en modo `sync` en producción: un turno tarda más que los 15 s que Twilio espera. No dejar el `TWILIO_ACCOUNT_SID` fuera del secret si se quiere modo async: sin él el runtime cae a `sync`. No commitear `.env`: está en `.gitignore` y contiene los tokens de ambas cuentas.
