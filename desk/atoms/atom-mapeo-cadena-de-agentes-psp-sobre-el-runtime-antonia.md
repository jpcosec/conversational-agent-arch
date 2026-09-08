---
id: atom-mapeo-cadena-de-agentes-psp-sobre-el-runtime-antonia
title: Mapeo cadena de agentes PSP sobre el runtime Antonia
five_wh_one_plus: what
tags:
- system:antonia
- domain:psp
- topic:arquitectura
provenance: null
---

# Mapeo cadena de agentes PSP sobre el runtime Antonia

## Answer

La cadena PSP de 5 etapas se absorbe asi en el runtime actual. (1) Sanitizacion de entrada -> PII scrubber existente (kb_agent/pii/scrubber.py) + RouterStateMachine. (2) Agente clasificador -> OrchestratorAgent (kb_agent/agents/orchestrator_agent.py) con decide_turn (kb_agent/agent.py) como fallback deterministico; clasifica el tipo de turno. (3) Agentes de dominio -> ContextCompiler (seleccion de atoms por modelo tipado) + RouterAgent (bundle justificado) + Conversador (draft_nl con LLM). (4) Agentes supervisores -> el mismo OrchestratorAgent; decide sin redactar y gobierna el turno leyendo flow_node, las transiciones permitidas (aristas transitions_to del grafo tipado de kgdb, vetadas por codigo en apply_transition_guard), scenario y user_traits del compiled_context. (5) Agente regulatorio / policy gate -> GateAgent (kb_agent/agents/gate.py) con los GateCriterion de la KB; valida la respuesta redactada ANTES de emitirla. Restricciones; una KB = un negocio; no meter roles del pipeline como sub-especialidades en la familia self (self se colapsa a [0] en compiler.py); __family__ no rutea seleccion.
