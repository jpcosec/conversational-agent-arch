---
id: task-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa
status: deferred
summary: ''
tags:
- workspace:desk
- artifact:task
- source:inbox
routine: ''
current_node: ''
history: []
references: []
depends_on: []
pills: []
files: []
checklists: []
task_type: ''
inherits_from: []
inherit_acceptance_context: false
atoms: []
---

# Una KB sin embeddings falla en silencio y nadie avisa

ID: task-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa
Status: deferred
Priority: medium

## Goal

Triage and resolve the inbox message promoted from `desk/inbox/20260827-184451-suggestion-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa.md`.

## Scope

Goal: que una KB sin vectores sea un error visible y no una degradacion muda del retrieval.
Scope: gap generico, aplica a cualquier KB. knowledge_base/operations.py:631-633 (_semantic_search) y kb_agent/ontologizador/compiler.py:345-346 (_semantic_candidates) hacen 'if not emb: continue' sin log ni excepcion: un atom sin vector desaparece del retrieval sin dejar rastro. Con la KB entera sin vectores el sistema sigue respondiendo por fuzzy matching literal, asi que el defecto es invisible desde afuera -- fue exactamente lo que paso con knowledge_vitali (50/50 atoms con embedding null; ver el commit que lo arreglo). Falta una guarda: chequeo de arranque o en el job static de CI que cuente atoms sin vector por KB y falle o advierta, mas un WARN la primera vez que _semantic_search descarta todo. Ojo con el falso positivo: los atoms agent-*-router y agent-*-gate no llevan vector por diseno (misma paridad en knowledge/ y knowledge_vitali/).
Validation: test que carga una KB con embeddings nulos y afirma que la guarda avisa; extension del job static de CI.

## Source

- `desk/inbox/20260827-184451-suggestion-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa.md`

## Done When

- The message is resolved, answered, or promoted into active work.
