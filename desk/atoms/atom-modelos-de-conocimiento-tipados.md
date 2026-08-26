---
id: atom-modelos-de-conocimiento-tipados
title: Modelos de Conocimiento Tipados
five_wh_one_plus: what
tags:
- domain:self.architecture.backend
- layer:document-model
- system:sldb
- topic:knowledge-models
provenance: null
---

# Modelos de Conocimiento Tipados

## Answer

Taxonomía de 12 modelos StructuredNLDoc (SLDB) que estructuran la KB del agente, separada del store de deskops: DomainAtom (conocimiento factual), RuleAtom (heurísticas condicionales), ToolAtom (definiciones JSON-schema de tools), TraitAtom (características reusables de usuario), ConversationStep (nodos de flujo del grafo conversacional), SelfDeclaration (identidad/whoami), StyleGuide (tono y registro), CapabilityBoundary (límites y escalamiento), StrategyRule (estrategia de interacción), FallbackRule (mensajes ante contexto vacío) y GateCriterion (criterios de validación post-draft del policy gate, familia gate, invisible al compilador de turno). Viven en kb_agent/models/knowledge/ y se materializan en el store knowledge/.sldb.
