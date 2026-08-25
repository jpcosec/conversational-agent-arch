# Recon index: HUM knowledge CORE (Common Lisp + OWL + desk)

## 0. One-line purpose
Two coupled repos forming an autopoietic "development OS": a **G-first cognitive shell** (`hum`, Common Lisp/SBCL agent loop with an s-expression IR) and a **knowledge/ontology substrate** (`hum-core`, Python `wiki-compiler` that compiles Markdown wiki → RDF/OWL knowledge graph with SHACL validation, plus desk/drawers work-surface rituals).

## 1. Repos / dirs covered
- `/home/jp/proyectos/hum-ecosystem/hum` — operational shell ("the doing"): agent loops, workflow orchestration, execution engine, Lisp core.
- `/home/jp/proyectos/hum-ecosystem/hum-core` — knowledge base ("the mind"): wiki→OWL compiler, ontology, desk/drawers, contracts, structure measuring.

## 2. Layer classification
- **MIND**
  - `/home/jp/proyectos/hum-ecosystem/hum-core/wiki/` — living documentation / concepts / standards (authoritative source of truth).
  - `/home/jp/proyectos/hum-ecosystem/hum-core/hum.owl` — derived RDF/OWL ontology (KnowledgeNode graph).
  - `/home/jp/proyectos/hum-ecosystem/hum-core/src/wiki_compiler/` — the compiler that turns wiki into the graph/ontology.
  - `/home/jp/proyectos/hum-ecosystem/hum/agent/ir.lisp` — s-expression typed IR (UNL/model/relation/command/thought).
- **DATA**
  - `/home/jp/proyectos/hum-ecosystem/hum-core/.sldb/` — sldb document/model store (ConceptDoc/ADRDoc/TaskDoc).
  - `/home/jp/proyectos/hum-ecosystem/hum-core/knowledge_graph.json` — compiled graph snapshot (KGDB target).
- **INTERACTION**
  - `/home/jp/proyectos/hum-ecosystem/hum/agent/repl.py`, `/home/jp/proyectos/hum-ecosystem/hum-core/wiki-compiler` (CLI), `pirate` (smaller self).
- **HARNESS**
  - `/home/jp/proyectos/hum-ecosystem/hum/workflow/` (coordinator/guard), `/home/jp/proyectos/hum-ecosystem/hum-core/desk/` + `drawers/` rituals, autopoiesis cycle.
- **OTHER**
  - `/home/jp/proyectos/hum-ecosystem/hum-core/src/{markov_entropy,structural_abstraction}/` + `deterministic_structure_measuring.md` (FFT/entropy "energy" metrics).

## 3. Descriptive index (the core deliverable)

### hum (operational shell)
- `/home/jp/proyectos/hum-ecosystem/hum/main.lisp` — working — CLI entrypoint; dispatches `--dispatch-{eltrace,vocabulary,tool,llm}`, REPL, and raw s-expression execution via `process-pipeline`.
- `/home/jp/proyectos/hum-ecosystem/hum/hum.asd` — working — ASDF system: loads packages, execution (system/providers/query/tools), agent (ir/eltrace/cache/core).
- `/home/jp/proyectos/hum-ecosystem/hum/agent/ir.lisp` — working — **the typed-language heart**: `classify-sexp`, `*sexp-kinds* = (:unl :model :relation :command :thought)`, UNL projection, sexp→KGDB-node JSON, sexp→routine→tool compiler, `process-pipeline`.
- `/home/jp/proyectos/hum-ecosystem/hum/agent/core.lisp` — working — G-first loop: L0 in-memory cache → L1 KGDB → LLM fallback; energy counters (`*g-hits*`, `*llm-calls*`); LLM prompt constrained to emit s-expressions.
- `/home/jp/proyectos/hum-ecosystem/hum/agent/eltrace.lisp` — working — execution trace log (list/get/run/extract of past s-exprs).
- `/home/jp/proyectos/hum-ecosystem/hum/agent/vocabulary.yaml` — working — Spanish verb DSL (pensar/ejecutar/consultar/checkear/escribir/aprender/eltrace) with typed args → handlers.
- `/home/jp/proyectos/hum-ecosystem/hum/execution/query.lisp` — working — KGDB bridge: `query-g`, `persist-to-g`, `ingest-snapshot` (shells out to `kgdb` CLI, writes `hum-core/knowledge_graph.json`).
- `/home/jp/proyectos/hum-ecosystem/hum/execution/{system,providers,tools}.lisp` — working — system command exec, LLM provider config from env/.env, tool registry.
- `/home/jp/proyectos/hum-ecosystem/hum/agent/{dispatcher,perception,memory,audit}.py`, `workflow/{coordinator,guard}.py`, `energy/monitor.py`, `execution/` — proto/working — Python-side dispatcher, perception, workflow policy, energy monitoring.
- `/home/jp/proyectos/hum-ecosystem/hum/hum_components.spec.yml` + `.mmd` — working — component map: HumCLI→DispatcherPython→MainLisp(AgentCore/ExecutionEngine/KnowledgeBridge)→KGDB/LLM.
- `/home/jp/proyectos/hum-ecosystem/hum/hum_activity.spec.yml` + `.mmd` — working — cognition activity flow: input→is_sexp→G-first loop→pipeline→persist→dispatch. **spec.yml = typed node/edge graph DSL, .mmd = Mermaid render.**
- `/home/jp/proyectos/hum-ecosystem/hum/README.md` — Operational shell doc: agent/workflow/energy/execution; "G-first: Formal logic first, LLM fallback".

### hum-core (knowledge substrate)
- `/home/jp/proyectos/hum-ecosystem/hum-core/README.md` — 6-step seed workflow; 4-zone model raw/wiki/desk/drawers; `wiki-compiler build|run` (autopoiesis).
- `/home/jp/proyectos/hum-ecosystem/hum-core/AGENTS.md` — session-init ritual: read selfDocs (WhoAmI/WhatAmI/HowAmI/WhereAmI/WhenAmI/WhyAmI) + Index; adopt autopoietic identity; tools `wiki-compiler` + `pirate`.
- `/home/jp/proyectos/hum-ecosystem/hum-core/hum.owl` — working (1198 lines, derived/gitignored) — RDF/XML; every node is `hum:KnowledgeNode` with `node_id`, `node_type`, `status`, `references`. Namespace `https://hum.ai/ontology/`. (Skimmed only — flat `rdf:Description` list, no explicit class hierarchy in file.)
- `/home/jp/proyectos/hum-ecosystem/hum-core/src/wiki_compiler/` — working — the compiler. Key: `main.py` (CLI), `builder.py`, `auditor.py`, `cleanser.py`, `scaffolder.py`, `gates.py`, `sync_gate.py` (Pydantic↔OWL), `shacl/` (shapes+validator), `contracts/`, `node_templates.py`, `face/` (FFT), `adapters/`, `commands/`.
- `/home/jp/proyectos/hum-ecosystem/hum-core/src/wiki_compiler/shacl/shapes.py` — working — SHACL node/edge shapes: enumerated `node_type` and `relation_type` vocabularies (the ontology's type system, see §4).
- `/home/jp/proyectos/hum-ecosystem/hum-core/wiki/` — working — 49 md files: `Index.md`, `concepts/`, `standards/{artifacts,languages}/`, `how_to/`, `reference/{cli,diagrams}/`, `adrs/`, `system/`, `selfDocs/` (empty on disk; referenced by AGENTS.md — likely generated).
- `/home/jp/proyectos/hum-ecosystem/hum-core/wiki/reference/owl_integration.md` — working — **canonical OWL doc**: markdown→rdf→hum.owl pipeline, SPARQL, HermiT/Pellet reasoning, SyncGate, SHACL. (rdflib for extract/export/query, owlready2 for reasoning.)
- `/home/jp/proyectos/hum-ecosystem/hum-core/wiki/reference/knowledge_node_facets.md` — working — node facet model.
- `/home/jp/proyectos/hum-ecosystem/hum-core/desk/` — working — active work surface: `STANDARDS.md` (executable rituals), `issues/`, `tasks/`, `Gates.md`, `atoms/`, `autopoiesis/`, `socratic/`, `pills/`, `unsolved/`, `mempalace_extraction.md`.
- `/home/jp/proyectos/hum-ecosystem/hum-core/desk/STANDARDS.md` — working — **executable governance**: multi-surface model, issue frontmatter schema, Initialization/Execution/Phase rituals, layer contracts, log-tag vocabulary, git hygiene.
- `/home/jp/proyectos/hum-ecosystem/hum-core/drawers/` — working — deferred work (many sldb/kgdb/workflow audit .md); `Board.md`, `diagrams/`, `requests/`.
- `/home/jp/proyectos/hum-ecosystem/hum-core/contracts/` — working — inter-repo contract surface: `integration.contract.yaml` (exports `workflow_context_bundle`; consumes sldb/kgdb/ontology payloads; pins sibling repo versions) + `schemas/*.schema.json` (4 JSON Schemas).
- `/home/jp/proyectos/hum-ecosystem/hum-core/.sldb/` — working — document store: `store_index.yaml` (registers ConceptDoc/ADRDoc/TaskDoc pydantic models via `model_ref`), `models/*.yaml`, `documents/*.yaml`.
- `/home/jp/proyectos/hum-ecosystem/hum-core/deterministic_structure_measuring.md` — working/experimental — FFT spectral + Markov n-gram + AST structural entropy to score code/text quality; feeds `energy.py`.
- `/home/jp/proyectos/hum-ecosystem/hum-core/src/{markov_entropy,structural_abstraction}/` + `src/wiki_compiler/face/` — proto — the measurement engines above.
- `/home/jp/proyectos/hum-ecosystem/hum-core/src/looting/{gemma-rag,gems,pirate}/` — proto — "looted"/imported subsystems (RAG, pirate small-self).
- `/home/jp/proyectos/hum-ecosystem/hum-core/knowledge_graph.json` — data — compiled KGDB snapshot; the L1 graph the Lisp shell queries.

## 4. Typed-language angle
Multiple overlapping type systems — this ecosystem is fundamentally about typed structured knowledge:

1. **S-expression IR (typed cognition)** — `/home/jp/proyectos/hum-ecosystem/hum/agent/ir.lisp`:
   `*sexp-kinds* = (:unl :model :relation :command :thought)`. Forms: `(think …)`, `(rel pred a b)`, `(model name fields)`, `(command name body)`, `(unl rel uw1 uw2)`. `classify-sexp` types by head; `sexp->routine->tool` compiles `(command …)` into a Lisp lambda+registered tool; `sexp-to-kgdb-node` serializes typed nodes to graph JSON. LLM is prompted to emit only these forms (`build-llm-prompt` in `core.lisp`).
2. **UNL (Universal Networking Language) anchor** — `ir.lisp` `project-to-unl`/`parse-unl-string`: `rel(uw1, uw2)` interlingua projection.
3. **OWL/RDF ontology** — `/home/jp/proyectos/hum-ecosystem/hum-core/hum.owl` + `wiki/reference/owl_integration.md`: namespace `https://hum.ai/ontology/`; class `KnowledgeNode`; properties `node_id`, `node_type`, `status`, `references`.
4. **SHACL shapes (the enumerated type vocabulary)** — `/home/jp/proyectos/hum-ecosystem/hum-core/src/wiki_compiler/shacl/shapes.py`:
   - `node_type ∈ {index, concept, standard, reference, how_to, adrs, selfDoc, workflow, faq}`
   - `compliance_status ∈ {implemented, partial, pending, violated}`
   - `relation_type ∈ {contains, implements, references, supersedes, derives_from, conflicts_with, validates}`
5. **spec-yaml DSL** — `/home/jp/proyectos/hum-ecosystem/hum/hum_components.spec.yml` and `hum_activity.spec.yml`: typed `nodes`/`edges` (with `kind:`, `relation:`) and `steps`/`branches`; each pairs with a `.mmd` Mermaid render. A declarative graph-spec → visualization language.
6. **Pydantic doc models (sldb)** — `/home/jp/proyectos/hum-ecosystem/hum-core/.sldb/store_index.yaml` references `wiki_compiler.contracts.wiki_nodes:ConceptDoc`, `:ADRDoc`, `tasks:TaskDoc` — typed document schemas with content-hash tracking.
7. **JSON Schema contracts** — `/home/jp/proyectos/hum-ecosystem/hum-core/contracts/schemas/{kgdb_graph_bundle,sldb_document_payload,ontology_audit_result,workflow_context_bundle}.schema.json` — cross-repo typed payloads.
8. **Markdown frontmatter → RDF** — YAML `identity{node_id,node_type}` + `edges[{target_id,relation_type}]` + `compliance{status}` (see `wiki/Index.md`) is the authoring surface that compiles into 3–4 above.

## 5. Stealable / reusable for a knowledge agent
- **G-first loop pattern** (`hum/agent/core.lisp`): L0 memory cache → L1 graph query → LLM only as fallback, with hit/call counters as an "energy" health metric. Cheap-deterministic-first is directly reusable.
- **Typed s-expression IR as the LLM contract** (`hum/agent/ir.lisp`): constrain the model to a tiny typed grammar (`think/rel/model/command/unl`) and compile each type differently (relation→graph edge, command→executable tool). Excellent pattern for a knowledge agent that must both reason and act deterministically.
- **sexp→routine→tool self-extension** (`ir.lisp` `sexp->routine->tool`): the agent learns new tools by compiling `(command …)` forms — a safe, inspectable "learn a skill" mechanism.
- **Single source → multi-target compilation**: Markdown+frontmatter → (a) `knowledge_graph.json` KGDB, (b) `hum.owl` RDF, (c) SHACL-validated typed nodes. `wiki/reference/owl_integration.md` documents the whole `markdown_to_rdf → export_to_owl → SPARQL/HermiT` pipeline.
- **SHACL as a compact, enforceable ontology type system** (`shacl/shapes.py`): closed enumerations for node/edge/status. Copy this as the schema for any knowledge-node store.
- **SyncGate bidirectional Pydantic↔OWL** (`src/wiki_compiler/sync_gate.py`, doc in owl_integration.md): keeps programmatic models and the ontology consistent, with SHACL violation reporting.
- **spec.yml + .mmd pairing** (`hum/*.spec.yml`): declarative typed graph DSL that renders to Mermaid — reusable for making an agent's architecture/flow self-describing and visualizable.
- **Desk/drawers executable rituals** (`hum-core/desk/STANDARDS.md`): frontmatter-typed issues, Initialization/Execution rituals, closed log-tag vocabulary, "a plan that survives its completion is drift" — a concrete methodology for agent-driven task hygiene.
- **Deterministic structure measuring** (`deterministic_structure_measuring.md` + `src/{markov_entropy,structural_abstraction,wiki_compiler/face}`): FFT/entropy/AST metrics to score coherence — reusable as an automated quality/energy signal for generated knowledge or code.
- **Contract-driven repo boundaries** (`contracts/integration.contract.yaml`): explicit exports/consumes + version pins across sibling repos (sldb/kgdb/ontology) — good pattern for a multi-service knowledge agent.
- **eltrace** (`hum/agent/eltrace.lisp`): persistent, replayable execution trace of every s-expression — provenance + reproducibility for agent actions.

## 6. Open questions / gaps
- `wiki/selfDocs/` is empty on disk yet AGENTS.md mandates reading 6 selfDocs (WhoAmI…WhyAmI) — generated at runtime? Sourced from `raw/`? Where is the "mind's identity" actually stored?
- `hum.owl` is a flat `rdf:Description` list with no explicit `owl:Class`/property axioms in-file (grep found none) — the ontology's class hierarchy/reasoning axioms live where? (owlready2 world? `owl_backend/`?) Reasoning value depends on this.
- Two "energy" notions: Lisp counters (`core.lisp`) vs FFT/entropy metrics (`energy.py`) — are they unified or parallel?
- `src/wiki_compiler/owl_backend/` and `owl_reasoner.py` are referenced by the doc but not confirmed present in the `src/wiki_compiler/` listing (saw `adapters/`, `shacl/`, `face/`) — verify module locations before relying on them.
- `.sldb/` only registers 3 doc models with `stores: []` — the sldb layer looks early/proto; relationship to `knowledge_graph.json` (KGDB) vs OWL needs clarification.
- `pirate` (smaller self) and `src/looting/` are referenced but not explored here — separate recon likely needed.
- Python vs Lisp split: dispatcher/perception/workflow exist in both `.py` and `.lisp` — which is authoritative at runtime?

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Produced recon index following TEMPLATE.md section structure (0-6) at /home/jp/proyectos/gemini_test/review/parts/01-hum-core.md, covering only the assigned hum and hum-core paths; no code changes made."
    }
  ],
  "changedFiles": [
    "/home/jp/proyectos/gemini_test/review/parts/01-hum-core.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [
    {
      "command": "grep owl:Class/Property counts + wc hum.owl",
      "result": "passed",
      "summary": "hum.owl is 1198 lines, flat rdf:Description KnowledgeNode list, no owl:Class axioms in-file"
    },
    {
      "command": "ls/find across hum and hum-core subdirs",
      "result": "passed",
      "summary": "enumerated agent/, workflow/, execution/, wiki/, desk/, drawers/, contracts/, .sldb/, src/wiki_compiler/"
    }
  ],
  "validationOutput": [
    "Output file written with all 7 template sections (0 One-line purpose through 6 Open questions), explicit absolute paths throughout"
  ],
  "residualRisks": [
    "owl_backend/ module location unconfirmed vs owl_integration.md claims",
    "selfDocs/ empty on disk; identity source unresolved",
    "pirate and src/looting/ not deeply explored (breadth-over-depth per task)"
  ],
  "noStagedFiles": true,
  "diffSummary": "Added one recon markdown file; no source code modified",
  "reviewFindings": [
    "no blockers"
  ],
  "manualNotes": "Recon-only scouting task. 'The mind' = hum-core wiki->OWL knowledge substrate + hum's typed s-expression IR (agent/ir.lisp). Typed-language angle spans 8 distinct type systems documented in section 4. Key files to open first: hum/agent/ir.lisp and hum-core/src/wiki_compiler/shacl/shapes.py."
}
```
