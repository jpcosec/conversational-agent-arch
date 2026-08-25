---
id: atom-sql-capa-identidad-y-estado
title: SQL DB (Identidad, Estado, Cron)
five_wh_one_plus: what
tags:
  - component:sql
  - layer:persistence
---
## Answer

La capa de persistencia relacional estricta. Aquí reside la identidad transaccional: credenciales, tokens de webhook, datos PII (nombres, correos), el registro del estado efímero/pausado de la Máquina de Estados, el mapeo `user_id -> trait_id`, y la cola de eventos programados (CRON) para la proactividad del agente. Ningún LLM lee directamente de acá.