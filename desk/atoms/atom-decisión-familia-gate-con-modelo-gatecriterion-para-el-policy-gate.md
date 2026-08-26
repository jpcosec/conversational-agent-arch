---
id: atom-decisión-familia-gate-con-modelo-gatecriterion-para-el-policy-gate
title: 'Decisión: familia gate con modelo GateCriterion para el policy gate'
five_wh_one_plus: why
tags:
- system:antonia
- domain:psp
- topic:policy-gate
- topic:modelacion
provenance: null
---

# Decisión: familia gate con modelo GateCriterion para el policy gate

## Answer

Se define una familia nueva 'gate' con un único modelo GateCriterion (atom_type: gate, __family__='gate', __semantics__ type:[knowledge,gate]). Justificación: (1) el gate tiene un eje de activación que ninguna familia cubre — se activa POST-DRAFT sobre la respuesta redactada, no sobre la pregunta (domain), ni el estado (conversation), ni siempre (self), ni la identidad (user); es un sexto eje en retrieval-architecture §2. (2) Precedente: la familia user tiene un solo modelo (TraitAtom); familia = eje de activación, no cantidad de modelos. (3) Ningún modelo existente sirve: RuleAtom es familia domain y entraría a rules en todos los turnos contaminando el contexto del Conversador; CapabilityBoundary es familia self y _extract_persona usa boundaries[0], con riesgo de desplazar boundary-antonia-clinico; ConversationStep modela el paso del flujo, no los criterios. (4) Seguridad: el compilador itera _MODEL_TYPES literales y 'gate' no está — los átomos gate son invisibles al runtime actual: cero regresión, cero colisión con persona. El código futuro del gate los selecciona con reader.find('type.knowledge.gate'). Campos del modelo: criterion (qué evaluar en la respuesta redactada), approval_condition (cuándo pasa), rejection_action (qué hacer al rechazar: derivar + motivo), tags con namespace gate:* (gate:regulatorio.dosis, gate:corpus, gate:derivacion). Costo: 1 archivo kb_agent/models/knowledge/gate.py + export en __init__.py + sldb models add + namespace gate:* en tag-namespaces. Es operación de modelación KB (ciclo de vida modelation-guide pasos 1-6), no código de runtime.
