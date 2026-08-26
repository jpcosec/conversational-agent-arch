---
id: atom-capa-frontend-del-runtime
title: Capa Frontend del Runtime
five_wh_one_plus: what
tags:
- domain:self.architecture.frontend
- layer:frontend
- system:kb-agent
- topic:ui
provenance: null
---

# Capa Frontend del Runtime

## Answer

Tres UIs HTML/JS estáticas (sin build) servidas por un único FastAPI en frontends/chat/server.py: chat con inspector de mesa (frontends/chat, consume /api/chat y /api/atom), editor de flujo conversacional (frontends/flow_editor, consume /api/flow y renderiza el grafo de ConversationStep con React Flow) y visor de perfilado (frontends/profiling, consume /api/profiles cruzando UserTraits SQL con TraitAtom SLDB). El backend expone además /api/health.
