---
id: atom-capas-de-verificación-y-release
title: Capas de verificación y release
five_wh_one_plus: how
tags:
- layer:ops
- role:boundary
- topic:ci-release
provenance: README.md
---

# Capas de verificación y release

## Answer

Cinco capas de verificación con su comando (README.md, sección "Ramas, CI y releases"). `static` (CI, job `static` de .github/workflows/ci.yml, sin deps) — `compileall`, `project.config.yaml` válido con negocio activo, y sin hardcodes de negocio en string-literals vivos de `kb_agent/`. `suite` (CI y local) — unit + integration sin LLM, `SKIP_LLM_TESTS=1 python -m pytest tests/unit tests/integration`; en CI instala `sldb`/`kgdb`/`deskops` por git. `ui` (local) — Playwright + Chromium contra la app in-process, `python -m pytest tests/ui` (marker `ui`, se salta sin Playwright). `llm` / `simulation` (local con `.env`, Vertex ADC vía `GOOGLE_GENAI_USE_VERTEXAI` + `GOOGLE_CLOUD_PROJECT`) — `set -a; source .env; set +a; python -m pytest tests/e2e`, smoke + simulaciones agente-vs-usuario con juez LLM. Release gate (local) — `deploy/release.sh`, preflight + suite offline + deploy + tag + `production`, fuente de verdad de qué hay arriba. CI corre en push a `main`, `dev` y `production` y en cada PR; los tests con marker `llm` se saltan solos sin credenciales o con `SKIP_LLM_TESTS=1` (tests/conftest.py). `known_gap` es un xfail estricto que documenta un defecto conocido del runtime y exige quitar la marca al arreglarse. Release — desde `main` limpio (el script rechaza working tree sucio), `deploy/release.sh [tag]` (sin tag, `release-YYYYMMDD-<sha>`; `SKIP_DEPLOY=1` sólo gate + tag). Secuencia — suite offline => `modal deploy deploy/modal_app.py` (app `kb-agent-runtime`, secret `kb-agent-runtime-gcp`, volumen `kb-agent-runtime-data`; alembic migra al arrancar el contenedor) => `production` = SHA desplegado + tag; no hace push, lo imprime — `git push origin production && git push origin <tag>`. Antes de producción se prueba en el endpoint dev (`MODAL_APP_NAME=kb-agent-runtime-dev`); `DEMO_MODE=1` es opt-in y nunca se setea en producción.
