# Playwright UI smoke test

Smoke E2E de las dos UIs servidas por `frontends.chat.server`:
- **Chat dashboard** (`/`) — Auditable Agent Runtime: turno real Gemini +
  Turn Inspector (latency, model route, atoms del contexto).
- **Flow editor** (`/conversation_flow_editor`) — grafo de `ConversationStep`
  del store (`/api/flow`).

## Correr

```bash
# 1. levantar el server (misma shell o background estable)
python3 -m uvicorn frontends.chat.server:app --host 127.0.0.1 --port 8100 &

# 2. correr el smoke (usa Gemini real via .env)
python3 tests/e2e/playwright/test_ui_playwright.py
```

Salida: `10/10 checks passed`. Screenshots en `/tmp/pw_chat.png`,
`/tmp/pw_flow.png`.

## Notas
- No usa mocks: el chat ejecuta un turno real (Vertex ADC).
- La UI auto-selecciona el turno real (`t1`); el inspector se puebla solo.
- Requiere `playwright` + chromium (`playwright install chromium`).
