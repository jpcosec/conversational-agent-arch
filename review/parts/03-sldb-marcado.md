# Recon index: SLDB toolchain (sldb, sldb-ui, sldb-refactor-worktree, marcado, marcado-ui)

## 0. One-line purpose
A family of tools treating Markdown as a **typed, reversible, query-able document/data layer**: `sldb` maps Markdown ⇄ Pydantic models via reversible markers + a `.sldb` store; `marcado` marks prose ranges with semantic milestone markers to build an Abstract Semantic Graph; the `-ui` repos are projection/editing frontends.

## 1. Repos / dirs covered
- `/home/jp/proyectos/hum-ecosystem/tools/sldb` — Structured Language Database: Markdown↔Pydantic extraction/render + `.sldb` store (Python).
- `/home/jp/proyectos/hum-ecosystem/tools/sldb-ui` — Astro/React web UI over an SLDB store (browse models/docs/fields/sections/ast).
- `/home/jp/proyectos/hum-ecosystem/tools/sldb-refactor-worktree` — planning/architecture worktree steering SLDB toward a Clojure-owned immutable revisioned graph kernel.
- `/home/jp/proyectos/hum-ecosystem/tools/marcado` — Semantic Markdown ASG MVP: HTML-comment markers over prose ranges → canonical ASG JSON + anchors.
- `/home/jp/proyectos/hum-ecosystem/tools/marcado-ui` — Vite/React document workspace for rendering/inspecting/editing marcado semantic Markdown.

## 2. Layer classification
- `sldb` (core/store/models) — **DATA** (document/state layer; the canonical StructuredNLDoc substrate).
- `sldb` marker grammar + Pydantic contracts — **MIND-adjacent / DATA** (typed field schemas over prose).
- `sldb-ui` — **INTERACTION** (Astro projection/navigation over store).
- `sldb-refactor-worktree` — **HARNESS / MIND** (architecture planning toward a graph kernel; no runtime).
- `marcado` (core) — **DATA / MIND** (semantic ASG over prose; typed marker taxonomy).
- `marcado-ui` — **INTERACTION** (React editor/viewer projecting marcado runtime).

## 3. Descriptive index (the core deliverable)

### sldb (`/home/jp/proyectos/hum-ecosystem/tools/sldb`)
- `/home/jp/proyectos/hum-ecosystem/tools/sldb/README.md` — full CLI + store + reversible-marker doc. maturity: **working**. Primary orientation doc.
- `/home/jp/proyectos/hum-ecosystem/tools/sldb/.pi/skills/use-sldb/SKILL.md` — Pi skill: when/how to use SLDB, core boundary (SLDB owns model contracts, reversible templates, render/extract, tracking, field mutation, store; does NOT own workflow logic). maturity: **working**.
- `/home/jp/proyectos/hum-ecosystem/tools/sldb/src/sldb/models/structured_doc.py` — `StructuredNLDoc` base class (Pydantic). Defines `__template__`, `__compositions__`, enforces non-empty field descriptions, render/compose payloads. maturity: **working**. Core model file.
- `/home/jp/proyectos/hum-ecosystem/tools/sldb/src/sldb/core/template_extractor.py` — compiles deterministic "search recipes" from template nodes; recognizes reversible `⸢...⸥` markers, enforces single canonical `rev` marker per field. maturity: **working**.
- `/home/jp/proyectos/hum-ecosystem/tools/sldb/src/sldb/core/data_extractor.py` — extracts field values from a document AST using recipes (Markdown → Pydantic payload).
- `/home/jp/proyectos/hum-ecosystem/tools/sldb/src/sldb/core/renderer.py` — `SLDBRenderer`: renders a `StructuredNLDoc` back to Markdown from `__template__` (reverse direction; strict round-trip). maturity: **working**.
- `/home/jp/proyectos/hum-ecosystem/tools/sldb/src/sldb/core/node.py` — `SLDBNode` dataclass: library-agnostic AST node (type/tag/content/children/metadata/map).
- `/home/jp/proyectos/hum-ecosystem/tools/sldb/src/sldb/core/ast/` — `base_ast_handler.py`, `markdown_ast_handler.py` (markdown-it-py wrapper → `SLDBNode`).
- `/home/jp/proyectos/hum-ecosystem/tools/sldb/src/sldb/core/ir/` — richer IR layer: `document_ir.py` (`DocumentIR`: context/structure/nodes/surface/graph/context_index), `meaning_node.py` (`MeaningNode` semantic node w/ owning_section + span), `surface_node.py`, `graph_view.py`/`graph_edge.py`, `section_context_entry.py`, `source_span.py`, `document_context.py`. maturity: **proto→working**. This is the graph-export substrate.
- `/home/jp/proyectos/hum-ecosystem/tools/sldb/src/sldb/core/handlers/` + `renderer_engine/` — per-block-type handlers/renderers (list, table, yaml, text).
- `/home/jp/proyectos/hum-ecosystem/tools/sldb/src/sldb/store/` — `.sldb` pointer database; 3-level YAML index cascade with 4-hash Merkle chain (`stores check` integrity). maturity: **working**.
- `/home/jp/proyectos/hum-ecosystem/tools/sldb/src/sldb/cli/` — graph-first CLI (`stores`/`models`/`docs`/`fields`/`sections`/`find`/`ast`).
- `/home/jp/proyectos/hum-ecosystem/tools/sldb/src/sldb/links/`, `runtime/`, `templates/`, `examples/` — link recovery/composition, validation runtime, template bootstrapping, example bundle.
- `/home/jp/proyectos/hum-ecosystem/tools/sldb/*.spec.yaml` (`sldb_architecture.spec.yaml`, `sldb_extraction_flow.spec.yaml`, `sldb_store_cascade.spec.yaml`, `sldb.spec.yml`) — specYaml contracts describing architecture/flows. maturity: **working**.

### sldb-ui (`/home/jp/proyectos/hum-ecosystem/tools/sldb-ui`)
- `package.json` — Astro 7 + React 19 + Node adapter; scripts dev/build/check/test(vitest).
- `src/pages/` — routes: `docs/`, `models/`, `fields/`, `sections.astro`, `ast/`, `links/`, `store/`, `search/`, `inbox/`, `transform/`, `api/`. Server-rendered projection of the SLDB store.
- `src/components/`, `src/lib/`, `src/layouts/`, `src/styles/` — UI building blocks. maturity: **proto/working** (v0.0.1).

### sldb-refactor-worktree (`/home/jp/proyectos/hum-ecosystem/tools/sldb-refactor-worktree`)
- `README.md` — target direction: **Clojure-owned kernel**, immutable revisioned graph as canonical persistence; canonical AST stays the structural substrate; links/anchors/relations/transactions/provenance are kernel concerns; Python only an orchestration adapter; strict render equality for reversible doc families. maturity: **idea/plan**.
- Priority docs: `also_core.md`, `core_README.md`, `diagramas_core.md`, `interfaces.md`, `libraries_core.md`, `plan_core.md`, plus `docs/architecture/`, `desk/atoms/`, `subagent/`. No runtime code (removed; lives in git history).

### marcado (`/home/jp/proyectos/hum-ecosystem/tools/marcado`)
- `README.md` — Semantic Markdown ASG MVP goal (YAML frontmatter + body + HTML-comment milestone markers → canonical ASG JSON + validation + anchors). maturity: **proto**.
- `semantic_markdown_asg_spec.md` — full format spec (Draft 0.1): purpose, design, marker grammar, namespaces, projections. Canonical model = ASG, not a single AST. maturity: **spec/working**.
- `src/marcado/markers.py` — `tokenize_markers`: parses `<!-- namespace:classification.path -->` (and closing `/`) HTML-comment markers into `MarkerToken`s + diagnostics + plain text with markers stripped. maturity: **working**.
- `src/marcado/model.py` — `Diagnostic`, `MarkerToken` (namespace/classification/facets/is_closing/offsets, `.key`), `ParsedDocument` (source/body/plain_text/frontmatter/tokens/logical_ranges/diagnostics).
- `src/marcado/ranges.py` — `LogicalRange`/`LogicalPosition`; matches open/close tokens into addressable ranges over plain text, offset-mapping around markers. maturity: **working**.
- `src/marcado/anchors.py` — `AnchorReference`/`RetrievalResult`; local `#namespace:classification.path`, qualified `asg://docs/<id>#key`, remote/shorthand anchors; unique-anchor resolution + repository loader. maturity: **working**.
- `src/marcado/{frontmatter,parser,validation,export,repository,cli}.py` — frontmatter parse, orchestration, syntax/graph validation, canonical JSON export, filesystem-backed remote doc loader, CLI.
- `schema/canonical.schema.json`, `examples/minimal-asg.md`, `docs/cli.md` — export schema, runnable example, CLI docs.

### marcado-ui (`/home/jp/proyectos/hum-ecosystem/tools/marcado-ui`)
- `package.json` — `@marcado/ui`; Vite 7 + React 18 + Tailwind 4 + react-markdown/remark-gfm/rehype-raw; playwright e2e; `scripts/sync-marcado-runtime.mjs` syncs the marcado runtime.
- `src/types.ts` — `Frontmatter`, `Document`, `Annotation` (selectedText + start/end offsets + note) — the editor's annotation model.
- `src/lib/marcado.ts` / `marcado-runtime.ts` / `marcado-adapter.ts` / `workspace-state.ts` — TS mirror of marcado parse (`MarkerRange`, `GraphEdge`, `NamespaceInfo`, `RuntimeExportMarkerToken/Range/Document`), runtime vs fallback mode, workspace state.
- `src/components/` — `document-workspace.tsx`, `DocumentViewer.tsx`, `DocumentSidebar.tsx`, `AnnotationPopup.tsx`, `AnnotationsList.tsx`, `workspace-navigator.tsx`, `workspace-shell.tsx`.
- `src/{hooks,data,utils,__tests__}/` — hooks, sample data, helpers, tests. maturity: **proto/working**.

## 4. Typed-language angle
Concrete typed-schema / marker / IR artifacts:
- **Reversible typed markers (sldb):** `⸢rev•field⸥` template syntax; parsed in `/home/jp/proyectos/hum-ecosystem/tools/sldb/src/sldb/core/template_extractor.py` (single canonical `rev` per field enforced). Typed fields via Pydantic `Field(description=...)` on `StructuredNLDoc` subclasses — mandatory descriptions are the human/LLM contract.
- **StructuredNLDoc contract:** `/home/jp/proyectos/hum-ecosystem/tools/sldb/src/sldb/models/structured_doc.py` — `__template__` (surface grammar) + `__compositions__` (render-time child-doc expansion) + typed fields.
- **Semantic IR / graph:** `/home/jp/proyectos/hum-ecosystem/tools/sldb/src/sldb/core/ir/document_ir.py` + `meaning_node.py` + `graph_view.py`/`graph_edge.py` — meaning nodes, source spans, section context, graph edges; feeds `sldb stores semantic-export --format kgdb`.
- **Marker grammar (marcado):** `namespace:classification(.segment)*(|facet)*` regexes in `/home/jp/proyectos/hum-ecosystem/tools/marcado/src/marcado/markers.py` and `anchors.py`; `MarkerToken.facets` is the typed classification tuple.
- **ASG spec + JSON schema:** `/home/jp/proyectos/hum-ecosystem/tools/marcado/semantic_markdown_asg_spec.md` and `/home/jp/proyectos/hum-ecosystem/tools/marcado/schema/canonical.schema.json` — the interchange type definition.
- **specYaml contracts:** `/home/jp/proyectos/hum-ecosystem/tools/sldb/sldb_*.spec.yaml` — architecture/flow/cascade contracts.
- **TS type mirror:** `/home/jp/proyectos/hum-ecosystem/tools/marcado-ui/src/lib/marcado-runtime.ts` (`RuntimeExportMarkerToken/Range/Document`) + `src/types.ts`.

## 5. Stealable / reusable for a knowledge agent's interaction layer
- **Reversible Markdown-as-data round-trip.** SLDB's extract⇄render with strict equality lets an agent read a doc as typed fields, mutate one field, and write back without disturbing prose. Cite: `structured_doc.py`, `renderer.py`, `template_extractor.py`, `data_extractor.py`. This is the strongest reusable primitive for an interaction layer that both reads and edits human docs.
- **Typed field contracts with mandatory descriptions** as LLM cues — `StructuredNLDoc.__pydantic_init_subclass__` enforcement in `structured_doc.py`. Directly reusable pattern for schema-guided generation.
- **`.sldb` pointer store + 4-hash Merkle cascade** (README "Store System") — decouples physical file location from logical model identity; benign-vs-real-change detection (hash_c text vs hash_d values). Reusable for change-aware agent memory.
- **Field-level + section-aware CRUD CLI surface** (`sldb fields query/show/update/append/clean`, `sldb sections fields`) — an agent-friendly addressing scheme `docs/<doc>/<field>` and semantic vs physical search (`--in semantic|physical|both`). Cite SKILL.md "Search modes".
- **Semantic export handoff** (`sldb stores semantic-export --format kgdb`) + `core/ir/*` — ready-made bridge from documents to a knowledge graph.
- **marcado overlay markers over unmodified prose** — HTML-comment milestone markers (`markers.py`) allow multiple coexisting semantic structures over the same text without altering the readable body; addressable ranges + stable anchors (`asg://docs/<id>#ns:class.path`) in `anchors.py`. Reusable as an annotation/citation addressing layer for an agent.
- **Anchor addressing scheme** (`anchors.py`: local/qualified/remote/shorthand + uniqueness enforcement) — a clean design for stable cross-document references an agent can cite.
- **Clean SKILL.md boundary doc** — `/home/jp/proyectos/hum-ecosystem/tools/sldb/.pi/skills/use-sldb/SKILL.md` is a model for how to expose a data layer to an agent (owns vs not-owns, anti-patterns, validation-first).
- **Kernel direction** (refactor-worktree README): immutable revisioned graph + AST substrate + adapters — worth reading before designing an agent's persistence.

## 6. Open questions / gaps
- Refactor-worktree is idea-stage (Clojure kernel); unclear how much of current Python `sldb` survives — risk when building on internal APIs vs CLI.
- Two parallel marker syntaxes: SLDB's `⸢rev•field⸥` (field-value extraction) vs marcado's `<!-- ns:class -->` (prose-range semantics). Their relationship/convergence is not documented here; both are "marcado" in spirit but separate codebases.
- marcado remote-anchor resolution is partly deferred ("MVP slice", `anchor_remote_resolution_deferred` in `anchors.py`).
- `sldb-ui` and `marcado-ui` runtime coupling (how UI reads the Python store / synced runtime) not fully traced — `marcado-ui/scripts/sync-marcado-runtime.mjs` suggests a build-time sync; sldb-ui `src/pages/api/` suggests a server bridge.
- ASG spec is Draft 0.1; canonical JSON schema stability unverified.

---

## Acceptance report

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Recon-only task: produced standardized recon index at /home/jp/proyectos/gemini_test/review/parts/03-sldb-marcado.md following TEMPLATE.md exactly, covering all five named dirs; no source code modified, UI node_modules/build not read."
    }
  ],
  "changedFiles": [
    "review/parts/03-sldb-marcado.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [],
  "validationOutput": [
    "Read: sldb README, SKILL.md, structured_doc.py, template_extractor.py, renderer.py, node.py, core/ir/document_ir.py, meaning_node.py; marcado README, model.py, markers.py, ranges.py, anchors.py, spec; sldb-ui + marcado-ui package.json + src/ top-level only."
  ],
  "residualRisks": [
    "Relationship/convergence between sldb marker syntax and marcado marker syntax not fully resolved from files read.",
    "UI-to-datalayer runtime coupling only inferred from directory names, not read in depth."
  ],
  "noStagedFiles": true,
  "diffSummary": "Added recon index file 03-sldb-marcado.md; no code changes.",
  "reviewFindings": [
    "no blockers"
  ],
  "manualNotes": "Followed output-path override and UI read restrictions (package.json/README/src top-level only). sldb-refactor-worktree is plan-stage (Clojure kernel), no runtime read."
}
```
