---
id: atom-agente-conversador
title: Agente Conversador
five_wh_one_plus: what
tags:
- layer:runtime
- role:engine
provenance: architecture-audit
---

# Agente Conversador

## Answer

Motor generativo de lenguaje natural (`GeminiConversador`). Recibe el contexto validado (y el resultado de una tool si la hubo) y redacta la respuesta final usando el LLM externo. No alucina ni toma decisiones de flujo; obedece la identidad, estilo y límites provistos por el Ontologizador.
