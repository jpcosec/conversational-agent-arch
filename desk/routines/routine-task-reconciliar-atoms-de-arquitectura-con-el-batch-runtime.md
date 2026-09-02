---
# routine-xxx
id: routine-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime
# active | archived
status: active
# Initial node identifier
entrypoint: checklist-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime-execution-ready
# Ordered or grouped primitive identifiers
decomposition:
- checklist-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime-execution-ready
- operator-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime-activate
- checklist-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime-testing-ready
- operator-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime-ready-for-testing
- checklist-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime-closeout-ready
- operator-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime-close
# Edge identifiers composing the graph
edges:
- edge-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime-execution-to-activate
- edge-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime-activate-to-testing
- edge-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime-testing-to-ready
- edge-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime-ready-to-closeout
- edge-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime-closeout-to-close
- edge-task-reconciliar-atoms-de-arquitectura-con-el-batch-runtime-close-to-complete
# Terminal node identifiers
terminal_nodes:
- complete
# e.g., system:deskops
tags:
- workspace:desk
- primitive:routine
---

# Routine for Reconciliar atoms de arquitectura con el batch runtime

## Summary

_Summarize what this routine does and how its nodes fit together._

Actionable routine for Reconciliar atoms de arquitectura con el batch runtime.
