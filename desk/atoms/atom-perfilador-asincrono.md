---
id: atom-perfilador-asincrono
title: Perfilador Asincrono
five_wh_one_plus: what
tags:
- layer:runtime
- role:background
- family:user
provenance: architecture-audit
---

# Perfilador Asincrono

## Answer

Background worker (`TraitExtractor`) que consume eventos de turno cerrado desde el EventBus. Usa el LLM para inferir características del usuario contra los `TraitAtom` candidatos y hace un upsert (SQL `UserTraits`). Opera fuera del tiempo de respuesta del usuario.
