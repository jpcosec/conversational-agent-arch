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

- Organización automática de átomos en la KB [active] - Promote deferred work from handoff-knowledge-org.md.
- Recomponer la base de spec2viz y atoms [active] - Promote deferred work from seed-recomponer-spec2viz-y-atoms.md.

## Task Details

_Generated from the task references above._

- Organización automática de átomos en la KB [ready_for_testing] - Promote deferred work from handoff-knowledge-org.md.
- Recomponer la base de spec2viz y atoms [active] - Promote deferred work from seed-recomponer-spec2viz-y-atoms.md.
- Extender el flujo conversacional de la KB Antonia para cumplir la cadena de agentes PSP [draft] - La KB de Antonia (knowledge/atoms/) modela completo el flujo de atención PSP: las 4 ramas de clasificación como RuleAtom, los steps faltantes del grafo conversacional (derivación MedInfo, revisión humana, journey operativo F0, autovalidación policy gate) como ConversationStep con transiciones coherentes, los criterios regulatorios del policy gate como RuleAtom propios, y los domain atoms de soporte (qué es MedInfo, proceso FV, contenido de journeys) — todo indexado en el store SLDB y verificable por conversación real contra el runtime sin ninguna modificación de kb_agent/.
