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

Suite de pruebas dividida en Unit (lógica pura y orquestador con LLM inyectado fake), Integration (API y flujos), E2E (smoke tests con Gemini real y harness de simulación Agente-vs-Agente), y UI (Playwright). Todo test aísla el estado usando la KB de pruebas y una base SQL efímera.
