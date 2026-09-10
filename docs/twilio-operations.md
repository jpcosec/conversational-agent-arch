# Twilio — canal WhatsApp/SMS del runtime

## Cómo funciona

El endpoint `POST /webhooks/twilio` en `frontends/chat/app.py` recibe los
webhooks de Twilio. Flujo:

1. **Validación de firma** — `X-Twilio-Signature` se valida con
   `TWILIO_AUTH_TOKEN` via `RequestValidator`. Sin token válido → 403.
2. **InboundService** (`kb_agent/inbound.py`) normaliza el remitente
   (`whatsapp:+569...` o `sms:+569...`), persiste el mensaje en la tabla
   `inbound_messages` (idempotencia por `UNIQUE(provider, provider_message_id)`
   frente a reintentos de Twilio), resuelve el usuario y corre el turno.
3. **Modo de respuesta**:
   - **sync** — TwiML con el texto de respuesta en línea. Solo sirve si el
     turno cabe en los 15 s de timeout de Twilio (medido: 20-35 s con LLM).
   - **async** (default cuando existe `TWILIO_ACCOUNT_SID`) — responde
     `<Response/>` al instante, el turno corre en un background task de
     FastAPI, y al terminar envía la respuesta por la REST API de Twilio
     (`client.messages.create`). El `MessageSid` saliente queda en
     `reply_provider_message_id`.
4. **Identidad** — Antonia usa `identity_key: phone`. Un mismo teléfono por
   WhatsApp y SMS unifica al mismo usuario. El webhook normaliza el `From` a
   `whatsapp:+569...` o `sms:+569...` como `external_id`.

## Configuración

Tres variables en `.env`:

| Variable | Obligatoria | Para qué |
|---|---|---|
| `TWILIO_ACCOUNT_SID` | async | Enviar respuesta por REST |
| `TWILIO_AUTH_TOKEN` | sí | Validar firma del webhook |
| `TWILIO_SMS_FROM` | opcional | Número SMS que recibe mensajes |
| `TWILIO_WHATSAPP_FROM` | opcional | Sender WhatsApp (ej. `whatsapp:+14155238886` sandbox) |

Override por env: `TWILIO_REPLY_MODE=sync|async` fuerza el modo.

## Cómo agregar un canal o cambiar de cuenta

1. En la consola de Twilio, ir al canal correspondiente:
   - **SMS** → Phone Numbers → Active numbers → el número → "A message comes in"
   - **WhatsApp (sandbox)** → Messaging → Try it out → Sandbox settings
   - **WhatsApp (sender propio)** → Messaging → Senders → WhatsApp senders
2. Poner la URL pública del webhook con método **POST**.
3. Asegurar que el `TWILIO_AUTH_TOKEN` en `.env` sea de la MISMA cuenta.

Para cambiar de cuenta Twilio, reemplazar las 3 variables en `.env` y el
webhook en la consola.

## Modal vs Local vs AWS

| Capa | Local | Modal | AWS |
|---|---|---|---|
| **URL pública** | ngrok (`deploy/launch_twilio_local.sh`) | `https://<workspace>--<app>.modal.run/webhooks/twilio` | API Gateway + Lambda o ALB + ECS/Fargate |
| **Secretos** | `.env` | Modal Secrets (`kb-agent-runtime-twilio` con `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN`) | Secrets Manager o Parameter Store |
| **Webhook timeout** | 15 s (Twilio), el turno va async | Idem. Modal no tiene límite duro de timeout de función, pero el webhook de Twilio sí corta a 15 s → async obligatorio | Idem: API Gateway timeout 29 s max, Lambda 900 s. Async siempre. |
| **Respuesta async** | REST desde localhost a Twilio | REST desde Modal a Twilio | REST desde Lambda/ECS a Twilio |
| **Idempotencia** | Tabla `inbound_messages` UNIQUE en SQLite local | Misma tabla en Volume persistente (`/data/ui-chat.sqlite`) | Misma tabla en RDS/Aurora o DynamoDB |

### AWS específico

Para poner esto en AWS:
- **Opción serverless**: API Gateway HTTP → Lambda con `TWILIO_REPLY_MODE=async`.
  La Lambda recibe el POST de Twilio, persiste el mensaje, responde 200 con
  `<Response/>`, y corre el turno (o encola en SQS/SNS para procesar fuera del
  webhook). La respuesta REST necesita que Lambda tenga conectividad de salida
  (NAT/VPC endpoint) y las creds Twilio en env.
- **Opción container**: ALB → ECS/Fargate sirviendo la misma FastAPI. El ALB
  termina TLS y pasa el request original, pero la URL de firma
  `X-Twilio-Signature` se calcula sobre `https://...`. Detrás del ALB hay que
  reconstruir la URL externa desde `X-Forwarded-Proto`/`Host` antes de validar.
- **Base de datos**: en AWS no hay SQLite compartido → migrar a RDS (PostgreSQL).
  La tabla `inbound_messages` requiere `UNIQUE(provider, provider_message_id)`
  para idempotencia.
- **Secretos**: via AWS Secrets Manager, no `.env`. El runtime los lee en startup.