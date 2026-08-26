---
id: task-conectar-el-runtime-a-twilio-whatsapp-sms
status: ready_for_testing
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-conectar-el-runtime-a-twilio-whatsapp-sms
current_node: checklist-task-conectar-el-runtime-a-twilio-whatsapp-sms-closeout-ready
history:
- operator-task-conectar-el-runtime-a-twilio-whatsapp-sms-activate
- operator-task-conectar-el-runtime-a-twilio-whatsapp-sms-ready-for-testing
references: []
depends_on: []
pills: []
files: []
checklists:
- checklist-task-conectar-el-runtime-a-twilio-whatsapp-sms-execution-ready
- checklist-task-conectar-el-runtime-a-twilio-whatsapp-sms-testing-ready
- checklist-task-conectar-el-runtime-a-twilio-whatsapp-sms-closeout-ready
task_type: implementation
inherits_from: []
inherit_acceptance_context: false
atoms: []
closeout_evidence_verified: false
---

# Conectar el runtime a Twilio (WhatsApp/SMS)

## Rationale

_Explain why this task exists or the business driver behind it._

El agente solo es accesible por la UI web. Twilio permite que usuarios reales escriban por WhatsApp/SMS al mismo runtime (Gemini + SLDB + SQL) sin duplicar logica de negocio.

## Goal

_Describe the concrete result this task must produce._

Exponer un webhook POST /webhooks/twilio que traduce mensajes de Twilio a Orchestrator.handle_turn(external_id, message) y devuelve la respuesta como TwiML, con validacion de firma y manejo del timeout de Twilio.

## Scope

_State what is in scope and what is out of scope._

IN: kb_chat_ui/server.py (o nuevo kb_agent/channels/twilio_webhook.py montado en app), .env (secretos Twilio), tests. OUT: NO tocar la KB, NO meter logica de negocio en el canal, NO modificar handle_turn (ya cierra el ciclo de tools sincronamente).

## Implementation Path

_Outline the expected implementation route or affected surface._

### Hecho clave (simplifica todo)
`Orchestrator.handle_turn(external_id, message, scenario=None)` en
`kb_agent/orchestrator.py:184` YA cierra el ciclo de tools de forma sincrona:
decide el turno (`decide_turn`), y si es `tool_call` ejecuta la tool
(`execute_tool` con registry `TOOL_HANDLERS`, :140-149) y el Conversador redacta
la confirmacion, todo dentro de la misma llamada. Devuelve un dict con:
  - `kind`: `"nl" | "tool_call" | "fallback"`
  - `reply` / `reply_text` (usar `reply_text` para Twilio: ya viene serializado)
  - metadata: `flow_node`, `traits_after`, `state_trace`, etc.
NO hace falta un ciclo async de tools ni `resume_with_tool_result`: una sola
llamada a `handle_turn` basta.

### Mapeo Twilio -> runtime
  - `From` (ej. `whatsapp:+56912345678`) -> `external_id` (clave de `Users` en SQL;
    ya persiste sesion, traits y flow_node por numero, reboot-safe)
  - `Body` -> `message`
  - `To` (tu numero Twilio) -> selector de negocio/config (multi-tenant, futuro)

### Paso 1 - Endpoint webhook (MVP sincrono)
Agregar en `kb_chat_ui/server.py` (o modulo nuevo
`kb_agent/channels/twilio_webhook.py` montado en `app`). Reusar el
`orchestrator` global ya instanciado en server.py:

```python
from fastapi import Request, Response, HTTPException
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

@app.post("/webhooks/twilio")
async def twilio_inbound(request: Request):
    form = dict(await request.form())
    validator = RequestValidator(os.environ["TWILIO_AUTH_TOKEN"])
    sig = request.headers.get("X-Twilio-Signature", "")
    if not validator.validate(str(request.url), form, sig):
        raise HTTPException(403, "invalid twilio signature")
    result = orchestrator.handle_turn(
        external_id=form.get("From", ""), message=form.get("Body", "").strip()
    )
    twiml = MessagingResponse()
    twiml.message(result.get("reply_text") or result.get("reply") or "")
    return Response(str(twiml), media_type="application/xml")
```
Dependencia: `pip install twilio`.

### Paso 2 - Secretos (NO en project.config.yaml; van en .env, ya se carga)
```
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM=whatsapp:+14155238886
```
El negocio activo lo sigue definiendo `project.config.yaml`; Twilio son
credenciales de canal.

### Paso 3 - Timeout de Twilio (~15s)
Un turno Gemini tarda ~3-5s (`latency_ms` observado ~3595ms). Si con tool
intermedia se acerca al limite: responder TwiML vacio (ACK 200) + correr
`handle_turn` en `BackgroundTasks` y enviar la respuesta por Messaging API:
```python
from twilio.rest import Client
client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
client.messages.create(from_=os.environ["TWILIO_FROM"], to=from_id, body=reply_text)
```
Para el MVP el modo sincrono alcanza.

### Guardarrailes / riesgos
  - PII: llegan numeros reales. El perfilador ya scrubbea antes de procesar;
    NO loguear `Body`/`From` en claro.
  - Firma Twilio: no saltear la validacion en prod.
  - Idempotencia: Twilio reintenta webhooks; `crear_reserva` no es idempotente
    hoy -> deduplicar por `MessageSid`.
  - Doctrina: el webhook es solo canal de entrada; NO logica de negocio, NO tocar KB.

### Archivos clave (contexto cero)
  - `kb_agent/orchestrator.py`: `handle_turn` (:184), `execute_tool` (:145),
    `TOOL_HANDLERS` (:140), `ensure_user` (:176)
  - `kb_chat_ui/server.py`: server FastAPI, `orchestrator` global, patron de endpoints
  - `kb_agent/project_config.py`: `load_project_config()`, `CFG`
  - `.env`: secretos (Vertex ADC ya OK; anadir Twilio)

### Multi-negocio (futuro, fuera de MVP)
Un numero Twilio = un negocio = un `project.config.yaml`. Para varios: enrutar por
`form["To"]` a un dict `{to_number: Orchestrator}` (hoy hay un solo orchestrator global).

### Verificacion local
`ngrok http 8100` -> configurar webhook Twilio a `https://<ngrok>/webhooks/twilio`
-> mandar "que pizzas tienen?" (kind nl) y "reservar mesa para 4 manana 21:00"
(kind tool_call, reserva en SQL) -> confirmar contexto entre mensajes.

## Validation

_List the checks required before this task can close._

- pytest tests/ -q

## Done When

_Name the observable condition that makes the task complete._

Un turno real por WhatsApp responde la carta (kind nl) y una reserva ejecuta crear_reserva y confirma (kind tool_call) persistida en SQL; el segundo mensaje del mismo numero mantiene contexto (traits/flow_node). Evidencia: runs/subagents/<run-dir>/validation.log con la corrida (ngrok o test con firma Twilio simulada).
