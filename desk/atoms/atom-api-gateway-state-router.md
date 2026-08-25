---
id: atom-api-gateway-state-router
title: API Gateway y State Router
five_wh_one_plus: what
tags:
  - component:router
  - layer:routing
---
## Answer

Es el componente de entrada del sistema. Actúa como servidor web (ej. FastAPI) que recibe los webhooks externos (ej. Twilio) o peticiones HTTP. Su rol principal es gestionar la **Máquina de Estados de la Conversación**, manejando el `buffering` (debounce para ráfagas de mensajes) y enrutando el flujo hacia el Ontologizador o el Conversador según el nodo activo en la sesión del usuario.