---
id: atom-persistencia-sql
title: 'SQL: Identidad y Estado'
five_wh_one_plus: what
tags:
- layer:knowledge
- role:data
provenance: architecture-audit
---

# SQL: Identidad y Estado

## Answer

Capa de persistencia relacional transaccional (vía SQLAlchemy). Almacena los `Users`, la máquina de estados persistente (`SessionState`), el `ChatHistory` (ya scrubbeado de PII), los mapeos relacionales de `UserTraits`, y las tablas de negocio como Reservas.
