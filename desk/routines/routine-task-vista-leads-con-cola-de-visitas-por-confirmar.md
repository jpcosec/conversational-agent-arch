---
# routine-xxx
id: routine-task-vista-leads-con-cola-de-visitas-por-confirmar
# active | archived
status: active
# Initial node identifier
entrypoint: checklist-task-vista-leads-con-cola-de-visitas-por-confirmar-execution-ready
# Ordered or grouped primitive identifiers
decomposition:
- checklist-task-vista-leads-con-cola-de-visitas-por-confirmar-execution-ready
- operator-task-vista-leads-con-cola-de-visitas-por-confirmar-activate
- checklist-task-vista-leads-con-cola-de-visitas-por-confirmar-testing-ready
- operator-task-vista-leads-con-cola-de-visitas-por-confirmar-ready-for-testing
- checklist-task-vista-leads-con-cola-de-visitas-por-confirmar-closeout-ready
- operator-task-vista-leads-con-cola-de-visitas-por-confirmar-close
# Edge identifiers composing the graph
edges:
- edge-task-vista-leads-con-cola-de-visitas-por-confirmar-execution-to-activate
- edge-task-vista-leads-con-cola-de-visitas-por-confirmar-activate-to-testing
- edge-task-vista-leads-con-cola-de-visitas-por-confirmar-testing-to-ready
- edge-task-vista-leads-con-cola-de-visitas-por-confirmar-ready-to-closeout
- edge-task-vista-leads-con-cola-de-visitas-por-confirmar-closeout-to-close
- edge-task-vista-leads-con-cola-de-visitas-por-confirmar-close-to-complete
# Terminal node identifiers
terminal_nodes:
- complete
# e.g., system:deskops
tags:
- workspace:desk
- primitive:routine
---

# Routine for Vista Leads con cola de visitas por confirmar

## Summary

_Summarize what this routine does and how its nodes fit together._

Actionable routine for Vista Leads con cola de visitas por confirmar.
