---
id: atom-agente-conversador
title: Agente Conversador (LlmAgent)
five_wh_one_plus: what
tags:
  - component:conversador
  - layer:engine
---
## Answer

Es el motor generativo encargado de la interfaz con el humano. Recibe el contexto validado y estricto desde el Ontologizador. Su trabajo es redactar respuestas en lenguaje natural o emitir JSON estructurado para el llamado a herramientas externas (Tool Calling). Tiene estrictamente prohibido alucinar o buscar datos; si el contexto es vacío, ejecuta un punto de quiebre.