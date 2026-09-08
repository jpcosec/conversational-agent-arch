---
# routine-xxx
id: routine-task-mover-logica-reimplementada-a-kgdb-sldb-pron
# active | archived
status: active
# Initial node identifier
entrypoint: checklist-task-mover-logica-reimplementada-a-kgdb-sldb-pron-execution-ready
# Ordered or grouped primitive identifiers
decomposition:
- checklist-task-mover-logica-reimplementada-a-kgdb-sldb-pron-execution-ready
- operator-task-mover-logica-reimplementada-a-kgdb-sldb-pron-activate
- checklist-task-mover-logica-reimplementada-a-kgdb-sldb-pron-testing-ready
- operator-task-mover-logica-reimplementada-a-kgdb-sldb-pron-ready-for-testing
- checklist-task-mover-logica-reimplementada-a-kgdb-sldb-pron-closeout-ready
- operator-task-mover-logica-reimplementada-a-kgdb-sldb-pron-close
# Edge identifiers composing the graph
edges:
- edge-task-mover-logica-reimplementada-a-kgdb-sldb-pron-execution-to-activate
- edge-task-mover-logica-reimplementada-a-kgdb-sldb-pron-activate-to-testing
- edge-task-mover-logica-reimplementada-a-kgdb-sldb-pron-testing-to-ready
- edge-task-mover-logica-reimplementada-a-kgdb-sldb-pron-ready-to-closeout
- edge-task-mover-logica-reimplementada-a-kgdb-sldb-pron-closeout-to-close
- edge-task-mover-logica-reimplementada-a-kgdb-sldb-pron-close-to-complete
# Terminal node identifiers
terminal_nodes:
- complete
# e.g., system:deskops
tags:
- workspace:desk
- primitive:routine
---

# Routine for Mover logica reimplementada a kgdb/sldb/pron

## Summary

_Summarize what this routine does and how its nodes fit together._

Actionable routine for Mover logica reimplementada a kgdb/sldb/pron.
