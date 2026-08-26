---
id: atom-grafo-de-steps-actual-de-antonia-y-extensiones-psp-requeridas
title: Grafo de steps actual de Antonia y extensiones PSP requeridas
five_wh_one_plus: where
tags:
- system:antonia
- domain:psp
- topic:flujo-conversacional
provenance: null
---

# Grafo de steps actual de Antonia y extensiones PSP requeridas

## Answer

Grafo actual en knowledge/atoms (ConversationStep, jerarquía conversation:steps.*): saludo -> {onboarding, registro_estado}; onboarding -> registro_estado; registro_estado -> {evento_adverso, agendar_recordatorio}; evento_adverso -> despedida; agendar_recordatorio -> recompra; recompra -> despedida; despedida = terminal. Extensiones PSP requeridas como nuevos ConversationStep: (1) step derivacion_medinfo — consulta médica no-EA, registra ticket, transición a revision_humana o despedida; (2) step revision_humana — estado de espera con ticket pendiente, el equipo contactará; (3) step journey_operativo — respuesta con contenido preaprobado F0 sin generación libre; (4) step validacion_policy_gate — autovalidación de la respuesta antes de emitir. Cada step nuevo necesita: instructions, required_slots, handout_target, allowed_transitions coherentes con el grafo, grounding_atoms apuntando a las reglas/domain atoms correspondientes, completion_condition. Los steps existentes que deriven a los nuevos deben actualizar sus allowed_transitions (registro_estado y saludo son los candidatos de entrada).
