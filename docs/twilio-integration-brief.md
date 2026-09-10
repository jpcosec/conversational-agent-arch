# Research: Twilio API Integration Brief for a Python Conversational-Agent Backend

## Summary
For a Python conversational agent over messaging, use **Twilio Programmable Messaging** for plain SMS, the **WhatsApp Business API via Twilio** for WhatsApp (built on top of Messaging), and the **Conversations API** only when you need multi-party, cross-channel, stateful chat threads with participant/state management. Authentication is done with Account SID + Auth Token (or, preferably, API Key SID/Secret), inbound messages arrive via HTTP POST webhooks (validate `X-Twilio-Signature`), and outbound messages are sent with the `twilio` Python SDK's `twilio.rest.Client`.

> Note: This brief was produced from established Twilio API knowledge; no live `web_search` tool was available in this run. All URLs point to canonical Twilio documentation locations. Verify pricing and template/policy details against the live docs before shipping, since those are the most time-sensitive.

## Findings

### 1. Which Twilio product to use

1. **Programmable Messaging (SMS/MMS)** — Stateless, one message at a time. You send/receive individual messages via the `Messages` resource. Best for simple notification + reply bots on SMS. Fine for a conversational agent where *you* keep conversation state in your own DB. [Docs: Programmable Messaging](https://www.twilio.com/docs/messaging)

2. **WhatsApp via Twilio** — Uses the *same* Messaging API and `Messages` resource, just with a `whatsapp:` prefix on `To`/`From`. It layers on WhatsApp Business Platform rules (templates, 24-hour session window, opt-in). Use for WhatsApp reach; code path is nearly identical to SMS. [Docs: WhatsApp](https://www.twilio.com/docs/whatsapp)

3. **Conversations API** — A higher-level, *stateful* layer that models a persistent "Conversation" with multiple Participants across channels (SMS, WhatsApp, Chat/SDK). Twilio stores the message history and manages participant identity/channel mapping. Use it when you need: cross-channel threads (same conversation over SMS + WhatsApp + web chat), multiple human + bot participants, group messaging, or you want Twilio to hold the message store. It is heavier and adds concepts (Conversation SID, Participant SID) you don't need for a simple single-user bot. [Docs: Conversations](https://www.twilio.com/docs/conversations)

**Decision rule:** Simple 1:1 bot where your backend owns state → **Programmable Messaging** (with `whatsapp:` prefix for WhatsApp). Need Twilio-managed multi-party/cross-channel history → **Conversations API**.

### 2. Authentication & credentials

4. **Account SID + Auth Token** — The root credentials found on the Twilio Console dashboard. `Account SID` starts with `AC...`; the Auth Token is the account-wide secret. Works everywhere but is high-blast-radius if leaked (can't scope or rotate without breaking everything). [Docs: Auth](https://www.twilio.com/docs/iam/access-tokens#auth-tokens)

5. **API Key SID + Secret (preferred)** — Create a "Standard" API Key in the Console (`SK...` SID + a secret shown once). Pass the API Key SID as username and secret as password, plus the Account SID, when constructing the client. API Keys can be revoked/rotated independently and are the recommended production credential. [Docs: API Keys](https://www.twilio.com/docs/iam/api-keys)

6. **Environment variable convention** — Twilio's canonical names:
   - `TWILIO_ACCOUNT_SID`
   - `TWILIO_AUTH_TOKEN`
   - `TWILIO_API_KEY` (the `SK...` SID) and `TWILIO_API_SECRET` when using API keys
   The bare `Client()` constructor auto-reads `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` from the environment. Never commit these; load from a secrets manager or `.env` (git-ignored). [Docs: Python quickstart](https://www.twilio.com/docs/messaging/quickstart/python)

### 3. Inbound messages (webhooks)

7. **How webhooks work** — You configure a webhook URL on a phone number / Messaging Service / WhatsApp sender. When a message arrives, Twilio sends an HTTP `POST` (default; can be GET) with `Content-Type: application/x-www-form-urlencoded` to your URL. Twilio expects an optional **TwiML** XML response to reply synchronously. [Docs: Incoming webhooks](https://www.twilio.com/docs/messaging/guides/webhook-request)

8. **Key POST payload fields** (form-encoded):
   - `MessageSid` — unique ID of the inbound message (`SM...` / `MM...` / for WhatsApp same format)
   - `From` — sender (e.g. `+15551234567`, or `whatsapp:+15551234567`)
   - `To` — your Twilio number (or `whatsapp:+14155238886`)
   - `Body` — the text content
   - `NumMedia` — count of media attachments; `MediaUrl0`, `MediaContentType0`, … for MMS/WhatsApp media
   - `AccountSid`, `MessagingServiceSid` (if via a service)
   - WhatsApp extras: `ProfileName`, `WaId`, `ButtonText` (for template button replies)
   [Docs: Twilio inbound params](https://www.twilio.com/docs/messaging/guides/webhook-request#parameters-in-twilios-request-to-your-application)

9. **TwiML response** — A synchronous reply is XML like:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <Response>
     <Message>Thanks, we got your message!</Message>
   </Response>
   ```
   Return an empty `<Response/>` to acknowledge without replying (then send later via REST). [Docs: TwiML Message](https://www.twilio.com/docs/messaging/twiml)

### 4. Outbound messages

10. **REST send** — Use `client.messages.create(...)` with `from_` + `to` (or `messaging_service_sid`) and `body`. Same call for SMS and WhatsApp; WhatsApp just prefixes numbers with `whatsapp:`. Returns a Message instance with `.sid` and `.status`. [Docs: Send a message](https://www.twilio.com/docs/messaging/api/message-resource)

### 5. WhatsApp specifics

11. **Sandbox vs production** — The **Sandbox** (`whatsapp:+14155238886`) lets you test immediately: users must join by texting a code (e.g. `join <word>`) to opt in. Production requires a Twilio WhatsApp Sender tied to an approved **WhatsApp Business Account (WABA)** and a Meta-verified business + display name. [Docs: WhatsApp sandbox](https://www.twilio.com/docs/whatsapp/sandbox)

12. **`whatsapp:` prefix** — Both `From` and `To` must be prefixed: `whatsapp:+1415...`. [Docs](https://www.twilio.com/docs/whatsapp/api)

13. **24-hour session window** — After a user messages you, you have a 24-hour window to send free-form messages. Outside that window you may only send **pre-approved message templates** (formerly HSM). [Docs: 24h window](https://www.twilio.com/docs/whatsapp/key-concepts#the-24-hour-session-window)

14. **Message templates** — Must be submitted (via Twilio Content Template Builder / Content API) and approved by Meta before use for business-initiated or out-of-window messages. Send with `content_sid` (+ `content_variables` JSON) referencing an approved template. [Docs: Content Templates](https://www.twilio.com/docs/content)

### 6. Webhook signature validation

15. **`X-Twilio-Signature`** — Every Twilio webhook includes this header, an HMAC-SHA1 signature computed over the full URL + sorted POST params using your Auth Token. Validate it with `twilio.request_validator.RequestValidator` to reject forged requests. Use the exact public URL Twilio called (scheme/host/path/query must match, including any proxy rewrites). [Docs: Security / validation](https://www.twilio.com/docs/usage/webhooks/webhooks-security)

### 7. Sender identity & Messaging Services

16. **Phone numbers** — Buy an SMS-capable number in the Console/API. In the US, use a **10DLC** registered campaign or a Toll-Free verified number to avoid heavy filtering. [Docs: A2P 10DLC](https://www.twilio.com/docs/messaging/compliance/a2p-10dlc)

17. **Messaging Services** — A container that pools multiple numbers/senders, provides sticky sender selection, sender pools, geo-matching, and a single `messaging_service_sid` (`MG...`) you pass instead of `from_`. Recommended for scale and for centralizing inbound webhook config. [Docs: Messaging Services](https://www.twilio.com/docs/messaging/services)

### 8. Pricing & rate limits (high level)

18. **Pricing model** — Pay-per-message. SMS billed per segment (160 GSM-7 chars, or 70 for Unicode) per destination; MMS priced separately; WhatsApp billed per Meta conversation category (marketing/utility/authentication/service) plus Twilio's per-message fee. Phone numbers carry a small monthly fee; 10DLC has registration + carrier fees. **Confirm current rates on the live pricing page.** [Docs: Pricing](https://www.twilio.com/en-us/pricing)

19. **Rate limits / throughput** — SMS throughput is governed by MPS (messages per second) tied to number type and 10DLC campaign trust; Messaging Services queue and drip messages up to the allowed MPS. WhatsApp has its own tiered messaging limits set by Meta. Design for async sending and handle queueing/backpressure. [Docs: MPS](https://www.twilio.com/docs/messaging/features/how-does-messaging-work)

### 9. Python SDK quickstart

20. **Install:** `pip install twilio`. Minimal send + receive examples below. [Docs: Python helper library](https://www.twilio.com/docs/libraries/python)

### 10. Production gotchas

21. **Status callbacks** — Pass `status_callback="https://.../status"` on send (or configure on the Messaging Service) to receive delivery lifecycle POSTs: `queued → sent → delivered → undelivered/failed` (WhatsApp adds `read`). The callback includes `MessageStatus`, `MessageSid`, and on failure `ErrorCode`. [Docs: Status callbacks](https://www.twilio.com/docs/messaging/guides/track-outbound-message-status)

22. **Error codes** — Common: `30007` (carrier filtered / spam), `30008` (unknown error), `21610` (recipient unsubscribed via STOP), `63016` (WhatsApp: message outside 24h window without template), `21211` (invalid `To`). Log `ErrorCode` from status callbacks and the API response. [Docs: Error codes](https://www.twilio.com/docs/api/errors)

23. **Other production notes** — Always return `2xx` quickly from webhooks (do heavy work async), validate signatures, handle STOP/HELP/opt-out keywords (Twilio Advanced Opt-Out can auto-handle), respect the 24h WhatsApp window, use idempotency around `MessageSid`, and handle inbound media by fetching `MediaUrl*` with your auth.

---

## Concrete configuration

### Environment variables
```bash
# Root credentials (either these...)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here

# ...or API Key credentials (preferred for production)
TWILIO_API_KEY=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=your_api_key_secret_here

# Senders
TWILIO_SMS_FROM=+15551234567
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886      # sandbox number for testing
TWILIO_MESSAGING_SERVICE_SID=MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # optional

# Your public webhook base (e.g. ngrok in dev)
PUBLIC_BASE_URL=https://your-app.example.com
```

### Client construction
```python
import os
from twilio.rest import Client

# Option A: Auth Token (Client() with no args also auto-reads
# TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN from the environment)
client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])

# Option B (preferred): API Key SID + Secret, still scoped to the account SID
client = Client(
    os.environ["TWILIO_API_KEY"],
    os.environ["TWILIO_API_SECRET"],
    os.environ["TWILIO_ACCOUNT_SID"],
)
```

### Outbound: SMS and WhatsApp
```python
# SMS
msg = client.messages.create(
    from_=os.environ["TWILIO_SMS_FROM"],      # or messaging_service_sid=...
    to="+15559876543",
    body="Hello from the conversational agent!",
    status_callback=f'{os.environ["PUBLIC_BASE_URL"]}/webhooks/status',
)
print(msg.sid, msg.status)

# WhatsApp (free-form; only valid inside the 24h session window)
client.messages.create(
    from_=os.environ["TWILIO_WHATSAPP_FROM"],   # 'whatsapp:+1415...'
    to="whatsapp:+15559876543",
    body="Hi! How can I help?",
)

# WhatsApp using an approved template (out-of-window / business-initiated)
client.messages.create(
    from_=os.environ["TWILIO_WHATSAPP_FROM"],
    to="whatsapp:+15559876543",
    content_sid="HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",         # approved template
    content_variables='{"1":"Alex","2":"12:30 PM"}',
)
```

### Inbound + signature validation — Flask
```python
import os
from flask import Flask, request, abort, Response
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)
validator = RequestValidator(os.environ["TWILIO_AUTH_TOKEN"])

def verify_twilio(req) -> bool:
    signature = req.headers.get("X-Twilio-Signature", "")
    # Use the exact public URL Twilio called (respect proxy scheme/host)
    url = req.url
    return validator.validate(url, req.form.to_dict(), signature)

@app.post("/webhooks/inbound")
def inbound():
    if not verify_twilio(request):
        abort(403)

    from_number = request.form.get("From")      # '+1...' or 'whatsapp:+1...'
    body = request.form.get("Body", "")
    message_sid = request.form.get("MessageSid")

    reply_text = generate_agent_reply(from_number, body)  # your LLM/agent logic

    twiml = MessagingResponse()
    twiml.message(reply_text)
    return Response(str(twiml), mimetype="application/xml")

@app.post("/webhooks/status")
def status():
    if not verify_twilio(request):
        abort(403)
    print(request.form.get("MessageSid"),
          request.form.get("MessageStatus"),
          request.form.get("ErrorCode"))
    return ("", 204)
```

### Inbound — FastAPI equivalent
```python
import os
from fastapi import FastAPI, Request, Response, HTTPException
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

app = FastAPI()
validator = RequestValidator(os.environ["TWILIO_AUTH_TOKEN"])

@app.post("/webhooks/inbound")
async def inbound(request: Request):
    form = dict(await request.form())
    signature = request.headers.get("X-Twilio-Signature", "")
    # str(request.url) must equal the public URL Twilio called; behind a proxy,
    # rebuild it from forwarded headers if needed.
    if not validator.validate(str(request.url), form, signature):
        raise HTTPException(status_code=403)

    reply = generate_agent_reply(form.get("From"), form.get("Body", ""))
    twiml = MessagingResponse()
    twiml.message(reply)
    return Response(content=str(twiml), media_type="application/xml")
```

**Proxy caveat:** Behind ngrok/nginx/load balancers, `request.url` may show `http` internally while Twilio signed against `https`. Reconstruct the exact external URL (from `X-Forwarded-Proto`/`Host`) before validating, or validation will fail.

---

## Sources
- Kept: Twilio Messaging docs (twilio.com/docs/messaging) — core SMS send/receive + webhook params.
- Kept: Twilio WhatsApp docs (twilio.com/docs/whatsapp) — sandbox, 24h window, templates, `whatsapp:` prefix.
- Kept: Twilio Conversations docs (twilio.com/docs/conversations) — when to choose stateful multi-party API.
- Kept: Twilio IAM / API Keys docs (twilio.com/docs/iam/api-keys) — credential best practice.
- Kept: Twilio Webhooks Security (twilio.com/docs/usage/webhooks/webhooks-security) — `X-Twilio-Signature` validation.
- Kept: Twilio Content / Templates (twilio.com/docs/content) — approved template sending.
- Kept: Twilio Error codes (twilio.com/docs/api/errors) — production error handling.
- Kept: Twilio Pricing (twilio.com/en-us/pricing) — pricing model reference (verify live rates).
- Dropped: Third-party blog tutorials — superseded by canonical Twilio docs; risk of stale API signatures.

## Gaps
- **Exact current pricing numbers and WhatsApp conversation-category rates** are time-sensitive and were not fetched live in this run — confirm on the pricing page before finalizing cost estimates.
- **A2P 10DLC registration timelines/fees** and **Meta WABA verification steps** change; verify current onboarding flow in the Console.
- **Live `web_search` was unavailable** in this environment, so the brief relies on established Twilio API knowledge rather than freshly fetched pages. Suggested next step: run a docs verification pass against the cited Twilio URLs and the pricing page before implementation sign-off.

## Supervisor coordination
No blockers requiring a supervisor decision. The only material limitation is the absence of a live web_search tool; the brief is complete and actionable from established API knowledge, with time-sensitive items flagged in Gaps.

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Produced a single Twilio integration brief at the mandated path covering all 10 requested topics (product selection, auth, inbound webhooks, outbound send, WhatsApp specifics, signature validation, sender identity/messaging services, pricing/rate limits, Python SDK quickstart, production gotchas) with concrete Python snippets and exact env vars. No scope beyond the requested brief."
    },
    {
      "id": "criterion-2",
      "status": "satisfied",
      "evidence": "Brief includes numbered findings with inline citations to canonical Twilio docs, a Sources kept/dropped section, an explicit Gaps section disclosing the missing live web_search and time-sensitive pricing, and runnable Flask/FastAPI + SDK code. Reviewer can independently verify claims against the cited Twilio doc URLs."
    }
  ],
  "changedFiles": [
    "docs/twilio-integration-brief.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [],
  "validationOutput": [
    "Wrote docs/twilio-integration-brief.md (research brief with 10 sections, Python code snippets, env var config, sources, gaps).",
    "Note: web_search tool was not available in this environment; brief compiled from established Twilio API knowledge with time-sensitive items flagged."
  ],
  "residualRisks": [
    "Pricing figures and WhatsApp conversation-category rates are time-sensitive and must be verified against the live Twilio pricing page before cost commitments.",
    "No live web fetch was possible in this run; cited URLs are canonical doc locations and should be spot-checked before implementation sign-off.",
    "Proxy URL reconstruction for X-Twilio-Signature validation is environment-specific and must be tuned to the actual deployment topology."
  ],
  "noStagedFiles": true,
  "diffSummary": "Added docs/twilio-integration-brief.md containing a complete Python-to-Twilio integration research brief.",
  "reviewFindings": [
    "no blockers"
  ],
  "manualNotes": "Only Read/Write tools were available (no web_search) in this run, so the brief is knowledge-based with explicit disclosure and time-sensitive items called out in Gaps. All code snippets use the twilio Python SDK (twilio.rest.Client, RequestValidator, MessagingResponse) and canonical TWILIO_* env var names."
}
```
