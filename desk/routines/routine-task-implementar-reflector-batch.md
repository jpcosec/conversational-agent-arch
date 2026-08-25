---
# routine-xxx
id: routine-task-implementar-reflector-batch
# active | archived
status: active
# Initial node identifier
entrypoint: checklist-task-implementar-reflector-batch-execution-ready
# Ordered or grouped primitive identifiers
decomposition:
- checklist-task-implementar-reflector-batch-execution-ready
- operator-task-implementar-reflector-batch-activate
- checklist-task-implementar-reflector-batch-testing-ready
- operator-task-implementar-reflector-batch-ready-for-testing
- checklist-task-implementar-reflector-batch-closeout-ready
- operator-task-implementar-reflector-batch-close
# Edge identifiers composing the graph
edges:
- edge-task-implementar-reflector-batch-execution-to-activate
- edge-task-implementar-reflector-batch-activate-to-testing
- edge-task-implementar-reflector-batch-testing-to-ready
- edge-task-implementar-reflector-batch-ready-to-closeout
- edge-task-implementar-reflector-batch-closeout-to-close
- edge-task-implementar-reflector-batch-close-to-complete
# Terminal node identifiers
terminal_nodes:
- complete
# e.g., system:deskops
tags:
- workspace:desk
- primitive:routine
---

# Routine for Implementar Reflector Batch

## Summary

_Summarize what this routine does and how its nodes fit together._

Actionable routine for Implementar Reflector Batch.
