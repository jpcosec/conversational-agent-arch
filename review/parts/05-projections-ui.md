# Recon index: PROJECTION / UI + Scraping tools

## 0. One-line purpose
The INTERACTION + ingestion layer of hum-ecosystem: how a typed knowledge base gets projected/visualized (`graph_ui`, `spec2viz`), scraped/ingested (`hum-scrapper`), and packaged from repos into typed, composable context (`repopackage`).

## 1. Repos / dirs covered
- `/home/jp/proyectos/hum-ecosystem/tools/graph_ui` — domain-agnostic visual graph editor (React/TS) + reconstruction spec docs.
- `/home/jp/proyectos/hum-ecosystem/tools/spec2viz` — semantic YAML → IR → diagram/HTML rendering (Python).
- `/home/jp/proyectos/hum-ecosystem/tools/hum-scrapper` — LangGraph browser-automation scraper with a persistent semantic "Labyrinth" portal atlas (Python).
- `/home/jp/proyectos/hum-ecosystem/tools/repopackage` — recursive, contract-based repo composition / context packaging (Python).

## 2. Layer classification
- **INTERACTION** — `graph_ui` (visual graph editor/projection), `spec2viz` (human-watchable rendering over specYaml semantics).
- **DATA / INGESTION** — `hum-scrapper` (ingests portal knowledge into a persistent semantic layer; DATA-adjacent).
- **HARNESS / MIND-adjacent** — `repopackage` (typed integration contracts, dependency graph resolution, context materialization).

## 3. Descriptive index (the core deliverable)

### graph_ui  (React 18 + Vite + TypeScript, @xyflow/react)
Docs (reconstruction spec, no code) at repo root:
- `/home/jp/proyectos/hum-ecosystem/tools/graph_ui/README.md` — overview; two worktrees (`ui-redesign` monolith vs `node-editor` 3-layer refactor) to be merged. working.
- `/home/jp/proyectos/hum-ecosystem/tools/graph_ui/spec.md` — full product+architecture spec (Match / CV / KnowledgeGraph domains, L1/L2/L3 layering). working (spec).
- `/home/jp/proyectos/hum-ecosystem/tools/graph_ui/reconstruction.md`, `sources.md`, `pitfalls.md` — rebuild guide, source map, pitfalls. docs.
- Python `src/` (`editor.py`, `auditor.py`, `provider.py`, `adapters/`, `contracts/`) — a separate small Python surface (sldb-integrated editor/auditor); proto.

App: `/home/jp/proyectos/hum-ecosystem/tools/graph_ui/apps/review-workbench`
- `package.json` — deps reveal the stack: `@xyflow/react` (React Flow) canvas, `@dagrejs/dagre` + `elkjs` layout, `zustand` store, `zod` schemas, `@tanstack/react-query`, Radix UI, Tailwind. working.
- `src/schema/registry.ts` + `registry.types.ts` — **NodeTypeRegistry**: domain-agnostic type registry keyed by `typeId`, each with zod `payloadSchema`, renderers (dot/label/detail zoom levels), `allowedConnections`, color tokens. working. **Core reusable primitive.**
- `src/schema/register-defaults.ts`, `graph-validation.ts` — default node type registration + validation. working.
- `src/stores/graph-store.ts`, `ui-store.ts`, `types.ts` — zustand stores; `ASTNode`/`ASTEdge`/`SemanticAction`/`ValidatedAST` types; undo/redo via semantic actions (`isVisualOnly` flag). working.
- `src/features/graph-editor/L1-app/GraphEditorPage.tsx` — L1 application/translation layer.
- `src/features/graph-editor/L2-canvas/` — L2 canvas: `GraphEditor.tsx`, `GraphCanvas.tsx`, `NodeShell.tsx`, `GroupShell.tsx` (compound/collapsible groups), `edges/`, `layout/` (ELK web worker), `panels/` (NodeInspector, EdgeInspector), `sidebar/`, `encoding/encoding-rules.ts`. working.
- `src/features/graph-editor/lib/` — projection engine: `schema-to-graph.ts` (raw JSON+schema → validated AST with auto-layout), `graph-to-domain.ts` (AST → domain data, bidirectional), `data-provider.ts`, `projection-view-store.ts`, `types.ts`. working. **Most reusable for typed-KB projection.**
- `src/features/hum-body/` — **domain projection of a Lisp codebase as an anatomical/organism graph**: `HumBodyPage.tsx`, `lib/types.ts` (HumOrgan/HumCapability/HumArtifact/HumRoutine/HumTrace), `lib/adapter.ts` (build graph + register node types), `lib/generated-hum-ast.ts` (generated), `renderers.tsx`. 5 view modes: structure/body/routine/trace/compare. working. **Directly wikipedia/astro-like projection prototype.**
- `scripts/generate-hum-ast.mjs` — codegen: reads `../../../hum/*.lisp`, extracts top-level forms, emits `generated-hum-ast.ts`. **AST ingestion → projection pipeline.** working.
- `scripts/lint-architecture.mjs`, `run-user-flow.mjs`; `user_flows/`, `auto_user_test/` — architecture linting + Playwright user-flow tests.

### spec2viz  (Python; semantic YAML → IR → renderers)
- `spec2viz/loader.py`, `validator.py`, `models/` (`sequence.py`, `state.py`, `component.py`, `activity.py`, `deployment.py`, `matrix.py`, `reflection.py`, `catalog.py`, `base.py`) — Pydantic spec models per diagram type. working.
- `spec2viz/ir.py` — renderer-agnostic **IR dataclasses** (SequenceIR, StateIR, ComponentIR, ActivityIR, DeploymentIR, MatrixIR). working. **Clean spec→IR→render separation.**
- `spec2viz/compilers/` — one compiler per diagram type (spec → IR). working.
- `spec2viz/renderers/` — `plantuml.py`, `mermaid.py`, `d2.py`, `vega.py`, `tree.py`, `graph_html.py` (**pure-DOM collapsible hierarchical tree, zero-dependency, works from `file://`**), `antonia.py` (styled HTML shell around Mermaid). working. **graph_html + antonia = self-contained HTML projection.**
- `spec2viz/deskops.py` + `orchestrator.py` — **catalog builder**: aggregate diagram-stores + legacy `vistas.yml` into a single filterable architecture HTML bundle (nav, filter bar, sections, coverage). working. **Wikipedia/astro-like static site generation.**
- `spec2viz/generators/`, `linters/`, `schema.py`, `templates/`, `cli.py` — JSON-schema export, lint, HTML templates, CLI (`spec2viz diagram|catalog|schema`). working.
- `examples/`, `tests/fixtures/` — sample specs + rendered outputs.

### hum-scrapper  (Python; LangGraph Sense-Think-Act browser automation)
- `README.md` + `docs/automation/architecture.md` — 4-layer arch (contracts ← adapters ← ariadne ← langgraph). working.
- `src/automation/contracts/` — Layer 0 shared types: `sensor.py` (Sensor protocol + SnapshotResult), `motor.py` (Motor + MotorCommand + TraceEvent + ExecutionResult), `state.py` (AriadneState TypedDict), `topology.py` (Room/Stage/Schema/SchemaControl). working. **Typed contracts.**
- `src/automation/adapters/browser_os.py` — Crawl4AI → BrowserOS CDP adapter. working.
- `src/automation/ariadne/labyrinth/` — persistent portal atlas: `labyrinth.py` (Room atlas, identify/expand, dead-ends), `url_node.py`, `room_state.py`, `skeleton.py`. working. **Accumulated typed portal knowledge across runs.**
- `src/automation/ariadne/thread/` — mission transition graph (Action, AriadneThread).
- `src/automation/ariadne/extraction/` — `schema_builder.py` (**LLM generates recursive Container>Item>Field JSON-CSS extraction schema mirroring DOM topology**), `portal_dictionary.py`. working. **Typed extraction schema generation.**
- `src/automation/ariadne/` also: `extracted_store.py`, `compiled_mission.py`, `portal_registry.py`, `mission_ledger.py`, `capabilities/`.
- `src/automation/langgraph/nodes/` — `interpreter.py`, `observe.py`, `theseus.py`, `delphi.py`, `recorder.py` + `builder.py`. working.
- `spec_schema.json`, `generate_atomic_traceability.py`, `project_ast.json` — spec schema + traceability tooling.

### repopackage  (Python; recursive contract-based repo composition)
- `README.md` + `docs/ARCHITECTURE.md` — treats git repos as nodes in a typed recursive graph; typed integration contracts; zero-checkout peeking. working. 80/10 rule (80-line files / 10-line functions).
- `src/repopackage/core/models.py` — Pydantic domain models: `Schema`, `Traits`, `DependencySpec`, `CommandExport`, `ContractExport`, `ProcedureExport`, project model. working. **Typed contract/export surface.**
- `src/repopackage/core/solver.py`, `constants.py` — dependency graph resolution.
- `src/repopackage/git/` — git operations (zero-checkout contract peeking).
- `src/repopackage/repo/manifest.py` — generates Google-Repo XML manifest from lockfile + `rp sync` materialization. working.
- `src/repopackage/cli/` (`main.py`, `handlers.py`) — `rp init|resolve|sync|validate|status|generate|graph` (graph export to Mermaid/PlantUML). working.
- `contracts/`, `compose.yaml`, `compose.lock.yaml` — integration contracts + project/lock models.

## 4. Typed-language angle
Concrete typed artifacts:
- `graph_ui/apps/review-workbench/src/schema/registry.types.ts` — `NodeTypeDefinition` (typeId, zod `payloadSchema`, renderers, `allowedConnections`, colorToken) = a typed node ontology.
- `graph_ui/.../src/stores/types.ts` — `ASTNode`/`ASTEdge`/`SemanticAction`/`ValidatedAST` = typed graph IR with validation errors.
- `graph_ui/.../src/features/hum-body/lib/types.ts` — a full typed model of a codebase-as-organism (organs/capabilities/artifacts/routines/traces).
- `spec2viz/spec2viz/ir.py` — renderer-agnostic IR dataclasses; `spec2viz/models/*.py` Pydantic spec schemas; `schema.py`/`generators/` export JSON Schema.
- `hum-scrapper/src/automation/contracts/*.py` (sensor/motor/state/topology protocols + TypedDict) and `extraction/schema_builder.py` (recursive Container>Item>Field extraction schema mirroring DOM).
- `hum-scrapper/spec_schema.json`, `project_ast.json`.
- `repopackage/src/repopackage/core/models.py` — Pydantic contract/export/dependency models; `contracts/*.yaml` integration contracts.

## 5. Stealable / reusable for a knowledge agent (projections of a typed KB)
- **NodeTypeRegistry pattern** (`graph_ui/.../src/schema/registry.ts`): a domain-agnostic, zod-validated type registry with per-type renderers at multiple zoom levels (dot/label/detail) and `allowedConnections` connection rules — directly reusable to project any typed KB into an editable graph.
- **Schema→AST→Domain bidirectional projection** (`graph_ui/.../src/features/graph-editor/lib/schema-to-graph.ts` + `graph-to-domain.ts`): validated AST with auto-layout in, domain objects out. The core "project + edit + re-serialize" loop.
- **Multi-lens projection** (`graph_ui/.../src/features/hum-body/`): same underlying model rendered as 5 lenses (structure/body/routine/trace/compare) — the astro/wikipedia "same data, many views" pattern.
- **AST ingestion codegen** (`graph_ui/.../scripts/generate-hum-ast.mjs`): source → parsed forms → typed generated module feeding the UI.
- **spec → IR → renderer separation** (`spec2viz/ir.py` + `compilers/` + `renderers/`): clean pipeline; add a renderer without touching semantics. `renderers/graph_html.py` is a **zero-dependency, file://-safe collapsible HTML tree** — ideal for static, offline KB projections.
- **Catalog/static-site builder** (`spec2viz/deskops.py` + `orchestrator.py`): aggregates many diagram-stores into one filterable HTML bundle (nav + filter bar + sections + coverage) — a wikipedia-like static projection generator over a typed store.
- **Semantic accumulation across runs** (`hum-scrapper/.../ariadne/labyrinth/`): a persistent typed atlas that grows with each observation — model for an incrementally-built KB.
- **LLM-generated recursive extraction schema** (`hum-scrapper/.../extraction/schema_builder.py`): forces schema to mirror source topology (Container>Item>Field) — reusable for typed ingestion of unstructured sources.
- **Typed integration contracts + zero-checkout peeking + graph export** (`repopackage`): model for composing a KB from many typed repos and exporting the dependency graph as Mermaid/PlantUML.

## 6. Open questions / gaps
- `graph_ui` is mid-merge: `node-editor`'s L1/L2/L3 architecture vs `ui-redesign`'s full feature set — which worktree is authoritative here, and is `apps/review-workbench` the merged result or one branch? (`sources.md` explains the two worktrees.)
- `graph_ui/src/*.py` (editor/auditor/provider) is a parallel Python surface separate from the React app — unclear how/if the two integrate with sldb.
- `spec2viz` reads canonical `specYaml` upstream; the actual `specyaml/` source of semantic truth is outside this scope (referenced but not here).
- `hum-scrapper` depends on running BrowserOS + Crawl4AI + Gemini key; ingestion is portal/web-oriented, not yet wired to a typed KB target.
- `repopackage` requires Google `repo` tool for materialization; how contracts feed downstream type generation (`rp generate`) not inspected in depth.
- No single shared graph IR across `graph_ui` (TS ASTNode/ASTEdge) and `spec2viz` (Python IR dataclasses) — a unification opportunity for KB projections.

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Recon covers exactly the four requested dirs (graph_ui, spec2viz, hum-scrapper, repopackage); followed TEMPLATE.md sections 0-6; avoided node_modules/dist, read package.json/README/src top-level only for UI."
    }
  ],
  "changedFiles": [
    "review/parts/05-projections-ui.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [],
  "validationOutput": [
    "Recon index written to /home/jp/proyectos/gemini_test/review/parts/05-projections-ui.md following TEMPLATE.md structure exactly."
  ],
  "residualRisks": [
    "graph_ui two-worktree merge state ambiguous; did not deep-read every src file (breadth over depth as instructed)."
  ],
  "noStagedFiles": true,
  "diffSummary": "Added recon index for projection/UI + scraping tools.",
  "reviewFindings": [
    "no blockers"
  ],
  "manualNotes": "Explicit absolute paths used throughout. Key reusable primitives for typed-KB projections: NodeTypeRegistry (graph_ui), schema-to-graph/graph-to-domain projection loop, spec2viz IR->renderer + graph_html zero-dep HTML tree + deskops catalog builder, hum-scrapper Labyrinth atlas + recursive extraction schema, repopackage typed contracts."
}
```
