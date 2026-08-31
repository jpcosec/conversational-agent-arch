---
# routine-xxx
id: routine-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid
# active | archived
status: active
# Initial node identifier
entrypoint: checklist-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid-execution-ready
# Ordered or grouped primitive identifiers
decomposition:
- checklist-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid-execution-ready
- operator-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid-activate
- checklist-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid-testing-ready
- operator-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid-ready-for-testing
- checklist-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid-closeout-ready
- operator-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid-close
# Edge identifiers composing the graph
edges:
- edge-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid-execution-to-activate
- edge-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid-activate-to-testing
- edge-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid-testing-to-ready
- edge-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid-ready-to-closeout
- edge-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid-closeout-to-close
- edge-task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid-close-to-complete
# Terminal node identifiers
terminal_nodes:
- complete
# e.g., system:deskops
tags:
- workspace:desk
- primitive:routine
---

# Routine for El turn_id en vivo (tN) no coincide con el persistido (uuid)

## Summary

_Summarize what this routine does and how its nodes fit together._

Actionable routine for El turn_id en vivo (tN) no coincide con el persistido (uuid).
