---
name: transitions_to
direction: directed
cardinality: many_to_many
axis: WHEN
source_types:
- ConversationStep
target_types:
- ConversationStep
condition: ''
---

# transitions_to

## Description

Allowed move from one conversation step to another. The orchestrator may only navigate along these edges.