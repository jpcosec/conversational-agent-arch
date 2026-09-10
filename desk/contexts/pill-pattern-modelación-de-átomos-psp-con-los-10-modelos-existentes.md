---
# pill-xxx
id: pill-pattern-modelación-de-átomos-psp-con-los-10-modelos-existentes
# e.g., language:python, library:pydantic
tags:
- system:antonia
- domain:psp
- topic:modelacion
---

# Pattern: Modelación de átomos PSP con los 10 modelos existentes

## What

_Define the context or guardrail this pill carries._

Mapa de modelacion para las piezas PSP. Reglas clasificadoras de las 4 ramas -> RuleAtom (answer + conditions + applies_to, tags conversation:classification). Steps nuevos (medinfo, revision_humana, journey_operativo, validacion_policy_gate) -> ConversationStep (instructions, required_slots, completion_condition, tag conversation:steps.nombre) mas sus relaciones como RelationDoc de kgdb en knowledge/relations/ (transitions_to, grounded_by, uses_tool). Criterios del policy gate -> GateCriterion, MODELO NUEVO de la familia gate (criterion, approval_condition, rejection_action, tags gate:*), unico modelo nuevo autorizado, decision en atom-decisión-familia-gate-con-modelo-gatecriterion-para-el-policy-gate. Informacion MedInfo/FV/titulacion/molecula de negocio -> DomainAtom (answer, tags domain:*). Limites nuevos -> extender CapabilityBoundary existente solo si la restriccion es del agente conversacional (no del gate).

## Why

_Explain why this context matters for safe execution._

La heurística de modelation-guide dice crear modelo nuevo solo si hay forma de campo distinta, comportamiento de compilación distinto o validación distinta. Las piezas conversacionales PSP son variantes de RuleAtom, ConversationStep o DomainAtom distinguidas por tags. El gate SÍ cumple el criterio 2 (comportamiento de compilación distinto) — se activa post-draft sobre la respuesta redactada, un eje de activación que ninguna familia existente tiene; por eso GateCriterion es familia nueva. El compilador no itera el tipo gate en _MODEL_TYPES, así que sus átomos son invisibles al turno actual — cero regresión.

## When

_Describe when an agent should apply this pill._

Al crear cada átomo nuevo de la tarea PSP; consultar antes de decidir el atom_type.

## Where

_Name the files, surfaces, or scope this pill applies to._

knowledge/atoms/*.md; taxonomía en knowledge_base/taxonomy/modelation-guide.md y retrieval-architecture.md; los 5 ejes de activación: self:* siempre, domain:* por relevancia, conversation:* por estado, user:traits.* por identidad, source:* nunca.

## How

_Describe the correct way to apply this guidance._

Cada atomo lleva id con prefijo del tipo (rule-antonia-*, step-antonia-*, gate-antonia-*, atom-antonia-*), title claro, atom_type del modelo, tags con eje correcto, summary de una frase (OBLIGATORIO en todos los modelos porque IndexProxies.summary es campo requerido) y los campos del modelo en secciones Markdown (Answer, Conditions, Instructions, etc.). RuleAtom y DomainAtom exigen ademas five_wh_one_plus (uno de what/why/how/how_not/when/where/for_whom). Steps ademas llevan kind (interaccion_simple / obtencion_datos / llamado_tool / handout) y domain_ref psp-selfix; sus transiciones, grounding y tool se declaran como RelationDoc (source_id/target_id en formato Modelo:nombre) creados por pron.Store (ver scripts/migrate_step_relations.py como ejemplo). Para GateCriterion calcar la estructura de boundary.py (herencia de IndexProxies, template con marcadores rev/optrev, AtomTag). Registro del modelo nuevo con sldb models add kb_agent.models.knowledge:GateCriterion --store knowledge/.sldb --pythonpath . y luego sldb stores update --store knowledge/.sldb --pythonpath . para reindexar. Los embeddings no van en el frontmatter; despues de agregar atomos correr python -m knowledge_base --kb knowledge index embeddings (DocumentIndex de pron en knowledge/.pron/, solo embebe lo que cambio).

## How Not

_Describe the shortcut or failure mode to avoid._

No usar atom_type como tag (el compilador filtra por modelo, no por tag). No mezclar dos formas de campo en un modelo con enum. No modelar los criterios del gate como RuleAtom ni CapabilityBoundary (RuleAtom es familia domain y contaminaria el contexto del Conversador en todos los turnos; CapabilityBoundary es familia self y _extract_persona usa boundaries[0], con riesgo de desplazar boundary-antonia-clinico). Usar el modelo GateCriterion de la familia gate (ver atom-decisión-familia-gate-con-modelo-gatecriterion-para-el-policy-gate). No crear ningun otro modelo mas alla de GateCriterion. No escribir transiciones ni grounding como texto en el step; son RelationDoc, y el ingest tipado (World.refresh) falla ante una arista hacia un documento inexistente.
