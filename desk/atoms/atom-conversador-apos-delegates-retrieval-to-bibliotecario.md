---
# atom-xxx, unique identifier
id: atom-conversador-apos-delegates-retrieval-to-bibliotecario
# Short, descriptive title
title: conversador_apos delegates retrieval to bibliotecario
# what | why | how | how_not | when | where | for_whom
five_wh_one_plus: what
# e.g., system:deskops, topic:templates
tags:
- system:kb-agent-runtime
- topic:delegation
- layer:runtime
- domain:knowledge-management
# Optional URL or path to the authoritative source of this knowledge
provenance: kb_agent/agent.py
---

# conversador_apos delegates retrieval to bibliotecario

## Answer

_Answer the selected 5WH1+ question as one stable knowledge unit._

The root LlmAgent conversador_apos handles user conversation but delegates every knowledge retrieval request to the bibliotecario sub-agent, which is the only agent configured to call retrieval tools. This preserves a two-step boundary: conversational mediation in the root agent and evidence-grounded lookup in the specialist sub-agent.
