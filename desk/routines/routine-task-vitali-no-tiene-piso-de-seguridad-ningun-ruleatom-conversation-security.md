---
# routine-xxx
id: routine-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security
# active | archived
status: active
# Initial node identifier
entrypoint: checklist-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-execution-ready
# Ordered or grouped primitive identifiers
decomposition:
- checklist-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-execution-ready
- operator-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-activate
- checklist-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-testing-ready
- operator-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-ready-for-testing
- checklist-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-closeout-ready
- operator-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-close
# Edge identifiers composing the graph
edges:
- edge-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-execution-to-activate
- edge-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-activate-to-testing
- edge-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-testing-to-ready
- edge-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-ready-to-closeout
- edge-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-closeout-to-close
- edge-task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security-close-to-complete
# Terminal node identifiers
terminal_nodes:
- complete
# e.g., system:deskops
tags:
- workspace:desk
- primitive:routine
---

# Routine for Vitali no tiene piso de seguridad: ningun RuleAtom conversation:security

## Summary

_Summarize what this routine does and how its nodes fit together._

Actionable routine for Vitali no tiene piso de seguridad: ningun RuleAtom conversation:security.
