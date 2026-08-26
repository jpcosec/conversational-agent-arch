---
id: atom-api-gateway-y-state-router
title: API Gateway y State Router
five_wh_one_plus: what
tags:
- domain:self.architecture.backend
- layer:runtime
- system:kb-agent
- topic:routing
provenance: null
---

# API Gateway y State Router

## Answer

Componente de entrada del sistema: un servidor FastAPI (frontends/chat/server.py) que recibe peticiones HTTP y sirve las UIs. Gestiona la Máquina de Estados (kb_agent/state_machine.py) con buffering (debounce) y enruta cada turno al Ontologizador o al Conversador vía el Orchestrator. La ingesta por webhooks externos (Twilio/WhatsApp) es un canal previsto en el despliegue; aún no cableado en runtime.
