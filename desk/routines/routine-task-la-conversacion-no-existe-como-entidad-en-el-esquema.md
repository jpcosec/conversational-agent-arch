---
# routine-xxx
id: routine-task-la-conversacion-no-existe-como-entidad-en-el-esquema
# active | archived
status: active
# Initial node identifier
entrypoint: checklist-task-la-conversacion-no-existe-como-entidad-en-el-esquema-execution-ready
# Ordered or grouped primitive identifiers
decomposition:
- checklist-task-la-conversacion-no-existe-como-entidad-en-el-esquema-execution-ready
- operator-task-la-conversacion-no-existe-como-entidad-en-el-esquema-activate
- checklist-task-la-conversacion-no-existe-como-entidad-en-el-esquema-testing-ready
- operator-task-la-conversacion-no-existe-como-entidad-en-el-esquema-ready-for-testing
- checklist-task-la-conversacion-no-existe-como-entidad-en-el-esquema-closeout-ready
- operator-task-la-conversacion-no-existe-como-entidad-en-el-esquema-close
# Edge identifiers composing the graph
edges:
- edge-task-la-conversacion-no-existe-como-entidad-en-el-esquema-execution-to-activate
- edge-task-la-conversacion-no-existe-como-entidad-en-el-esquema-activate-to-testing
- edge-task-la-conversacion-no-existe-como-entidad-en-el-esquema-testing-to-ready
- edge-task-la-conversacion-no-existe-como-entidad-en-el-esquema-ready-to-closeout
- edge-task-la-conversacion-no-existe-como-entidad-en-el-esquema-closeout-to-close
- edge-task-la-conversacion-no-existe-como-entidad-en-el-esquema-close-to-complete
# Terminal node identifiers
terminal_nodes:
- complete
# e.g., system:deskops
tags:
- workspace:desk
- primitive:routine
---

# Routine for La conversacion no existe como entidad en el esquema

## Summary

_Summarize what this routine does and how its nodes fit together._

Actionable routine for La conversacion no existe como entidad en el esquema.
