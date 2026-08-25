---
# routine-xxx
id: routine-task-persistencia-en-disco-entre-sesiones
# active | archived
status: active
# Initial node identifier
entrypoint: checklist-task-persistencia-en-disco-entre-sesiones-execution-ready
# Ordered or grouped primitive identifiers
decomposition:
- checklist-task-persistencia-en-disco-entre-sesiones-execution-ready
- operator-task-persistencia-en-disco-entre-sesiones-activate
- checklist-task-persistencia-en-disco-entre-sesiones-testing-ready
- operator-task-persistencia-en-disco-entre-sesiones-ready-for-testing
- checklist-task-persistencia-en-disco-entre-sesiones-closeout-ready
- operator-task-persistencia-en-disco-entre-sesiones-close
# Edge identifiers composing the graph
edges:
- edge-task-persistencia-en-disco-entre-sesiones-execution-to-activate
- edge-task-persistencia-en-disco-entre-sesiones-activate-to-testing
- edge-task-persistencia-en-disco-entre-sesiones-testing-to-ready
- edge-task-persistencia-en-disco-entre-sesiones-ready-to-closeout
- edge-task-persistencia-en-disco-entre-sesiones-closeout-to-close
- edge-task-persistencia-en-disco-entre-sesiones-close-to-complete
# Terminal node identifiers
terminal_nodes:
- complete
# e.g., system:deskops
tags:
- workspace:desk
- primitive:routine
---

# Routine for Persistencia en Disco entre Sesiones

## Summary

_Summarize what this routine does and how its nodes fit together._

Actionable routine for Persistencia en Disco entre Sesiones.
