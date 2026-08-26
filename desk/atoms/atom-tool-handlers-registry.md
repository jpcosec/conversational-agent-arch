---
id: atom-tool-handlers-registry
title: Tool Handlers y Registry
five_wh_one_plus: what
tags:
- layer:runtime
- role:boundary
provenance: architecture-audit
---

# Tool Handlers y Registry

## Answer

Mecanismo de ejecución de acciones. Las tools son funciones locales de Python (`crear_reserva`, `agendar_recordatorio`) mapeadas en el `project.config.yaml`. Cuando la policy decide ejecutarlas, el Orquestador llama al handler, el cual típicamente muta estado relacional (tablas SQL de negocio).
