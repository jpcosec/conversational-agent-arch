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

Background worker (`TraitExtractor`) que consume eventos de turno cerrado desde el EventBus. Antes de llamar al LLM aplica un pre-filtro semántico: rankea los `TraitAtom` candidatos por similitud coseno turno-vs-trait (reusa el embedder cacheado del proceso, mismo patrón que `ContextCompiler`) y pasa solo el top-k al LLM en vez de TODOS los traits cada turno; es fail-open (sin embedder, sin traits con vector o si el catalogo cabe en el top-k, pasan todos) y los traits sin embedding se anexan siempre fuera del ranking. El LLM infiere las características y se hace upsert en SQL `UserTraits` con precedencia por fuente: `form` (datos duros declarados en el formulario/registro, `confidence=1.0`, vía `ingest_form_traits`) gana sobre `perfilador` (inferencia LLM); el upsert respeta siempre el `source` de mayor autoridad. Opera fuera del tiempo de respuesta del usuario.
