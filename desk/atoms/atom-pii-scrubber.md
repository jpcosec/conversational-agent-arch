---
id: atom-pii-scrubber
title: PII Scrubber
five_wh_one_plus: what
tags:
- layer:runtime
- role:boundary
provenance: architecture-audit
---

# PII Scrubber

## Answer

Capa de interceptación de privacidad. El Orquestador lo invoca para enmascarar (scrub) todo contenido antes de persistirlo en el historial SQL (`ChatHistory`) y antes de publicarlo en el EventBus, asegurando aislamiento absoluto de datos personales.
