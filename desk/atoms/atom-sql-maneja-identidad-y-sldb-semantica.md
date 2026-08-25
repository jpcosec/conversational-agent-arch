---
id: atom-sql-maneja-identidad-y-sldb-semantica
title: SQL maneja Identidad y SLDB la Semántica
five_wh_one_plus: how
tags:
  - architecture:data
  - layer:persistence
---
## Answer

La arquitectura impone una separación estricta entre la identidad transaccional y el modelo cognitivo. La base de datos SQL gestiona exclusivamente el PII (Personal Identifiable Information), credenciales, la cola de eventos (CRON) y el estado temporal de la sesión (como el debounce de mensajes).

Por otro lado, SLDB actúa como una base de conocimiento pura, almacenando reglas de dominio, características de perfil y herramientas. La relación entre ambos mundos se hace mediante una tabla en SQL (`UserTraits`) que mapea de forma opaca un `user_id` relacional hacia múltiples `trait_ids` semánticos en SLDB.