---
name: grounded_by
direction: directed
cardinality: many_to_many
axis: WHY
source_types:
- ConversationStep
target_types: []
condition: ''
---

# grounded_by

## Description

A document whose content grounds the step's instructions: it enters the turn's bundle whenever the step is active.
