---
id: atom-policy-gate-como-agente-separado-con-rama-kb-propia
title: Policy gate como agente separado con rama KB propia
five_wh_one_plus: how
tags:
- system:antonia
- domain:psp
- topic:policy-gate
provenance: null
---

# Policy gate como agente separado con rama KB propia

## Answer

El policy gate (etapa 5 PSP, compuerta regulatoria final) es un agente separado del orquestador con rama KB propia — `GateAgent` en kb_agent/agents/gate.py, sobre `kb_agent.agents.base.Agent` con rol `AgentRole.GATE`, `include_contents=False` y salida tipada `GateVerdict {approved, reasons, action, criterion_ids}`. Interviene DESPUÉS del draft del Conversador y ANTES de emitir al paciente (`Orchestrator._policy_gate`) — juzga la respuesta redactada contra los `GateCriterion` de la KB (familia `gate`, campos `criterion`, `approval_condition`, `rejection_action`), renderizados una vez en `static_instruction` por `render_gate_criteria` con el encuadre de negocio que llega de un `AgentFraming` de rol `gate` (knowledge/atoms/agent-antonia-gate.md); agregar un criterio a la KB cambia el juez sin tocar código (test de gobernanza en tests/unit/test_gate_agent.py). El veredicto es `approved` true sólo si TODOS los criterios se cumplen, con `action` `pass` | `handoff` (derivar la revisión a un humano con el borrador y el motivo) | `protocol` (aplicar un protocolo específico, p.ej. farmacovigilancia) y los `criterion_ids` violados. La única parte no gobernada por la KB es el pre-filtro determinista `response_claims_completed_action` (criterio sintético `gate-integridad-accion-no-ejecutada`) que rechaza respuestas que afirman una acción sin tool ejecutada en el turno ni en la sesión. Sin criterios en la KB o si el LLM falla, el gate aprueba (fail-open). El orquestador (decide_turn) sigue sin KB propia — su lógica es determinista y testeable.
