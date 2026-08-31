---
# routine-xxx
id: routine-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara
# active | archived
status: active
# Initial node identifier
entrypoint: checklist-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara-execution-ready
# Ordered or grouped primitive identifiers
decomposition:
- checklist-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara-execution-ready
- operator-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara-activate
- checklist-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara-testing-ready
- operator-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara-ready-for-testing
- checklist-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara-closeout-ready
- operator-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara-close
# Edge identifiers composing the graph
edges:
- edge-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara-execution-to-activate
- edge-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara-activate-to-testing
- edge-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara-testing-to-ready
- edge-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara-ready-to-closeout
- edge-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara-closeout-to-close
- edge-task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara-close-to-complete
# Terminal node identifiers
terminal_nodes:
- complete
# e.g., system:deskops
tags:
- workspace:desk
- primitive:routine
---

# Routine for Grounding: el conversador afirma atributos de productos que la KB no declara

## Summary

_Summarize what this routine does and how its nodes fit together._

Actionable routine for Grounding: el conversador afirma atributos de productos que la KB no declara.
