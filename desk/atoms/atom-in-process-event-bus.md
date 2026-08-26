---
id: atom-in-process-event-bus
title: InProcess Event Bus
five_wh_one_plus: what
tags:
- layer:runtime
- role:boundary
provenance: architecture-audit
---

# InProcess Event Bus

## Answer

Canal de mensajería in-memory que desacopla el cierre del turno síncrono del perfilado asíncrono. El Orquestador publica el turno aquí (`publish_turn_closed`), momento en el cual se aplica el enmascaramiento de PII antes de encolarlo.
