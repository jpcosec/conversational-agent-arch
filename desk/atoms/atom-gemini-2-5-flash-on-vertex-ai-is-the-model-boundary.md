---
# atom-xxx, unique identifier
id: atom-gemini-2-5-flash-on-vertex-ai-is-the-model-boundary
# Short, descriptive title
title: Gemini 2.5 Flash on Vertex AI is the model boundary
# what | why | how | how_not | when | where | for_whom
five_wh_one_plus: what
# e.g., system:deskops, topic:templates
tags:
- system:kb-agent-runtime
- topic:llm-boundary
- layer:runtime
- domain:knowledge-management
# Optional URL or path to the authoritative source of this knowledge
provenance: kb_agent/agent.py
---

# Gemini 2.5 Flash on Vertex AI is the model boundary

## Answer

_Answer the selected 5WH1+ question as one stable knowledge unit._

Both conversador_apos and bibliotecario are configured as Google ADK LlmAgent instances that use gemini-2.5-flash. The runtime therefore depends on Vertex AI as its model-serving boundary while keeping retrieval logic and knowledge storage outside the model provider.
