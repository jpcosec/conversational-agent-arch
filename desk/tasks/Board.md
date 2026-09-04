---
# board-xxx
id: board-001
# Affected workspace or domain
scope: desk
# List of task-xxx paths
tasks:
- desk/tasks/task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp.md
- desk/tasks/task-verificar-si-el-known-gap-donpeppe-saludo-unico-sigue-vigente.md
- desk/tasks/task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime.md
- desk/tasks/task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo.md
- desk/tasks/task-vista-leads-con-cola-de-visitas-por-confirmar.md
- desk/tasks/task-metricas-reales-en-el-dashboard-desde-el-sqlite.md
- desk/tasks/task-chat-de-producto-sin-inspector-para-el-equipo-de-vitali.md
# List of pill-xxx paths
pills:
- desk/contexts/pills.md
# List of ritual-xxx paths
rituals:
- desk/rituals/phase.md
- desk/rituals/execution.md
- desk/rituals/testing.md
- desk/rituals/closeout.md
# e.g., system:sldb, workspace:desk
tags:
- workspace:desk
---

# gemini_test Board

## Purpose

_Explain what this board routes and why it exists._

Enrutar el trabajo activo del repo y mantener visibles sus gates de ejecución, testing, closeout y fase.

## Notes

_Add short operational notes about the current routed set._

Fase runtime-vitali cerrada (2026-09-01), 10 tasks con evidencia en commits 20eb34b, 16f39fa y e04e1f0; suite offline 269 verde, UI y alembic OK. Falta la validacion integrada LLM (capa e2e), routed en task-verificar-known-gap. PSP Antonia sigue en ready_for_testing, exige conversacion real (capa LLM con .env Vertex). task-reconciliar-atoms actualiza las verdades de arquitectura que el batch cambio, solo desk/atoms y docs, sin tocar KBs. Drawer conserva reconstruir-kb-vitali (decision del owner), modo-editor (diferido) y evento-adverso (candidata capa KB). Rama vitali adelantada a origin, push pendiente.

## Task Details

_Generated from the task references above._

- Extender el flujo conversacional de la KB Antonia para cumplir la cadena de agentes PSP [ready_for_testing] - La KB de Antonia (knowledge/atoms/) modela completo el flujo de atención PSP: las 4 ramas de clasificación como RuleAtom, los steps faltantes del grafo conversacional (derivación MedInfo, revisión humana, journey operativo F0, autovalidación policy gate) como ConversationStep con transiciones coherentes, los criterios regulatorios del policy gate como átomos GateCriterion de la nueva familia gate (modelo nuevo, invisible al runtime actual), y los domain atoms de soporte (MedInfo, proceso FV, journeys, titulación, molécula) que completan la ontología cerrada PSP — todo indexado en el store SLDB y verificable por conversación real contra el runtime sin ninguna modificación del código de turno (decide_turn, compiler, state_machine, orchestrator).
- Verificar si el known_gap donpeppe_saludo_unico sigue vigente [active] - Correr la capa e2e (smoke + simulaciones con juez) sobre el runtime post-batch (20eb34b + 16f39fa) y emitir veredicto del known_gap donpeppe_saludo_unico - si la entidad Conversation lo arreglo, retirar el xfail estricto de tests/e2e/simulation/scenarios.py; si sigue vigente, documentar por que y dejarlo. Esta corrida es ademas la validacion integrada de la fase runtime-vitali.
- Reconciliar atoms de arquitectura con el batch runtime [draft] - Actualizar atom-concepto-turno-extendido (turn_id uuid unico), atom-persistencia-sql (Conversation + TurnKind + identity_key phone), atom-orquestador-hub (_resolve_conversation, carreras ensure_user), atom-perfilador-asincrono (pre-filtro top-k + ingestion form + precedencia form sobre perfilador), atom-sldb-knowledge-base (audit embeddings) y renombrar/reescribir atom-ontologizador-context-compiler a knowledge; despues rematerializar docs.
- Chat: nueva conversacion, ficha del lead y stepper del flujo [draft] - En frontends/chat: boton 'Nueva conversacion' que rota la sesion; ficha del lead (para quien busca, proyecto de interes, dia y bloque preferido, modalidad, email, telefono) derivada de traits y slots del ultimo turno; stepper del flujo (saludo, calificacion, agendar, datos, cierre) con el paso activo resaltado, leido de /api/flow; badges tecnicos del timeline reemplazados por el nombre humano del paso.
- Vista Leads con cola de visitas por confirmar [draft] - Reemplazar /users por una vista Leads: lista de conversaciones con estado de negocio (nuevo, calificado, con preferencia de visita, datos completos), ficha del lead y cola 'visitas por confirmar' con dia/bloque, modalidad, email y telefono; click abre la conversacion.
- Metricas reales en el dashboard desde el sqlite [draft] - Endpoint /api/metrics y dashboard con conversaciones por dia, porcentaje de turnos en fallback, porcentaje derivados por el gate, leads con datos de contacto, latencia media por turno; chip 'Datos de ejemplo' eliminado.
- Chat de producto sin inspector para el equipo de Vitali [draft] - Ruta /chat con solo la conversacion: brand del negocio, sin inspector ni badges, boton Nueva conversacion, formulario inicial opcional de nombre y telefono que fija external_id por telefono (identity_key phone), diseño movil primero, indicador de escribiendo. Navegacion en tres grupos: Chat, Operacion (Leads, Metricas), Desarrollo (Inspector, Flow, Mindmap), etiquetas en espanol desde el yaml.
