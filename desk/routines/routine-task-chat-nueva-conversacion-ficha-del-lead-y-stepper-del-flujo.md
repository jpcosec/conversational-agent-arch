---
# routine-xxx
id: routine-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo
# active | archived
status: active
# Initial node identifier
entrypoint: checklist-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-execution-ready
# Ordered or grouped primitive identifiers
decomposition:
- checklist-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-execution-ready
- operator-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-activate
- checklist-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-testing-ready
- operator-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-ready-for-testing
- checklist-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-closeout-ready
- operator-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-close
# Edge identifiers composing the graph
edges:
- edge-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-execution-to-activate
- edge-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-activate-to-testing
- edge-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-testing-to-ready
- edge-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-ready-to-closeout
- edge-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-closeout-to-close
- edge-task-chat-nueva-conversacion-ficha-del-lead-y-stepper-del-flujo-close-to-complete
# Terminal node identifiers
terminal_nodes:
- complete
# e.g., system:deskops
tags:
- workspace:desk
- primitive:routine
---

# Routine for Chat: nueva conversacion, ficha del lead y stepper del flujo

## Summary

_Summarize what this routine does and how its nodes fit together._

Actionable routine for Chat: nueva conversacion, ficha del lead y stepper del flujo.
