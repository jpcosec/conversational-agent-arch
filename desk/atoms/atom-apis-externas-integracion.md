---
id: atom-apis-externas-integracion
title: APIs Externas (Integración)
five_wh_one_plus: what
tags:
  - component:api
  - layer:external
---
## Answer

Representa los servicios de terceros (Google Calendar, CRMs, Twilio, bases de datos externas) que interactúan con la arquitectura. Su ejecución obliga a la Máquina de Estados a pausarse (`waiting_tool`) y sus retornos (JSON) se inyectan siempre de vuelta al contexto de la conversación como "System Turns" para que el Conversador redacte una conclusión.