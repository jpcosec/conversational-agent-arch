---
id: atom-estrategia-de-testing
title: Estrategia de Testing de 4 Capas
five_wh_one_plus: what
tags:
- layer:ops
- role:boundary
provenance: architecture-audit
---

# Estrategia de Testing de 4 Capas

## Answer

Suite de pruebas dividida en Unit (lógica pura y orquestador con LLM inyectado fake), Integration (API y flujos), E2E (smoke tests con Gemini real y harness de simulación Agente-vs-Agente) y UI (Playwright). Como capas de verificación se ejecutan por separado — `suite` = unit + integration sin LLM (`SKIP_LLM_TESTS=1 python -m pytest tests/unit tests/integration`, también en CI); `ui` = `python -m pytest tests/ui` con Chromium contra la app in-process (marker `ui`, se salta sin Playwright; incluye tests/ui/test_demo_e2e.py del modo demo); `llm` / `simulation` = `tests/e2e` con credenciales Vertex del `.env` (marker `llm`, se salta solo sin credenciales o con `SKIP_LLM_TESTS=1`, tests/conftest.py), smoke + simulaciones agente-vs-usuario con juez LLM (tests/e2e/simulation). Los escenarios con `known_gap` documentan un defecto conocido del runtime como xfail estricto — al arreglarse el test exige quitar la marca; sólo cuando el resultado del gap varía con el LLM se declara `known_gap_strict=False` con el motivo obligatorio en `known_gap_variance` (tests/e2e/simulation/scenarios.py). Todo test aísla el estado usando la KB de pruebas y una base SQL efímera.
