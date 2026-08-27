---
id: atom-encuadre-de-agentes-desde-la-kb-agentframing
title: Encuadre de agentes desde la KB (AgentFraming)
five_wh_one_plus: why
tags:
- layer:knowledge
- role:engine
- family:agent
- topic:agent-framing
provenance: docs/CONFIGURATION.md
---

# Encuadre de agentes desde la KB (AgentFraming)

## Answer

Porque una KB = un negocio y el código no puede hardcodear el dominio. Cada agente LLM arma su prompt en dos capas — la doctrina (mecánica fija del runtime — familias, regla de oro, formato de salida) vive en las funciones `render_*` de `kb_agent/agents/` (`render_gate_criteria`, `render_router_instruction`, `render_orchestrator_flow`) y se mantiene business-neutral; el encuadre (quién es este agente EN ESTE negocio, más ejemplos de dominio) vive en la KB como documento tipado `AgentFraming` (kb_agent/models/knowledge/agent_framing.py, familia `agent`, campos `role`, `framing`, `examples`). Los roles válidos son el enum `AgentRole` de kb_agent/agents/base.py (`conversador` | `router` | `orchestrator` | `gate`), único punto de verdad de qué agentes existen. El Orquestador carga el encuadre por rol en `Orchestrator._load_agent_framing(role)` y lo inyecta como lead-in al `render_*` correspondiente; sin `AgentFraming` para un rol, el agente cae a un encuadre genérico neutro. Ejemplos en la KB de Antonia — knowledge/atoms/agent-antonia-gate.md (gate regulatorio de farmacovigilancia) y agent-antonia-router.md (ejemplos clínicos del ruteador). Detalle en docs/CONFIGURATION.md.
