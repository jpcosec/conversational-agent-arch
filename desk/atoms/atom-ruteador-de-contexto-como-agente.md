---
id: atom-ruteador-de-contexto-como-agente
title: Ruteador de contexto como agente
five_wh_one_plus: what
tags:
- layer:runtime
- role:engine
- topic:router
provenance: kb_agent/agents/router.py
---

# Ruteador de contexto como agente

## Answer

`RouterAgent` (kb_agent/agents/router.py, commit f4fcf50) es el cuarto agente LLM del diseño (Conversador, Ruteador, Orquestador, Gate), construido sobre `kb_agent.agents.base.Agent` con rol `AgentRole.ROUTER`. Decide QUÉ documentos de la KB entran al bundle de contexto del turno y lo justifica — salida tipada `RouterDecision` con `BundleEntry {doc_id, motivo, family?, score?}`, motivo OBLIGATORIO por documento (contrato de auditoría, visible en el rastro y el Turn Inspector). Regla de oro — cualquier documento de cualquier familia puede entrar si el motivo lo justifica; la familia es carga base, no límite de selección. Tiene tools reales sobre la instancia única de `knowledge_base.operations.KnowledgeOperations` del proceso — `explore_multi` (similitud semántica + fuzzy con score, default `tuning.router_max_results`), `explore` (navegar el grafo) y `show` (leer un documento antes de decidir). Su `static_instruction` (`render_router_instruction`) es doctrina del sistema, no de la KB, con el encuadre de negocio como lead-in opcional (`AgentFraming` rol `router`). Dos garantías que no dependen del modelo — `apply_security_floor` (función pura) fuerza las `RuleAtom` con tag `conversation:security` siempre, y cada `doc_id` devuelto se valida contra el reader (alucinaciones descartadas). Sin RouterAgent inyectado o si falla, `ContextCompiler._build_bundle` sigue como fallback determinista (fail-open, igual que el gate); `decisions.ruteador.source` dice cuál de los dos produjo el bundle.
