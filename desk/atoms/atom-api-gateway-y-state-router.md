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

Es el componente de entrada del sistema. Actúa como servidor web (FastAPI) que recibe webhooks (Twilio) o HTTP. Gestiona la Máquina de Estados, manejando el buffering (debounce) y enrutando el flujo al Ontologizador o Conversador.
