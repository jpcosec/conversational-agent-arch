---
id: atom-configuración-por-capas-y-tuning
title: Configuración por capas y tuning
five_wh_one_plus: what
tags:
- layer:ops
- role:boundary
- topic:configuration
provenance: docs/CONFIGURATION.md
---

# Configuración por capas y tuning

## Answer

La configuración vive en tres capas, no en el código (docs/CONFIGURATION.md). (1) KB (`knowledge/`, store `.sldb`) — todo texto que lee o escribe un LLM (hechos, reglas, identidad, flujo, encuadre de agentes). (2) YAML (`project.config.yaml`, bloque `project:`) — valores y parámetros, con override por variable de entorno; además de identidad, `kb_root`, DBs, `model`, `tools`, `server` y `ui`, tiene dos bloques nuevos cargados por `load_project_config` (kb_agent/project_config.py). `tuning` (`TuningConfig`) — `max_bundle_size` (tope del bundle en ContextCompiler), `history_limit` (mensajes recientes en el contexto), `router_max_results` (default de `explore_multi` del ruteador) y `tool_timeout_ms` (timeout de una tool call), antes constantes hardcodeadas; overrides `MAX_BUNDLE_SIZE`, `HISTORY_LIMIT`, `ROUTER_MAX_RESULTS`, `TOOL_TIMEOUT_MS`. `deploy` (`DeployConfig`) — `modal_app_name` (nombre de la app y del volumen `<app>-data`; `MODAL_APP_NAME` tiene prioridad), `gcp_secret_name` (Secret con el ADC de Vertex), `twilio_secret_name` (null => `/webhooks/twilio` responde 503), `min_containers` y `serve_timeout_s`, leídos por deploy/modal_app.py al importar. (3) Runtime (`kb_agent/`) — mecánica fija (11 tipos de documento, máquina de estados, tag `conversation:security`); no es config.
