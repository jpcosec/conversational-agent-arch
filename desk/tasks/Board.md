---
# board-xxx
id: board-001
# Affected workspace or domain
scope: desk
# List of task-xxx paths
tasks:
- desk/tasks/task-organizaci-n-autom-tica-de-tomos-en-la-kb.md
- desk/tasks/task-recomponer-la-base-de-spec2viz-y-atoms.md
- desk/tasks/task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp.md
# List of pill-xxx paths
pills:
- desk/contexts/pills.md
# List of ritual-xxx paths
rituals:
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



## Notes

_Add short operational notes about the current routed set._

- Organización automática de átomos en la KB [complete] - cerrada; el handoff del drawer fue consumido.
- Recomponer la base de spec2viz y atoms [complete] - cerrada; el seed del drawer fue consumido.
- Extender el flujo conversacional de la KB Antonia para cumplir la cadena de agentes PSP [ready_for_testing] - unica task abierta del board.
- task-ui-foundations [complete] - obsoleta (rutas viejas/redirects ya shipeados o borrados); no se rutea.

## Task Details

_Generated from the task references above._

- Organización automática de átomos en la KB [complete] - Promote deferred work from handoff-knowledge-org.md.
- Recomponer la base de spec2viz y atoms [complete] - Promote deferred work from seed-recomponer-spec2viz-y-atoms.md.
- Extender el flujo conversacional de la KB Antonia para cumplir la cadena de agentes PSP [ready_for_testing] - La KB de Antonia (knowledge/atoms/) modela completo el flujo de atención PSP: las 4 ramas de clasificación como RuleAtom, los steps faltantes del grafo conversacional (derivación MedInfo, revisión humana, journey operativo F0, autovalidación policy gate) como ConversationStep con transiciones coherentes, los criterios regulatorios del policy gate como átomos GateCriterion de la nueva familia gate (modelo nuevo, invisible al runtime actual), y los domain atoms de soporte (MedInfo, proceso FV, journeys, titulación, molécula) que completan la ontología cerrada PSP — todo indexado en el store SLDB y verificable por conversación real contra el runtime sin ninguna modificación del código de turno (decide_turn, compiler, state_machine, orchestrator).
