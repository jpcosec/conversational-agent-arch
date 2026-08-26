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

El policy gate (etapa 5 PSP, compuerta regulatoria final) debe implementarse como agente separado del orquestador, con sus propios átomos en knowledge/: sus reglas son materia médico-regulatoria que cambia con el corpus aprobado (folleto ISP + material Medical), no lógica determinista de código. Interviene DESPUÉS del draft del Conversador y ANTES de emitir al paciente: evalúa la respuesta redactada contra criterios de aprobación (no indica dosis, no diagnostica, no promete resultados, solo información del corpus aprobado, deriva cuando corresponde). Si rechaza -> deriva a revisión humana con el borrador y el motivo. Mientras no exista el paso de código que lo invoque, sus criterios pueden vivir en la KB como reglas de autovalidación que el LLM aplica estadísticamente; la garantía dura requiere código posterior. El orquestador (decide_turn) NO necesita KB propia: su lógica es determinista y testeable.
