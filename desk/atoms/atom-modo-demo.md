---
id: atom-modo-demo
title: Modo demo
five_wh_one_plus: what
tags:
- layer:frontend
- role:boundary
- topic:demo
provenance: kb_agent/project_config.py
---

# Modo demo

## Answer

Modo opt-in del runtime que sirve las 4 vistas sin orquestador ni LLM. Se activa con `DEMO_MODE=1` y lo resuelve `ProjectConfig.demo_mode` (kb_agent/project_config.py) — nunca se enciende en modo test (`resolved_mode != "test"`) ni se setea en producción. Con el flag activo, `create_app` (frontends/chat/app.py) no exige Orchestrator y todos los `/api/*` responden datos prefabricados de `frontends/chat/demo_data.py` (config, atoms, flow, usuarios, perfiles); el chat usa `DemoStateMachineConversador`, una máquina de estados determinista (saludo -> consulta -> obtencion_datos -> tool_call) que imita al Conversador. Sobre las 4 vistas corre `frontends/shared/demo-tour.js`, un único recorrido guiado con cuadros que apuntan a elementos por `data-testid`, navega solo de vista en vista y guarda el progreso en localStorage (`demo-tour-idx`, `demo-tour-done`). Lo verifica tests/ui/test_demo_e2e.py (Playwright, marker `ui`, sin credenciales).
