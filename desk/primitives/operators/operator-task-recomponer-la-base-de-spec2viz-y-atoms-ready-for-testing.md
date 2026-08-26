---
# operator-xxx
id: operator-task-recomponer-la-base-de-spec2viz-y-atoms-ready-for-testing
# active | archived
status: active
# Atomic runtime action, e.g., set_field, append_list
action: set_field
# Payload path modified by the operator
target: status
# Value used by the operator action
value: ready_for_testing
# e.g., system:deskops
tags:
- primitive:operator
---

# Mark ready for testing

## Summary

_Summarize the state transition this operator performs._

Moves the task into the testing gate.
