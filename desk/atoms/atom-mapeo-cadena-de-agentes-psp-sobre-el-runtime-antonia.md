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

La cadena PSP de 5 etapas se absorbe así en el runtime actual: (1) Sanitización de entrada -> PII scrubber existente (kb_agent/pii/scrubber.py) + RouterStateMachine. (2) Agente clasificador -> decide_turn (kb_agent/agent.py), que debe renombrarse conceptualmente a orquestador; clasifica el tipo de turno. (3) Agentes de dominio -> ContextCompiler (selección de atoms por modelo tipado) + Conversador (draft_nl con LLM). (4) Agentes supervisores -> el mismo orquestador (decide_turn): decide sin redactar, gobierna el turno; para ser supervisor real debe leer flow_node, allowed_transitions, scenario y user_traits que ya existen en compiled_context pero hoy no consume. (5) Agente regulatorio / policy gate -> NO existe; debe ser un agente separado con su propia rama de modelos en knowledge, que valida la respuesta redactada ANTES de emitirla al paciente. Restricciones: una KB = un negocio; no meter roles del pipeline como sub-especialidades en la familia self (self se colapsa a [0] en compiler.py); __family__ no rutea selección.
