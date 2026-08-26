---
# routine-xxx
id: routine-task-organizaci-n-autom-tica-de-tomos-en-la-kb
# active | archived
status: active
# Initial node identifier
entrypoint: checklist-task-organizaci-n-autom-tica-de-tomos-en-la-kb-execution-ready
# Ordered or grouped primitive identifiers
decomposition:
- checklist-task-organizaci-n-autom-tica-de-tomos-en-la-kb-execution-ready
- operator-task-organizaci-n-autom-tica-de-tomos-en-la-kb-activate
- checklist-task-organizaci-n-autom-tica-de-tomos-en-la-kb-testing-ready
- operator-task-organizaci-n-autom-tica-de-tomos-en-la-kb-ready-for-testing
- checklist-task-organizaci-n-autom-tica-de-tomos-en-la-kb-closeout-ready
- operator-task-organizaci-n-autom-tica-de-tomos-en-la-kb-close
# Edge identifiers composing the graph
edges:
- edge-task-organizaci-n-autom-tica-de-tomos-en-la-kb-execution-to-activate
- edge-task-organizaci-n-autom-tica-de-tomos-en-la-kb-activate-to-testing
- edge-task-organizaci-n-autom-tica-de-tomos-en-la-kb-testing-to-ready
- edge-task-organizaci-n-autom-tica-de-tomos-en-la-kb-ready-to-closeout
- edge-task-organizaci-n-autom-tica-de-tomos-en-la-kb-closeout-to-close
- edge-task-organizaci-n-autom-tica-de-tomos-en-la-kb-close-to-complete
# Terminal node identifiers
terminal_nodes:
- complete
# e.g., system:deskops
tags:
- workspace:desk
- primitive:routine
---

# Routine for Organización automática de átomos en la KB

## Summary

_Summarize what this routine does and how its nodes fit together._

Actionable routine for Organización automática de átomos en la KB.
