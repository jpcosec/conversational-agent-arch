---
# routine-xxx
id: routine-task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica
# active | archived
status: active
# Initial node identifier
entrypoint: checklist-task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica-execution-ready
# Ordered or grouped primitive identifiers
decomposition:
- checklist-task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica-execution-ready
- operator-task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica-activate
- checklist-task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica-testing-ready
- operator-task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica-ready-for-testing
- checklist-task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica-closeout-ready
- operator-task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica-close
# Edge identifiers composing the graph
edges:
- edge-task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica-execution-to-activate
- edge-task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica-activate-to-testing
- edge-task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica-testing-to-ready
- edge-task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica-ready-to-closeout
- edge-task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica-closeout-to-close
- edge-task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica-close-to-complete
# Terminal node identifiers
terminal_nodes:
- complete
# e.g., system:deskops
tags:
- workspace:desk
- primitive:routine
---

# Routine for Perfilador: pre-filtrar traits candidatos por similitud semantica

## Summary

_Summarize what this routine does and how its nodes fit together._

Actionable routine for Perfilador: pre-filtrar traits candidatos por similitud semantica.
