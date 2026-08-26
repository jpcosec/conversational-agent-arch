---
id: atom-garantia-cero-alucinaciones
title: "Garant\xEDa Cero Alucinaciones"
five_wh_one_plus: what
tags:
- layer:business
- family:concepts
provenance: architecture-audit
---

# Garantía Cero Alucinaciones

## Answer

Regla arquitectónica estricta: el LLM tiene prohibido inventar información. Si el Ontologizador compila un contexto vacío (sin hechos ni reglas que sustenten la consulta del usuario), la máquina de estados fuerza una transición a un nodo de `BREAKPOINT_MISS`, obligando al agente a usar un mensaje de `fallback` determinista en lugar de alucinar una respuesta.
