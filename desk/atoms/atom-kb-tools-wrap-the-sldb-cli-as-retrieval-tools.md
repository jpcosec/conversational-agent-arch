---
# atom-xxx, unique identifier
id: atom-kb-tools-wrap-the-sldb-cli-as-retrieval-tools
# Short, descriptive title
title: kb_tools wrap the sldb CLI as retrieval tools
# what | why | how | how_not | when | where | for_whom
five_wh_one_plus: what
# e.g., system:deskops, topic:templates
tags:
- system:kb-agent-runtime
- topic:retrieval
- layer:runtime
- domain:knowledge-management
# Optional URL or path to the authoritative source of this knowledge
provenance: kb_agent/kb_tools.py
---

# kb_tools wrap the sldb CLI as retrieval tools

## Answer

_Answer the selected 5WH1+ question as one stable knowledge unit._

The runtime exposes retrieval through Python tools that wrap real sldb CLI commands instead of implementing an independent search engine. list_topics reads the semantic index, search_knowledge runs sldb find, and read_atom runs sldb docs show inside the configured knowledge-base root.
