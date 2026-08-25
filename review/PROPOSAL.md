# Part 2 — Proposal: features to steal / build for a typed-language knowledge agent

Framing: "the mind" (typed knowledge) vs "how we interact" (projections + agents).
Goal: a **framework to work over typed language**. Below, each feature marked:
- `[STEAL]` copy code/pattern nearly as-is
- `[ROB]` take the idea, reimplement smaller
- `[GLUE]` new integration work connecting existing pieces

## A. The mind (typed substrate)

### A1. One canonical typed-node + edge core `[ROB]`
Pick ONE node/edge model and make everything else an adapter.
- Base it on `kgdb` `KnowledgeNode` + `VocabularyTerm` (open vocab, closed structure) — `tools/kgdb/src/kgdb/contracts/{base,node}.py`.
- Absorb ontomap's who/what/where/when/how/why as *optional edge facets*, not a competing model.
- Rationale: kills the 3-edge-model fragmentation. Single identity/IRI scheme.

### A2. Reversible typed documents as the authoring surface `[STEAL]`
- Reuse `sldb` `StructuredNLDoc` + `⸢rev•field⸥` markers wholesale (`tools/sldb`).
- Gives lossless Markdown ⇄ typed model, field-level CRUD, `.sldb` change-aware store.
- This is the strongest already-working primitive in the whole ecosystem.

### A3. Truth × Sense typing as a validation gate `[ROB]`
- From `Matrix`: every proposition carries `S_i` (well-typed/applicable) and `V_i` (true).
- Reuse `spec/proposition_lifecycle.yaml` state machine: reject `unsinnig` (out-of-schema) distinctly from `false`.
- Small, high-value: an agent that says "this is not even a valid question here."

### A4. Provenance chain: Source → Sample → Atom `[STEAL]`
- From `knowledge` repo (`spec/KB_SYSTEM_SPEC.md`): immutable sources (path+hash), verifiable samples, distilled atoms.
- Plus grounding-maturity states (`grounding:derived` vs validated) to avoid false precision.
- Reuse the content-vs-governance split: atoms stay clean, metadata in a registry.

### A5. Facet catalog for typed dimensions `[STEAL]`
- `tools/ontology/contracts/facets.py`: IO/AST/Semantic/ADR/TestMap/Compliance/Source/Git facets.
- Ready-made typed dimensions for code/doc nodes with provenance + drift status.

## B. How we interact (projection + agency)

### B1. Zero-dependency HTML projection (wikipedia/astro-like) `[STEAL]`
- `spec2viz/renderers/graph_html.py` (file://-safe collapsible tree) + `deskops.py` catalog builder.
- Generates a static, filterable site from the typed store. Lowest-effort "wikipedia view."

### B2. Typed node registry + editable graph `[STEAL]`
- `graph_ui` `NodeTypeRegistry` (zod schema per typeId, multi-zoom renderers, allowed connections).
- `schema-to-graph` / `graph-to-domain` bidirectional projection loop.
- The "hum-body" feature proves the multi-lens (same data, N views) pattern.

### B3. Prose annotation overlay `[ROB]`
- `marcado` HTML-comment markers over unmodified text → addressable ranges + stable anchors.
- Use as the citation/highlight layer linking prose spans to typed atoms.

### B4. Graph query DSL as the agent's question interface `[STEAL]`
- `kgdb` `StructuredQuery` (filters ∩ relations ∩ scope) serialized as JSON, with worked example queries.
- The agent asks the graph in a typed language instead of grepping.

### B5. spec→IR→renderer separation `[STEAL]`
- `spec2viz` `ir.py` + compilers + renderers. Add a view without touching semantics.

## C. Agency / orchestration

### C1. G-first loop (cheap-deterministic-first) `[ROB]`
- `hum/agent/core.lisp`: L0 memory → L1 graph → LLM fallback, with hit/call energy counters.
- Reusable as the agent's core control loop; LLM only when the typed store can't answer.

### C2. Typed s-expr as the LLM output contract `[ROB]`
- `hum/agent/ir.lisp`: constrain the model to `(think/rel/model/command/unl)`; compile each kind differently (relation→edge, command→tool).
- Makes LLM output inspectable and executable, not free text.

### C3. Zero-context subagent bundles + phase-gated rituals `[STEAL]`
- `deskops` task lifecycle: TaskDoc + Pills + Atoms = 100% context; execution/testing/closeout gates.
- CLI-as-state-recovery (read repo artifacts, not chat) = anti-hallucination.
- Directly reusable to orchestrate the knowledge agent itself.

### C4. Iterable corpus-refinement loop `[STEAL]`
- `knowledge` "weak-answers pass": batched N-atom passes, fixed answer template, structural validation.
- An agent self-improvement loop over the KB.

## D. Ingestion

### D1. Code → typed spec `[ROB]` — `core/code2specyaml` (Tree-sitter/AST → IR → specYaml).
### D2. Conversation → structure `[ROB]` — `core/turn_extractor` (sessions → typed turns).
### D3. Web → typed atlas `[ROB]` — `hum-scrapper` Labyrinth (persistent typed portal atlas + LLM-generated recursive extraction schema).

## Recommended minimal spine (the "framework over typed language")
If we build almost nothing new, the smallest working loop is:
1. `sldb` typed reversible docs (A2) as authoring + storage.
2. `kgdb` node/edge core + query DSL (A1, B4) as the graph.
3. `sldb → kgdb` semantic export (already exists) as the bridge.
4. `spec2viz` graph_html (B1) as the read projection.
5. `deskops` lifecycle (C3) to orchestrate authoring/validation.
6. Add `S_i/V_i` gate (A3) + Source→Sample→Atom provenance (A4) as the "typed language" differentiators.

Everything else (graph_ui editor, marcado overlays, ingestion, G-first LLM loop) is additive.
