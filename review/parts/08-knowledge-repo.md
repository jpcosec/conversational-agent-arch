# Recon index: KNOWLEDGE repo (`/home/jp/proyectos/knowledge`)

## 0. One-line purpose
A concrete, working knowledge-base *instance* built on `sldb` + `deskops`, that atomizes durable knowledge into provenance-tracked "atoms" (5WH1+ Q/A units) with a Source→Sample→Atom trace model, a three-graph (provenance/concept/structure) architecture, a knowledge-only CLI, an atom-metadata registry, and derived spec2viz diagram views.

## 1. Repos / dirs covered
- `/home/jp/proyectos/knowledge` — root of the standalone KB subproject (project identity "Upla").
- `/home/jp/proyectos/knowledge/knowledge` — the `knowledge` Python CLI (atoms + metadata + graph + validate).
- `/home/jp/proyectos/knowledge/README.md` — orientation (spec/desk/.sldb/scripts).
- `/home/jp/proyectos/knowledge/spec/` — 18+ design specs (KB system, graph architecture, anchoring, atom quality).
- `/home/jp/proyectos/knowledge/desk/` — deskops operational surface (board/tasks/rituals/atoms/primitives).
- `/home/jp/proyectos/knowledge/.knowledge/atoms/` — 131 atom markdown files + `tag-namespaces.yaml` (canonical atom store).
- `/home/jp/proyectos/knowledge/metadata/atoms/atom-metadata-registry.yaml` — metadata moved OUT of atoms (~2547 lines).
- `/home/jp/proyectos/knowledge/.sldb/` — SLDB store: models, document indices, runtime graph snapshots.
- `/home/jp/proyectos/knowledge/views/spec2viz/` — semantic YAML diagram specs + rendered mermaid/default outputs.
- `/home/jp/proyectos/knowledge/human_feedback/` — Obsidian vault (empty except `.obsidian` config).
- `/home/jp/proyectos/knowledge/@human_feedback/INTERVENTION_NEEDED.md` — historical human-intervention log (now resolved).
- `/home/jp/proyectos/knowledge/diagramas/` — hand-authored Spanish overview diagrams (three-graph, anchor bundle, etc).
- `/home/jp/proyectos/knowledge/scripts/generate_atoms.py`, `subagent-outputs/` — atom-generation tooling + agent run logs.
- Review artifacts: `provenance-review.md`, `tracking-review.md`, `weak-answers-pass{,-2,-3}.md`, `top-level-atom-hardening.md`.

## 2. Layer classification
- **MIND** — `.knowledge/atoms/` (atom corpus = ontology/knowledge substrate), `.knowledge/atoms/tag-namespaces.yaml` (semantic namespaces), `metadata/atoms/atom-metadata-registry.yaml` (governance/provenance faceting), `spec/` (design ontology).
- **DATA** — `.sldb/` (SLDB store: `core/models/*.yaml`, `core/documents/*.yaml`, `runtime/knowledge_graph.kg.json`, `semantic_index.yaml`, `semantic_dag.yaml`).
- **INTERACTION** — `views/spec2viz/` (derived diagrams), `diagramas/` (overview projections). Specs also reference `graph_ui`, `sldb-ui`, `spec2viz` as projection surfaces.
- **HARNESS** — `desk/` (deskops board/tasks/rituals/primitives), `knowledge` CLI, `scripts/generate_atoms.py`, `subagent-outputs/`.
- **OTHER** — `human_feedback/` (Obsidian vault, effectively empty), `@human_feedback/INTERVENTION_NEEDED.md` (archived log).

## 3. Descriptive index (the core deliverable)

### CLI
- `/home/jp/proyectos/knowledge/knowledge` — working. Python/argparse CLI `knowledge`. Subcommands: `list {atoms,metadata,namespaces}`, `show {atom,metadata}`, `add atom`, `set-metadata`, `graph {build,missing,neighbors,trace,list,show}`, `validate`. Reads atoms as markdown-with-YAML-frontmatter; delegates graph/validate to `deskops` and `sldb` subprocesses.

### Atom store (MIND)
- `/home/jp/proyectos/knowledge/.knowledge/atoms/*.md` — working. 131 atoms; each is frontmatter (`id`, `title`, `five_wh_one_plus`, `tags`, `provenance`) + `# Title` + `## Answer`. Canonical location (CLI prefers `.knowledge/atoms` over legacy `desk/atoms`).
- `/home/jp/proyectos/knowledge/desk/atoms/*.md` — legacy mirror, same 131 basenames (identical set; `diff` confirms). Reviews (`tracking-review.md`) count 74 top-level + 26 nested bootstrap = 100 there historically; current tree has 131 flat.
- `/home/jp/proyectos/knowledge/.knowledge/atoms/tag-namespaces.yaml` — working. Defines *semantic* namespaces still allowed on atoms: `cross`, `domain`, `entity`, `graph`, `layer`, `system`, `topic`. Notes that governance/provenance/project/source/grounding/role/etc. were moved to the metadata registry.

### Metadata (MIND/governance)
- `/home/jp/proyectos/knowledge/metadata/atoms/atom-metadata-registry.yaml` — working. `document_kind: atom_metadata_registry`; `records[]` keyed by `atom_id` with `path`, `title`, `provenance_statement`, and grouped `metadata_tags` (`project:`, `source:`, `source_kind:`, `scope:`, `method:`, `role:`, `grounding:`). Keeps atoms as "pure knowledge units."

### SLDB store (DATA)
- `/home/jp/proyectos/knowledge/.sldb/core/models/*.yaml` — model registrations (AtomDoc, FAQDoc, TaskDoc, RepositoryDoc, RitualDoc, StepDoc, PillDoc, BoardDoc, InboxNoteDoc). `AtomDoc.yaml` points `model_ref: deskops.models:AtomDoc` at `/home/jp/proyectos/hum-ecosystem/tools/deskops/deskops/models/atom.py`.
- `/home/jp/proyectos/knowledge/.sldb/core/documents/*.yaml` — tracked-document registries (hashes + semantic_tags per doc). `AtomDoc.yaml` is the authoritative atom tracking index.
- `/home/jp/proyectos/knowledge/.sldb/runtime/knowledge_graph.kg.json` — graph snapshot (`schema: deskops_kgdb_graph_snapshot_v1`, 137 nodes, **edge_count: 0** — nodes materialized, edges not yet extracted). Also `knowledge_graph.nx.json`, `semantic_index.yaml`, `semantic_dag.yaml`, `runtime/sections/AtomDoc.yaml`.

### Specs (design ontology)
- `/home/jp/proyectos/knowledge/spec/KB_SYSTEM_SPEC.md` — the central spec. Layers: operative (deskops), sources (immutable, path+hash), samples/"biopsias" (traceable cuts), atoms (distilled). Principle: **Fuente → Biopsia → Átomo**.
- `/home/jp/proyectos/knowledge/spec/ATOM_CONCEPT_GRAPH_SCHEMA.md` — node/edge schema: backbone (`Source`, `Sample`, `Atom`), concept, projected-structural, light tag facets. "Not everything reduces to Tag."
- `/home/jp/proyectos/knowledge/spec/GRAPH_ARCHITECTURE.md`, `THREE_GRAPH_MODEL_DIAGRAMS.md`, `MULTI_SOURCE_ANCHORING.md`, `ATOM_CONCEPT_GRAPH.md`, `THE_KNOWLEDGE_DATABASE.md`, `KNOWLEDGE_INDEX_AND_RETRIEVAL.md`, `NAMESPACE_TREE.md`, `ATOM_IDENTIFICATION_AND_LAYOUT.md`, `ATOM_METADATA_DOC.md`, `KB_SYSTEM_CLARIFICATIONS.md`, `BOOTSTRAP_KB_WITH_CURRENT_DESKOPS.md`, `DESKOPS_FOR_KNOWLEDGE_MANAGEMENT.md`, `LEGACY_EXTRACTION_FROM_HUM_ECOSYSTEM.md` — supporting specs.
- `/home/jp/proyectos/knowledge/spec/atom_quality/` — the quality regime: `ATOM_QUALITY_CHECKLIST.md`, `ATOM_AUTHORING_STANDARD.md`, `ATOM_AUTHORING_PROCEDURE.md`, `ATOM_AUTHOR_SKILLS.md`, `ATOM_REVIEW_ROUTINE.md`, `ATOM_TAGGING_AND_PROVENANCE_CONVENTIONS.md`, `ATOM_MODEL_ALIGNMENT_AND_MIGRATION_NOTES.md`, `INDEX.md`.
- `/home/jp/proyectos/knowledge/spec/source_apps/` — synthesis notes over the source tools this KB draws from: `sldb.md`, `deskops.md`, `kgdb.md`, `ontomap.md`, `tractatusIR.md`, `spec2viz.md`, `graph_ui.md`, `sldb-ui.md`, `marcado.md`, `hum-scrapper.md`, `repopackage.md`, `SYNTHESIZED_ARCHITECTURE.md`, `INDEX.md`.

### Desk (HARNESS)
- `/home/jp/proyectos/knowledge/desk/` — deskops workspace: `config.json` (project_identity "Upla", desk_format 1.0.0), `rituals/{closeout,execution,testing}.md`, `tasks/Board.md`, `contexts/pills.md`, `primitives/{conditions,edges,checklists,hooks,operators}`, plus empty `faq/`, `inbox/`, `registry/`, `routines/`, `steps/`, `drawer/`.

### Views (INTERACTION)
- `/home/jp/proyectos/knowledge/views/spec2viz/specs/*.yml` — 11 semantic diagram specs (e.g. `sequence.retrieval-pipeline.yml`, `state.proposition-lifecycle.yml`, `state.grounding-maturity.yml`, `component.kb-canonical-layers.yml`, `activity.bootstrap-path.yml`).
- `/home/jp/proyectos/knowledge/views/spec2viz/out/{mermaid,default}/` — rendered outputs. README documents `spec2viz validate|render` refresh commands.

### Reviews / passes (this task's focus artifacts)
- `provenance-review.md` — decision NOT to batch-add per-file provenance; recommends provisional corpus-level wording.
- `tracking-review.md` — audit: all 100 (74 top + 26 nested) atoms tracked in `.sldb/core/documents/AtomDoc.yaml`, 0 untracked/stale.
- `top-level-atom-hardening.md` — normalized `role:*`/`topic:*` tags on 53 of 74 atoms; rewrote 6 answers.
- `weak-answers-pass.md`, `-2.md`, `-3.md` — three passes, 12 atoms each (36 total), strengthened only `## Answer` using an "affirm / distinguish / imply" 2–3 sentence pattern.

## 4. Typed-language angle
Concrete typed/schema/IR artifacts:
- **Atom schema (implicit typed doc):** `/home/jp/proyectos/knowledge/knowledge` lines ~19–63 define `Atom` dataclass + regexes `FRONTMATTER_RE`, `ANSWER_RE`, `TAG_RE` (`^[a-z][a-z0-9_]*:[a-z][a-z0-9_-]*$`) and `ATOM_QUESTIONS = ["what","why","how","how_not","when","where","for_whom"]` (the 5WH1+ typed question enum).
- **Semantic tag type system:** `/home/jp/proyectos/knowledge/.knowledge/atoms/tag-namespaces.yaml` — namespaced faceted tag grammar with `meaning`/`use_when`/`do_not_use_when` per namespace.
- **Metadata registry schema:** `/home/jp/proyectos/knowledge/metadata/atoms/atom-metadata-registry.yaml` — `document_kind`, grouped `metadata_tags` by namespace.
- **SLDB models:** `/home/jp/proyectos/knowledge/.sldb/core/models/*.yaml` bind doc types to Python model classes with `semantics:` type tags (e.g. `type.knowledge.atom`, `workspace.desk.atoms`).
- **Graph snapshot IR:** `/home/jp/proyectos/knowledge/.sldb/runtime/knowledge_graph.kg.json` — typed node identity (`node_id`,`node_type`) + `semantics` + `source.provenance`; schema `deskops_kgdb_graph_snapshot_v1`.
- **Concept-graph type grammar:** `/home/jp/proyectos/knowledge/spec/ATOM_CONCEPT_GRAPH_SCHEMA.md` — Source/Sample/Atom node types and edge families (`supports`, `distilled_from`, `anchored_in`, `drawn_from_section`, `depends_on`, etc, visible in atom titles).
- **View DSL:** `/home/jp/proyectos/knowledge/views/spec2viz/specs/*.yml` — semantic diagram type language.

## 5. Stealable / reusable for a knowledge agent
- **Atom = frontmatter Q/A unit typed by 5WH1+.** Minimal, durable, LLM-authorable knowledge unit: `id/title/five_wh_one_plus/tags/provenance` + `## Answer`. See `knowledge` CLI `cmd_add_atom` and `ATOM_QUESTIONS`.
- **Separation of pure knowledge from governance metadata.** Atoms stay clean; provenance/project/source/grounding/role tags live in `metadata/atoms/atom-metadata-registry.yaml`. Cleanly reusable pattern: content vs. governance split.
- **Source → Sample(biopsy) → Atom provenance chain** (`spec/KB_SYSTEM_SPEC.md`). Sources immutable (path+hash), samples are verifiable anchored cuts, atoms are distilled. Directly reusable provenance model for a knowledge agent.
- **Grounding maturity as first-class, honest-uncertainty state.** Atoms tagged `grounding:derived` vs sample-linked/validated; provisional corpus-level provenance wording explicitly avoids "false precision" (`provenance-review.md`). Strong pattern for agent-generated knowledge with unverified sources.
- **Three-graph model** (provenance / concept / structure) kept distinct but interoperable (`spec/GRAPH_ARCHITECTURE.md`, `diagramas/`). Relation-first / proposition-first ontology (`atom-proposition-first-architecture.md`: facts `(R a b)` over object-attribute pairs).
- **Quality gates + review routines.** `spec/atom_quality/ATOM_QUALITY_CHECKLIST.md` (atomicity, single-claim, not-a-restatement, reusability, provenance-present) — a concrete rubric an agent can self-apply. `knowledge validate` chains `sldb stores update/check` + `deskops graph missing` as an authoring completion gate.
- **"Weak-answers pass" as an iterable refinement workflow.** Batched 12-atom passes with a fixed "affirm/distinguish/imply" answer template + structural validation — a reusable agent self-improvement loop over a corpus.
- **Derived views are reversible to atoms.** spec2viz diagrams generated from structured YAML, not hand-drawn (`atom-materialized-diagrams-should-be-derived-views-...`, `atom-view-generation-should-be-reversible-back-to-atoms-and-evidence-links`).
- **Deterministic selectors + fuzzy fallback** in CLI (`select_atom`, `find_snapshot_node`) — exact-then-fuzzy resolution, good UX pattern for agent tooling.

## 6. Open questions / gaps
- **Graph edges are empty** (`knowledge_graph.kg.json` `edge_count: 0`, all atom nodes `edges: []`). The rich edge families (supports/distilled_from/anchored_in) exist as atom *claims* but are not materialized in the snapshot yet.
- **Dual atom stores**: `.knowledge/atoms/` and `desk/atoms/` hold identical 131 files; CLI prefers `.knowledge/atoms`. Migration is mid-flight — unclear which is authoritative long-term or how they stay in sync.
- **Path drift in specs**: specs reference `/home/jp/Upla/kb/...` and `/home/jp/Upla/tutor_apoe/...`; reviews reference `/home/jp/Upla/kb`; actual repo is `/home/jp/proyectos/knowledge`. Historical relocation not fully reconciled.
- **Samples/sources layer is largely spec-only.** No `sources/` or `samples/` dirs present; provenance is mostly free-text `provenance:` statements + `grounding:derived`. The Source→Sample→Atom chain is designed but not yet populated with real sample bindings.
- **External dependency on `deskops`/`sldb` binaries** (subprocess calls, `model_ref` into `/home/jp/proyectos/hum-ecosystem/tools/deskops/`). Repo is not standalone-runnable without that ecosystem.
- **`human_feedback/` is an empty Obsidian vault**; the actual feedback record lives in `@human_feedback/INTERVENTION_NEEDED.md` (marked resolved). Human-in-the-loop channel is defined but dormant.
- Reviews note the workspace **is not a git repo** in prior runs (staged-file checks failed); root now has `.git/`.

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Produced a recon index for /home/jp/proyectos/knowledge following review/TEMPLATE.md sections 0-6 exactly, covering the required targets (README, knowledge CLI, desk/, spec/, metadata/, views/, .sldb/, .knowledge/, human_feedback/, provenance-review.md, tracking-review.md, weak-answers-pass*.md, top-level-atom-hardening.md) with absolute paths. No scope widening; recon only, no repo files modified."
    }
  ],
  "changedFiles": [
    "/home/jp/proyectos/gemini_test/review/parts/08-knowledge-repo.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [
    {
      "command": "ls/find/grep/read across /home/jp/proyectos/knowledge (README, knowledge CLI, spec, .sldb, .knowledge, metadata, views, reviews)",
      "result": "passed",
      "summary": "Mapped repo structure, atom schema, provenance model, graph snapshot, and review passes."
    },
    {
      "command": "diff .knowledge/atoms vs desk/atoms basenames; count atoms",
      "result": "passed",
      "summary": "Confirmed 131 identical atom files in both stores; graph snapshot has 137 nodes, 0 edges."
    }
  ],
  "validationOutput": [
    "131 atoms in .knowledge/atoms and desk/atoms (identical basenames)",
    "knowledge_graph.kg.json: node_count=137, edge_count=0",
    "Output written to /home/jp/proyectos/gemini_test/review/parts/08-knowledge-repo.md"
  ],
  "residualRisks": [
    "Did not deep-read every spec/atom; breadth-first per task. Graph edge emptiness and dual-store authority inferred from snapshot + CLI logic, not from ecosystem docs."
  ],
  "noStagedFiles": true,
  "diffSummary": "Added one recon index markdown file; no source files modified.",
  "reviewFindings": [
    "no blockers"
  ],
  "manualNotes": "Specs use stale /home/jp/Upla/kb paths; actual repo is /home/jp/proyectos/knowledge. Source->Sample->Atom chain is designed but sample/source layers are not yet populated; provenance is currently mostly free-text + grounding:derived."
}
```
