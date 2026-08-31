---
# routine-xxx
id: routine-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios
# active | archived
status: active
# Initial node identifier
entrypoint: checklist-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios-execution-ready
# Ordered or grouped primitive identifiers
decomposition:
- checklist-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios-execution-ready
- operator-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios-activate
- checklist-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios-testing-ready
- operator-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios-ready-for-testing
- checklist-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios-closeout-ready
- operator-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios-close
# Edge identifiers composing the graph
edges:
- edge-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios-execution-to-activate
- edge-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios-activate-to-testing
- edge-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios-testing-to-ready
- edge-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios-ready-to-closeout
- edge-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios-closeout-to-close
- edge-task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios-close-to-complete
# Terminal node identifiers
terminal_nodes:
- complete
# e.g., system:deskops
tags:
- workspace:desk
- primitive:routine
---

# Routine for Identidad no unificada entre canales: el mismo usuario es dos usuarios

## Summary

_Summarize what this routine does and how its nodes fit together._

Actionable routine for Identidad no unificada entre canales: el mismo usuario es dos usuarios.
