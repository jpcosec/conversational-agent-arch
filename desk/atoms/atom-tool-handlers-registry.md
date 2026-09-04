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

Mecanismo de ejecución de acciones. Las tools son funciones locales de Python mapeadas en el yaml del negocio (sección `tools`, p.ej. `crear_reserva`, `agendar_recordatorio` en Antonia; `registrar_lead`, `crear_visita` en Vitali). Un `ToolAtom` de la KB declara el schema que ve el LLM (`function_declarations`); el yaml declara quién lo ejecuta (`modulo:funcion`). Cuando el orquestador decide un `tool_call`, `execute_tool` llama al handler con `(session, user_id, args)`; el handler típicamente muta estado relacional (tablas SQL de negocio) y devuelve un dict que se agrega como System Turn al contexto para que el Conversador redacte con el resultado real. El step destino decidido junto con el tool_call se aplica sólo si la tool devolvió `status: ok`; con `faltan_datos` el flujo se queda en el step actual. Los handlers devuelven su propia clave `args` con booleanos 'vino informado' para que la PII no quede en claro en `turns.tool`.
