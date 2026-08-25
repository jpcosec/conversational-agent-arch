---
id: atom-aislamiento-estricto-de-pii
title: Aislamiento Estricto de PII
five_wh_one_plus: what
tags:
- domain:standards.privacy
- layer:persistence
- system:sql
- topic:pii
provenance: null
---

# Aislamiento Estricto de PII

## Answer

Regla dura: ningún dato personal identificable (nombres, teléfonos, emails) puede salir de la tabla de Identidad SQL hacia motores cognitivos (Reflector, Perfilador) o logs. Debe enmascararse o tokenizarse en origen antes de cualquier lectura downstream.
