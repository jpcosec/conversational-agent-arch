---
id: task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp
status: ready_for_testing
summary: ''
tags:
- workspace:desk
- artifact:task
routine: routine-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp
current_node: checklist-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-closeout-ready
history:
- operator-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-activate
- operator-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-ready-for-testing
references: []
depends_on: []
pills:
- desk/contexts/pill-guardrail-extensión-kb-first-código-solo-si-es-imprescindible.md
- desk/contexts/pill-pattern-modelación-de-átomos-psp-con-los-10-modelos-existentes.md
- desk/contexts/pill-adr-compliance-farmacéutico-en-el-contenido-de-la-kb-antonia.md
files:
- kb_agent/models/knowledge/gate.py
- kb_agent/models/knowledge/__init__.py
- knowledge/atoms/rule-antonia-clasificacion-operacional.md
- knowledge/atoms/rule-antonia-clasificacion-medinfo.md
- knowledge/atoms/rule-antonia-clasificacion-tratamiento.md
- knowledge/atoms/rule-antonia-eventos-adversos.md
- knowledge/atoms/step-antonia-derivacion-medinfo.md
- knowledge/atoms/step-antonia-revision-humana.md
- knowledge/atoms/step-antonia-journey-operativo.md
- knowledge/atoms/step-antonia-validacion-policy-gate.md
- knowledge/atoms/step-antonia-saludo.md
- knowledge/atoms/step-antonia-registro-estado.md
- knowledge/atoms/gate-antonia-dosis.md
- knowledge/atoms/gate-antonia-diagnostico.md
- knowledge/atoms/gate-antonia-corpus.md
- knowledge/atoms/gate-antonia-derivacion.md
- knowledge/atoms/gate-antonia-promesas.md
- knowledge/atoms/atom-antonia-medinfo.md
- knowledge/atoms/atom-antonia-farmacovigilancia.md
- knowledge/atoms/atom-antonia-journeys.md
- knowledge/atoms/atom-antonia-titulacion.md
- knowledge/atoms/atom-antonia-molecula.md
- knowledge/desk/atoms/tag-namespaces.yaml
- knowledge/.sldb/
checklists:
- checklist-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-execution-ready
- checklist-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-testing-ready
- checklist-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-closeout-ready
task_type: design
inherits_from: []
inherit_acceptance_context: false
atoms:
- atom-mapeo-cadena-de-agentes-psp-sobre-el-runtime-antonia
- atom-clasificación-de-4-ramas-del-flujo-psp
- atom-policy-gate-como-agente-separado-con-rama-kb-propia
- atom-grafo-de-steps-actual-de-antonia-y-extensiones-psp-requeridas
- atom-decisión-familia-gate-con-modelo-gatecriterion-para-el-policy-gate
closeout_evidence_verified: false
---

# Extender el flujo conversacional de la KB Antonia para cumplir la cadena de agentes PSP

## Rationale

_Explain why this task exists or the business driver behind it._

El negocio PSP Selfix (Laboratorio Chile / Teva) exige una cadena de atención de 5 etapas (sanitización, clasificador, agentes de dominio, supervisores, compuerta regulatoria) y un árbol de decisión de 4 ramas (journey operativo F0, derivación FV, derivación MedInfo, respuesta IA con policy gate) definidos en docs/psp-arquitectura-resumen.md y specs/psp-flujo-atencion-chatbot.yml del proyecto /home/jp/AntonIA/projects/teva/PSP/. El runtime actual absorbe parcialmente los roles (decide_turn=orquestador/supervisor, ContextCompiler+Conversador=agentes de dominio, PII scrubber=sanitización), pero la KB de Antonia solo modela la rama de eventos adversos. La decisión de diseño es KB-first: extender knowledge/ lo máximo posible sin tocar código del runtime, porque el compilador ya entrega toda la KB al LLM por turno y el conocimiento bien redactado cambia el comportamiento sin riesgo de regresión.

## Goal

_Describe the concrete result this task must produce._

La KB de Antonia (knowledge/atoms/) modela completo el flujo de atención PSP: las 4 ramas de clasificación como RuleAtom, los steps faltantes del grafo conversacional (derivación MedInfo, revisión humana, journey operativo F0, autovalidación policy gate) como ConversationStep con transiciones coherentes, los criterios regulatorios del policy gate como átomos GateCriterion de la nueva familia gate (modelo nuevo, invisible al runtime actual), y los domain atoms de soporte (MedInfo, proceso FV, journeys, titulación, molécula) que completan la ontología cerrada PSP — todo indexado en el store SLDB y verificable por conversación real contra el runtime sin ninguna modificación del código de turno (decide_turn, compiler, state_machine, orchestrator).

## Scope

_State what is in scope and what is out of scope._

IN — (1) Reglas de clasificación: 4 RuleAtom nuevos (rule-antonia-clasificacion-operacional, rule-antonia-clasificacion-medinfo, rule-antonia-clasificacion-tratamiento y extensión de conditions en rule-antonia-eventos-adversos si hace falta alinearla con los 4 criterios mínimos de reporte PSP), cada uno con conditions que describan señales de la rama y answer que instruya la derivación correcta. (2) Steps nuevos: step-antonia-derivacion-medinfo, step-antonia-revision-humana, step-antonia-journey-operativo, step-antonia-validacion-policy-gate — cada uno con instructions, required_slots, handout_target, allowed_transitions, grounding_atoms y completion_condition; actualización de allowed_transitions en step-antonia-saludo y step-antonia-registro-estado para enrutar hacia los steps nuevos. (3) Modelo GateCriterion (familia gate, decisión registrada en atom-decisión-familia-gate-con-modelo-gatecriterion-para-el-policy-gate): crear kb_agent/models/knowledge/gate.py con atom_type gate, __family__ = "gate", campos criterion / approval_condition / rejection_action / tags; exportarlo en __init__.py, registrarlo con sldb models add y declarar el namespace gate:* en tag-namespaces. Es modelación KB (ciclo de vida de modelation-guide, pasos 1-6), no código de runtime: el compilador no itera "gate" en _MODEL_TYPES, por lo que los átomos gate son invisibles al turno actual (cero regresión, cero colisión con persona). (4) Átomos gate: criterios regulatorios de aprobación/rechazo como GateCriterion — gate-antonia-dosis (la respuesta no indica ni comenta dosis), gate-antonia-diagnostico (no diagnostica ni interpreta síntomas), gate-antonia-corpus (solo información del corpus aprobado), gate-antonia-derivacion (deriva cuando corresponde: EA a FV, clínica a MedInfo/médico), gate-antonia-promesas (no promete resultados ni tiempos fuera del programa); cada uno con criterion, approval_condition y rejection_action (encolar a revisión humana con el borrador y el motivo). (5) Domain atoms de soporte que completan la ontología cerrada PSP: atom-antonia-medinfo (qué cubre MedInfo y cómo se gestiona), atom-antonia-farmacovigilancia (proceso FV, registro con timestamp, derivación <24h, la autoridad sanitaria la reporta Laboratorio Chile), atom-antonia-journeys (qué contenido preaprobado F0 existe y cuándo usarlo), atom-antonia-titulacion (esquema 0.25 -> 0.5 -> 1 mg SOLO como información del programa, nunca como indicación; fuente disponible en docs/psp-arquitectura-resumen.md del proyecto PSP) y atom-antonia-molecula (semaglutida). CORPUS NO DISPONIBLE: el folleto ISP y el material Medical NO existen en ningún repo local; para atom-antonia-molecula aplicar el fallback de la pill de compliance — redactar solo el marco no-clínico (la molécula es semaglutida como dato del spec PSP, derivación al médico para todo lo demás), provenance pendiente y TODO explícito en el answer; NUNCA rellenar con conocimiento general del LLM. (6) Reindexado del store knowledge/.sldb y verificación de recuperación, incluyendo type.knowledge.gate. OUT — Cualquier cambio en kb_agent/ FUERA de models/knowledge/ (decide_turn, compiler, state_machine, orchestrator quedan intactos); enforcement determinista del ruteo o gate bloqueante post-draft (fase posterior de código que consumirá los GateCriterion vía reader.find("type.knowledge.gate")); tests/knowledge/ (fixture Don Peppe); embeddings offline si el pipeline de indexado no está disponible (dejar frontmatter listo).

## Implementation Path

_Outline the expected implementation route or affected surface._

1. Leer las pills vinculadas (KB-first, modelación, compliance) y los 5 atoms de diseño del desk (mapeo cadena PSP, 4 ramas, policy gate separado, grafo de steps, decisión familia gate). 2. Leer los átomos existentes de knowledge/atoms/ para calcar convenciones de frontmatter, tono y estructura de secciones, y los modelos de kb_agent/models/knowledge/ para calcar la forma de un modelo (usar boundary.py como referencia estructural de GateCriterion). 3. Crear el modelo GateCriterion: gate.py + export + sldb models add + namespace gate:* + validación de import. 4. Redactar los 4 RuleAtom de clasificación. 5. Redactar los 4 ConversationStep nuevos y actualizar allowed_transitions de saludo y registro_estado. 6. Redactar los 5 GateCriterion del policy gate. 7. Redactar los 5 DomainAtom de soporte (medinfo, farmacovigilancia, journeys, titulacion, molecula). 8. Reindexar el store: sldb stores update --store knowledge/.sldb --pythonpath . (registro previo del modelo: sldb models add kb_agent.models.knowledge:GateCriterion --store knowledge/.sldb --pythonpath .). AVISO: knowledge/.sldb/core/store_index.yaml contiene paths absolutos stale de un worktree inexistente (gemini_test-kb); si stores update falla por eso, re-registrar los modelos resuelve. 9. Verificar recuperación con el CLI knowledge (python -m knowledge_base) y el SLDBReader, incluyendo type.knowledge.gate. 10. Conversar contra el runtime real (python -m kb_agent.cli) cubriendo los 4 caminos: consulta operativa, reporte de malestar, pregunta clínica no-EA, duda de tratamiento; verificar además que los átomos gate NO aparecen en el contexto compilado del turno (invisibilidad esperada). REQUIERE credenciales Gemini (.env con GOOGLE_API_KEY o GEMINI_API_KEY); si no hay credenciales en el entorno, este paso se DIFIERE: documentarlo como pendiente en la tarea y cerrar con los checks estáticos — no bloquea el closeout. 11. Registrar en la tarea qué comportamientos quedan garantizados por KB y cuáles requieren la fase de código (ruteo forzado, gate bloqueante que consuma type.knowledge.gate) como insumo del siguiente diseño.

## Validation

_List the checks required before this task can close._

- python -c "from kb_agent.models.knowledge import GateCriterion" (el modelo importa limpio)
- python -c "from kb_agent.ontologizador.sldb_reader import SLDBReader; r=SLDBReader('knowledge'); assert r.find('type.knowledge.step'); assert r.find('type.knowledge.rule'); assert r.find('type.knowledge.gate')"
- pytest tests/unit tests/integration -q (check significativo: 144 passed en baseline; NO usar pytest tests/ a secas — sin credenciales LLM el conftest e2e skippea los 162 y el verde es trivial)
- Verificar que el contexto compilado de un turno NO contiene átomos gate (compilador no itera el tipo gate: invisibilidad esperada)
- Revisión manual de los átomos nuevos contra la pill de compliance (6 puntos)
- Conversación manual por rama con python -m kb_agent.cli documentada en la tarea

## Done When

_Name the observable condition that makes the task complete._

El modelo GateCriterion existe, importa y está registrado en el store; los ~18 átomos nuevos existen en knowledge/atoms/ con frontmatter tipado válido (4 RuleAtom de clasificación, 4 ConversationStep, 5 GateCriterion, 5 DomainAtom); el store reindexado los expone (SLDBReader.find los recupera por type.knowledge.rule / type.knowledge.step / type.knowledge.domain / type.knowledge.gate); el grafo conversation:steps.* no tiene transiciones colgantes; los átomos gate NO aparecen en el contexto compilado del turno; y una conversación de prueba por cada una de las 4 ramas PSP muestra al agente siguiendo la derivación correcta (journey/FV/MedInfo/respuesta validada) sin ninguna modificación del código de turno (decide_turn, compiler, state_machine, orchestrator).
