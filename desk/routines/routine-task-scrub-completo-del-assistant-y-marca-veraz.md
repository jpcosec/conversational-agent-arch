---
# routine-xxx
id: routine-task-scrub-completo-del-assistant-y-marca-veraz
# active | archived
status: active
# Initial node identifier
entrypoint: checklist-task-scrub-completo-del-assistant-y-marca-veraz-execution-ready
# Ordered or grouped primitive identifiers
decomposition:
- checklist-task-scrub-completo-del-assistant-y-marca-veraz-execution-ready
- operator-task-scrub-completo-del-assistant-y-marca-veraz-activate
- checklist-task-scrub-completo-del-assistant-y-marca-veraz-testing-ready
- operator-task-scrub-completo-del-assistant-y-marca-veraz-ready-for-testing
- checklist-task-scrub-completo-del-assistant-y-marca-veraz-closeout-ready
- operator-task-scrub-completo-del-assistant-y-marca-veraz-close
# Edge identifiers composing the graph
edges:
- edge-task-scrub-completo-del-assistant-y-marca-veraz-execution-to-activate
- edge-task-scrub-completo-del-assistant-y-marca-veraz-activate-to-testing
- edge-task-scrub-completo-del-assistant-y-marca-veraz-testing-to-ready
- edge-task-scrub-completo-del-assistant-y-marca-veraz-ready-to-closeout
- edge-task-scrub-completo-del-assistant-y-marca-veraz-closeout-to-close
- edge-task-scrub-completo-del-assistant-y-marca-veraz-close-to-complete
# Terminal node identifiers
terminal_nodes:
- complete
# e.g., system:deskops
tags:
- workspace:desk
- primitive:routine
---

# Routine for Scrub Completo del Assistant y Marca Veraz

## Summary

_Summarize what this routine does and how its nodes fit together._

Actionable routine for Scrub Completo del Assistant y Marca Veraz.
