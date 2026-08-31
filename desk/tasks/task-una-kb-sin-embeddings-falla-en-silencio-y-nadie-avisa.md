---
id: task-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa
status: active
summary: ''
tags:
- workspace:desk
- artifact:task
- source:drawer
routine: routine-task-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa
current_node: checklist-task-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa-execution-ready
history: []
references:
- desk/drawer/tasks/task-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa.md
depends_on: []
pills: []
files: []
checklists:
- checklist-task-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa-execution-ready
- checklist-task-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa-testing-ready
- checklist-task-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa-closeout-ready
task_type: ''
inherits_from: []
inherit_acceptance_context: false
atoms: []
---

# Una KB sin embeddings falla en silencio y nadie avisa

## Rationale

_Explain why this task exists or the business driver behind it._

Not provided.

## Goal

_Describe the concrete result this task must produce._

Triage and resolve the inbox message promoted from `desk/inbox/20260827-184451-suggestion-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa.md`.

## Scope

_State what is in scope and what is out of scope._

Goal: que una KB sin vectores sea un error visible y no una degradacion muda del retrieval.
Scope: gap generico, aplica a cualquier KB. knowledge_base/operations.py:631-633 (_semantic_search) y kb_agent/ontologizador/compiler.py:345-346 (_semantic_candidates) hacen 'if not emb: continue' sin log ni excepcion: un atom sin vector desaparece del retrieval sin dejar rastro. Con la KB entera sin vectores el sistema sigue respondiendo por fuzzy matching literal, asi que el defecto es invisible desde afuera -- fue exactamente lo que paso con knowledge_vitali (50/50 atoms con embedding null; ver el commit que lo arreglo). Falta una guarda: chequeo de arranque o en el job static de CI que cuente atoms sin vector por KB y falle o advierta, mas un WARN la primera vez que _semantic_search descarta todo. Ojo con el falso positivo: los atoms agent-*-router y agent-*-gate no llevan vector por diseno (misma paridad en knowledge/ y knowledge_vitali/).
Validation: test que carga una KB con embeddings nulos y afirma que la guarda avisa; extension del job static de CI.

## Implementation Path

_Outline the expected implementation route or affected surface._

Promoted from desk/drawer/tasks/task-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa.md.

## Validation

_List the checks required before this task can close._

- pytest

## Done When

_Name the observable condition that makes the task complete._

Promoted work is completed, validated, and closed with a commit.
