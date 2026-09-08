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

Grafo de Antonia como aristas tipadas de kgdb (RelationDoc transitions_to en knowledge/relations/, tipos en knowledge/relations/types/, migrado el 2026-09-08 desde el texto libre allowed_transitions). saludo -> {onboarding, registro_estado, journey_operativo, derivacion_medinfo, enrolamiento}; enrolamiento -> {derivacion_medinfo, onboarding}; onboarding -> registro_estado; registro_estado -> {evento_adverso, agendar_recordatorio, derivacion_medinfo}; evento_adverso -> despedida; agendar_recordatorio -> recompra; recompra -> despedida; journey_operativo -> {registro_estado, despedida}; derivacion_medinfo -> {revision_humana, despedida}; revision_humana -> despedida; validacion_policy_gate -> revision_humana (sin entradas; es el checkpoint post-draft, no un nodo del flujo del usuario); despedida es terminal. Un step nuevo necesita instructions, required_slots, handout_target, completion_condition, tag conversation:steps.<nombre>, y sus relaciones como RelationDoc (transitions_to hacia los steps destino, grounded_by hacia las reglas/domain atoms que lo sustentan, uses_tool si ejecuta una tool). El ingest tipado (World.refresh) rechaza una arista hacia un documento inexistente, asi que no puede quedar una transicion colgante.
