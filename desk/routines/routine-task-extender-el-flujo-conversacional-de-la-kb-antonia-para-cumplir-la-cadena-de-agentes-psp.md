---
# routine-xxx
id: routine-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp
# active | archived
status: active
# Initial node identifier
entrypoint: checklist-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-execution-ready
# Ordered or grouped primitive identifiers
decomposition:
- checklist-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-execution-ready
- operator-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-activate
- checklist-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-testing-ready
- operator-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-ready-for-testing
- checklist-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-closeout-ready
- operator-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-close
# Edge identifiers composing the graph
edges:
- edge-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-execution-to-activate
- edge-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-activate-to-testing
- edge-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-testing-to-ready
- edge-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-ready-to-closeout
- edge-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-closeout-to-close
- edge-task-extender-el-flujo-conversacional-de-la-kb-antonia-para-cumplir-la-cadena-de-agentes-psp-close-to-complete
# Terminal node identifiers
terminal_nodes:
- complete
# e.g., system:deskops
tags:
- workspace:desk
- primitive:routine
---

# Routine for Extender el flujo conversacional de la KB Antonia para cumplir la cadena de agentes PSP

## Summary

_Summarize what this routine does and how its nodes fit together._

Actionable routine for Extender el flujo conversacional de la KB Antonia para cumplir la cadena de agentes PSP.
