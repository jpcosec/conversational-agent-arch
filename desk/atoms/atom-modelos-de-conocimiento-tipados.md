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

Taxonomía de 11 modelos StructuredNLDoc (SLDB) que estructuran la KB del agente, separada del store de deskops: DomainAtom (conocimiento factual), RuleAtom (heurísticas condicionales), ToolAtom (definiciones JSON-schema de tools), TraitAtom (características reusables de usuario), ConversationStep (nodos de flujo), SelfDeclaration (identidad/whoami), StyleGuide (tono y registro), CapabilityBoundary (límites y escalamiento), StrategyRule (estrategia de interacción) y FallbackRule (mensajes ante contexto vacío). Viven en kb_agent/models/knowledge/ y se materializan en el store .knowledge/.
