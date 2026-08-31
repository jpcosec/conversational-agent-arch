---
# board-xxx
id: board-001
# Affected workspace or domain
scope: desk
# List of task-xxx paths
tasks:
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

- Extender el flujo conversacional de la KB Antonia para cumplir la cadena de agentes PSP [ready_for_testing] - única task abierta del board.

## Task Details

_Generated from the task references above._

- Extender el flujo conversacional de la KB Antonia para cumplir la cadena de agentes PSP [ready_for_testing] - La KB de Antonia (knowledge/atoms/) modela completo el flujo de atención PSP: las 4 ramas de clasificación como RuleAtom, los steps faltantes del grafo conversacional (derivación MedInfo, revisión humana, journey operativo F0, autovalidación policy gate) como ConversationStep con transiciones coherentes, los criterios regulatorios del policy gate como átomos GateCriterion de la nueva familia gate (modelo nuevo, invisible al runtime actual), y los domain atoms de soporte (MedInfo, proceso FV, journeys, titulación, molécula) que completan la ontología cerrada PSP — todo indexado en el store SLDB y verificable por conversación real contra el runtime sin ninguna modificación del código de turno (decide_turn, compiler, state_machine, orchestrator).
