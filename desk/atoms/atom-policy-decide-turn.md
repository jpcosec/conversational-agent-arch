---
id: atom-policy-decide-turn
title: Policy Pura (decide_turn)
five_wh_one_plus: what
tags:
- layer:runtime
- role:engine
provenance: architecture-audit
---

# Policy Pura (decide_turn)

## Answer

Función de evaluación pura (`decide_turn`) sin estado ni I/O. Analiza el contexto compilado y determina estrictamente la acción a seguir devolviendo un `kind`: `tool_call` (si hay intención y parámetros válidos), `fallback` (si falta grounding o el contexto está vacío), o `nl` (lenguaje natural).
