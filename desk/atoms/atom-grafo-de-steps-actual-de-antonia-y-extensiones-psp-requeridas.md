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

Grafo actual en knowledge/atoms (ConversationStep, jerarquía conversation:steps.*): saludo -> {onboarding, registro_estado}; onboarding -> registro_estado; registro_estado -> {evento_adverso, agendar_recordatorio}; evento_adverso -> despedida; agendar_recordatorio -> recompra; recompra -> despedida; despedida = terminal. Extensiones PSP requeridas como nuevos ConversationStep: (1) step derivacion_medinfo — consulta médica no-EA, registra ticket, transición a revision_humana o despedida; (2) step revision_humana — estado de espera con ticket pendiente, el equipo contactará; (3) step journey_operativo — respuesta con contenido preaprobado F0 sin generación libre; (4) step validacion_policy_gate — autovalidación de la respuesta antes de emitir. Cada step nuevo necesita: instructions, required_slots, handout_target, allowed_transitions coherentes con el grafo, grounding_atoms apuntando a las reglas/domain atoms correspondientes, completion_condition. Los steps existentes que deriven a los nuevos deben actualizar sus allowed_transitions (registro_estado y saludo son los candidatos de entrada). FAN-OUT PROPUESTO (el ejecutor puede ajustarlo con criterio sin-transiciones-colgantes): saludo -> {onboarding, registro_estado, journey_operativo, derivacion_medinfo} (la consulta operativa o médica puede llegar de entrada); registro_estado -> {evento_adverso, agendar_recordatorio, derivacion_medinfo} (una pregunta clínica no-EA puede surgir al reportar estado); derivacion_medinfo -> {revision_humana, despedida}; revision_humana -> despedida; journey_operativo -> {registro_estado, despedida}. POSICIÓN DE validacion_policy_gate: NO es un nodo del grafo conversacional de usuario — es un checkpoint post-draft; modelarlo como step SIN entradas desde otros steps (ningún allowed_transitions apunta a él) y con transición de salida a revision_humana (caso rechazo); su rol en esta fase es documental+autovalidación vía instructions, hasta que la fase de código lo consuma.
