---
# routine-xxx
id: routine-task-metricas-reales-en-el-dashboard-desde-el-sqlite
# active | archived
status: active
# Initial node identifier
entrypoint: checklist-task-metricas-reales-en-el-dashboard-desde-el-sqlite-execution-ready
# Ordered or grouped primitive identifiers
decomposition:
- checklist-task-metricas-reales-en-el-dashboard-desde-el-sqlite-execution-ready
- operator-task-metricas-reales-en-el-dashboard-desde-el-sqlite-activate
- checklist-task-metricas-reales-en-el-dashboard-desde-el-sqlite-testing-ready
- operator-task-metricas-reales-en-el-dashboard-desde-el-sqlite-ready-for-testing
- checklist-task-metricas-reales-en-el-dashboard-desde-el-sqlite-closeout-ready
- operator-task-metricas-reales-en-el-dashboard-desde-el-sqlite-close
# Edge identifiers composing the graph
edges:
- edge-task-metricas-reales-en-el-dashboard-desde-el-sqlite-execution-to-activate
- edge-task-metricas-reales-en-el-dashboard-desde-el-sqlite-activate-to-testing
- edge-task-metricas-reales-en-el-dashboard-desde-el-sqlite-testing-to-ready
- edge-task-metricas-reales-en-el-dashboard-desde-el-sqlite-ready-to-closeout
- edge-task-metricas-reales-en-el-dashboard-desde-el-sqlite-closeout-to-close
- edge-task-metricas-reales-en-el-dashboard-desde-el-sqlite-close-to-complete
# Terminal node identifiers
terminal_nodes:
- complete
# e.g., system:deskops
tags:
- workspace:desk
- primitive:routine
---

# Routine for Metricas reales en el dashboard desde el sqlite

## Summary

_Summarize what this routine does and how its nodes fit together._

Actionable routine for Metricas reales en el dashboard desde el sqlite.
