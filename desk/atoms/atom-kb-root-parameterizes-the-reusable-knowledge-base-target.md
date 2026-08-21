---
# atom-xxx, unique identifier
id: atom-kb-root-parameterizes-the-reusable-knowledge-base-target
# Short, descriptive title
title: KB_ROOT parameterizes the reusable knowledge-base target
# what | why | how | how_not | when | where | for_whom
five_wh_one_plus: what
# e.g., system:deskops, topic:templates
tags:
- system:kb-agent-runtime
- topic:configuration
- layer:runtime
- domain:knowledge-management
# Optional URL or path to the authoritative source of this knowledge
provenance: kb_agent/kb_tools.py
---

# KB_ROOT parameterizes the reusable knowledge-base target

## Answer

_Answer the selected 5WH1+ question as one stable knowledge unit._

The retrieval runtime is reusable because the sldb execution target is centralized in KB_ROOT and STORE within kb_tools.py. Changing that root repoints the same agent runtime toward a different SLDB-backed knowledge base without changing the agent delegation pattern or tool surface.
