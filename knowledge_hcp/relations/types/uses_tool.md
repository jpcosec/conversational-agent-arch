---
name: uses_tool
direction: directed
cardinality: many_to_one
axis: HOW
source_types:
- ConversationStep
target_types:
- ToolAtom
condition: ''
---

# uses_tool

## Description

The tool a llamado_tool step executes.