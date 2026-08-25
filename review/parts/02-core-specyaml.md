# Recon index: hum-ecosystem/core (specYaml + code2spec + turn_extractor + knowledge)

## 0. One-line purpose
`core/` is the semantic substrate of the hum-ecosystem: it defines `specYaml` (a typed, Pydantic-backed spec/document language), the machinery to project code into it (`code2specyaml`), a conversation→structure extractor (`turn_extractor`), and a queryable/materializable `knowledge` organ.

## 1. Repos / dirs covered
- `/home/jp/proyectos/hum-ecosystem/core/specyaml` — canonical typed spec format + Python runtime (Pydantic models + JSON Schema).
- `/home/jp/proyectos/hum-ecosystem/core/code2specyaml` — code→spec mapper (Tree-sitter/AST → Normalized IR → specYaml) + structural legibility linter.
- `/home/jp/proyectos/hum-ecosystem/core/turn_extractor` — parse opencode/notebook/html sessions into typed turn structures (conversation → structure).
- `/home/jp/proyectos/hum-ecosystem/core/knowledge` — formal, queryable, materializable knowledge substrate (SLDB-style YAML+Markdown atoms).
- `/home/jp/proyectos/hum-ecosystem/core/knowledge_tests` — semantic-layering test fixtures (S/M/G Tractarian model of meaning).

## 2. Layer classification
- MIND: `/home/jp/proyectos/hum-ecosystem/core/specyaml` (typed-language substrate, the canonical schema).
- MIND: `/home/jp/proyectos/hum-ecosystem/core/knowledge` (ontology/knowledge organ; selfdocs/protocols/contracts).
- MIND/HARNESS: `/home/jp/proyectos/hum-ecosystem/core/code2specyaml` (extractor + mapper + linter; IR pipeline).
- OTHER (tooling/ETL): `/home/jp/proyectos/hum-ecosystem/core/turn_extractor` (conversation→structure ingest).
- MIND (theory fixtures): `/home/jp/proyectos/hum-ecosystem/core/knowledge_tests` (semantic-typing test cases).

## 3. Descriptive index (the core deliverable)

### specyaml (typed spec language) — working runtime, specified contracts
- `/home/jp/proyectos/hum-ecosystem/core/specyaml/README.md` — role: canonical semantic layer shared by code2specyaml, sldb, spec2viz, specStyleLinter. Runtime API `load_document(path)`, `json_schema()`. (working)
- `/home/jp/proyectos/hum-ecosystem/core/specyaml/src/specyaml/models.py` — **the type system**: full Pydantic model suite for `SpecificationDocument` and all sections. (working)
- `/home/jp/proyectos/hum-ecosystem/core/specyaml/src/specyaml/io.py` — YAML→model boundary (`load_document`) and `json_schema()` derived from Pydantic. (working)
- `/home/jp/proyectos/hum-ecosystem/core/specyaml/src/specyaml/__init__.py` — exports `SpecificationDocument`, `load_document`, `json_schema`.
- `/home/jp/proyectos/hum-ecosystem/core/specyaml/MACHINE_CONTRACT.md` — normative typed-boundary contract; enumerates the required core model families and profile-extension rules. (spec)
- `/home/jp/proyectos/hum-ecosystem/core/specyaml/SPEC.md` — normative summary: core sections, extension/anchor/coverage/lint/machine rules. (spec)
- `/home/jp/proyectos/hum-ecosystem/core/specyaml/FORMAT.md` — canonical document contract (proto/spec).
- `/home/jp/proyectos/hum-ecosystem/core/specyaml/PROFILES.md` — profile & extension system.
- `/home/jp/proyectos/hum-ecosystem/core/specyaml/ANCHORS.md` — anchor, evidence, coverage, composition rules.
- `/home/jp/proyectos/hum-ecosystem/core/specyaml/RENDERERS.md` — downstream renderer boundary rules.
- `/home/jp/proyectos/hum-ecosystem/core/specyaml/LINT.md` — deterministic conformance/style rules.
- `/home/jp/proyectos/hum-ecosystem/core/specyaml/SLDB_PROFILE.md` — mapping of SLDB docs into specYaml.
- `/home/jp/proyectos/hum-ecosystem/core/specyaml/VERIFICATION.md` — example bundle + verification matrix.
- `/home/jp/proyectos/hum-ecosystem/core/specyaml/WHITEPAPER.md` — product position/rationale.
- `/home/jp/proyectos/hum-ecosystem/core/specyaml/core.spec.yml` — canonical core example document (the reference instance).
- `/home/jp/proyectos/hum-ecosystem/core/specyaml/examples/`, `.../tests/`, `.../desk/`, `.../pyproject.toml` — fixtures, tests, workflow desk, packaging.
- `/home/jp/proyectos/hum-ecosystem/core/specyaml/IEEE-1016-2009.pdf` — reference standard (software design descriptions).

### code2specyaml (code<->spec transform) — proto→working
- `/home/jp/proyectos/hum-ecosystem/core/code2specyaml/WHITEPAPER.md` — pipeline thesis: Extract (Tree-sitter) → Normalize (IR) → Map (specYaml) → Review → Lint (Structural Legibility / "Mapping Resistance"). (spec)
- `/home/jp/proyectos/hum-ecosystem/core/code2specyaml/MAPPING_CONTRACT.md` — **IR schema** (`CodeEntity`, `CodeRelation`) and formal IR→specYaml mapping tables. (spec)
- `/home/jp/proyectos/hum-ecosystem/core/code2specyaml/extract_ast.py` — working prototype: Python `ast`-based extractor emitting specYaml (`elements`/`relations`) for the sldb repo. (proto/working)
- `/home/jp/proyectos/hum-ecosystem/core/code2specyaml/EXTRACTION_CONTRACT.md`, `LINT_CONTRACT.md`, `OUTPUT_CONTRACT.md`, `ROUNDTRIP_EXPECTATIONS.md`, `SPEC.md` — contract docs for each pipeline stage. (spec)
- `/home/jp/proyectos/hum-ecosystem/core/code2specyaml/code2specyaml.spec.yml` — self-describing specYaml doc for this project.
- `/home/jp/proyectos/hum-ecosystem/core/code2specyaml/tests/`, `.../desk/` — tests + workflow desk.

### turn_extractor (conversation → structure) — proto
- `/home/jp/proyectos/hum-ecosystem/core/turn_extractor/extract_session_turns.py` — parses opencode `session-ses_*.md` into typed dataclasses (`SessionMetadata`, `UserTurn`, `AssistantTurn`, `ToolCall`); writes per-turn JSON+MD + index. (proto)
- `/home/jp/proyectos/hum-ecosystem/core/turn_extractor/extract_notebook_turns.py`, `extract_html_turns.py`, `debug_notebook_html.py`, `inspect_panel.py` — variant extractors for notebook/html conversation sources. (proto)
- `/home/jp/proyectos/hum-ecosystem/core/turn_extractor/init_index.py` — index bootstrap.
- `/home/jp/proyectos/hum-ecosystem/core/turn_extractor/raw_specs/turns_session/` — extracted turn outputs.
- `/home/jp/proyectos/hum-ecosystem/core/turn_extractor/Notebook/`, `.../desk/` — inputs + workflow desk.

### knowledge (the knowledge module) — bootstrapped/proto
- `/home/jp/proyectos/hum-ecosystem/core/knowledge/README.md` — organ index; zones = selfdocs/protocols/rituals/contracts/procedures/query/materialization; principles: determinization, queryability (SLDB structure = YAML frontmatter + Markdown). (spec)
- `/home/jp/proyectos/hum-ecosystem/core/knowledge/selfdocs/` — identity docs (`WhatAmI/WhoAmI/WhyAmI/WhereAmI/WhenAmI/HowAmI.md`, `looting_protocol.md`, `concepts/`). Descriptive. (proto)
- `/home/jp/proyectos/hum-ecosystem/core/knowledge/protocols/` — 30+ normative rule docs (auditor, gates, tasks_lifecycle, document_topology, contracts, zones, trails...). (bootstrapped)
- `/home/jp/proyectos/hum-ecosystem/core/knowledge/rituals/` — same doc set as protocols (behavioral sequences). (bootstrapped)
- `/home/jp/proyectos/hum-ecosystem/core/knowledge/procedures/ingest_raw.yaml` — procedural IR: node identity + ordered `steps` + typed inputs/outputs (recipe format). (proto)
- `/home/jp/proyectos/hum-ecosystem/core/knowledge/query/glossary.yaml` — domain ontology terms (`KnowledgeNode`, `KnowledgeGraph`, `Edge`, `Facet`, `Transclusion`, `TopologyProposal`...). (bootstrapped)
- `/home/jp/proyectos/hum-ecosystem/core/knowledge/contracts/` (empty), `.../materialization/` (empty) — declared, not yet populated. (idea)

### knowledge_tests (semantic-typing fixtures) — idea/proto
- `/home/jp/proyectos/hum-ecosystem/core/knowledge_tests/test_001_onion_sofrito.yaml` — S(surface)/M(logical form)/G(world projection) layering; Tractarian `sinn` classification, well_typed/grounded/projectable.
- `/home/jp/proyectos/hum-ecosystem/core/knowledge_tests/test_003_mapping_and_typing.yaml` — same sign resolves to different concept/role by `doc_type` (recipe vs history); S as a typing "lens".
- `.../test_002_context_comparison.yaml`, `.../test_004_systemic_emergence_pizza.yaml` — further semantic-layer experiments.

## 4. Typed-language angle
specYaml is the typed language. Concrete type-defining artifacts:

- **`/home/jp/proyectos/hum-ecosystem/core/specyaml/src/specyaml/models.py`** — the executable type system. Root type `SpecificationDocument` (extra="forbid") with required sections: `apiVersion`, `kind`, `metadata` (`DocumentMetadata`), `document` (`DocumentSection` = purpose/scope/glossary/references), `profiles` (`ProfileDeclaration`), `extensions` (`ExtensionsSection` w/ `ExtensionPolicy`), `semantics` (`SemanticsSection` = `SemanticElement[]` + `SemanticRelation[]`), `constraints`, `anchors` (`AnchorsSection`: kinds/fields), `coverage` (`CoverageSection`: model + `CoverageLink[]`), `evidence`, `renderers` (`RendererLayer[]`), `lint` (`LintPolicy`), `machineContract`.
  - Typed identity: `SemanticElement{id,kind,label,description,anchors[],attributes,constraints,evidence[]}`; `SemanticRelation{from,to,relation,label,anchors[],evidence[],confidence}`.
  - Provenance types: `AnchorEntry{kind,path,symbol,startLine,endLine,provenance,confidence,recipeId,evidenceKind}` and `EvidenceEntry{type,anchor,note}`.
  - Type-boundary policy encoded via `ConfigDict(extra="forbid")` on core sections vs `extra="allow"` on extension-bearing sections (`SemanticElement`, `SemanticRelation`, `ExtensionsSection`, `ConstraintsSection`, `RenderersSection`). Aliases (`in`, `from`) map YAML keywords to Python fields.
- **`/home/jp/proyectos/hum-ecosystem/core/specyaml/src/specyaml/io.py`** — `json_schema()` = `SpecificationDocument.model_json_schema()`; grammar/schema is derived, not hand-written.
- **`/home/jp/proyectos/hum-ecosystem/core/specyaml/MACHINE_CONTRACT.md`** — normative list of required model families + typed-boundary rules ("YAML must be parsed into typed models before semantic consumers operate"; reject undeclared unknown fields; endpoints must be validated references, not prose).
- **`/home/jp/proyectos/hum-ecosystem/core/code2specyaml/MAPPING_CONTRACT.md`** — the intermediate IR type grammar (`CodeEntity`, `CodeRelation` with kinds `defines/imports/inherits/calls/references`) and the IR→specYaml relation renaming table.
- **`/home/jp/proyectos/hum-ecosystem/core/knowledge_tests/*.yaml`** — a second, theoretical typing model: S/M/G layers with `well_typed`, `grounded`, `sinn` (Tractarian sense) — meaning-as-typing where `doc_type` selects interpretation.
- **`/home/jp/proyectos/hum-ecosystem/core/knowledge/query/glossary.yaml`** — the ontology/vocabulary layer (KnowledgeNode/Edge/Facet/Transclusion).
- **`/home/jp/proyectos/hum-ecosystem/core/knowledge/procedures/ingest_raw.yaml`** — procedural IR shape (identity + steps + typed I/O).

## 5. Stealable / reusable for a knowledge agent
- **Pydantic-first typed document core** at `.../specyaml/src/specyaml/models.py` — directly reusable as the schema/validation layer for a typed knowledge agent; gives free JSON Schema via `json_schema()`. The `extra="forbid"` (core) vs `extra="allow"` (extension namespaces) pattern is a clean way to enforce a stable core while allowing profile growth.
- **Provenance/evidence/confidence model** (`AnchorEntry` + `EvidenceEntry`) — reusable anchoring convention: every generated node/edge answers where/how-certain/what-recipe. See `.../MACHINE_CONTRACT.md` §6 and `.../MAPPING_CONTRACT.md` §3.
- **IR → canonical-doc mapping table** (`.../code2specyaml/MAPPING_CONTRACT.md`) — reusable blueprint for turning any extracted fact graph into anchored semantic elements/relations; relation-kind renaming (`defines`→`contains`) is a nice normalization pattern.
- **Working AST extractor** (`.../code2specyaml/extract_ast.py`) — small, copyable Python `ast` walker producing `elements`/`relations` specYaml; good starting point for code-graph ingestion (note: it uses `source/target/kind` keys, not yet the canonical `from/to/relation` of models.py — a real roundtrip gap).
- **Typed conversation extractor** (`.../turn_extractor/extract_session_turns.py`) — dataclass model (`SessionMetadata`/`UserTurn`/`AssistantTurn`/`ToolCall`) + regex splitter for chat/tool logs; reusable for turning agent transcripts into structured, queryable turns (conversation→structure).
- **S/M/G semantic-layer model** (`.../knowledge_tests/`) — a principled separation of surface text, logical form, and world-projection with typing predicates (well_typed/grounded/projectable); reusable mental model for a meaning-typing pipeline.
- **Knowledge organ topology** (`.../knowledge/README.md`): selfdocs/protocols/rituals/contracts/procedures/query/materialization with Descriptive/Normative/Procedural/Formal classes + SLDB YAML-frontmatter+Markdown atom convention (node_id/node_type/facet/edges) — reusable structure for organizing an agent's knowledge base.

## 6. Open questions / gaps
- **Roundtrip mismatch**: `extract_ast.py` emits `apiVersion: specyaml/v0alpha1` with relations keyed `source/target/kind` and no `document/profiles/extensions/...` sections, so its output would fail `SpecificationDocument.model_validate` (which requires all core sections and uses `from/to/relation`). MAPPING_CONTRACT §5 says output MUST validate against `models.py` — currently unmet by the prototype.
- `knowledge/contracts/` and `knowledge/materialization/` are empty despite README marking them "ready for migration"; the query surface is only a static `glossary.yaml` (no executable query engine present here).
- No explicit link found from `turn_extractor` output into specYaml or knowledge atoms — conversation→structure stops at per-turn JSON/MD; integration path is undefined.
- The two typed models (Pydantic `specYaml` vs Tractarian S/M/G in `knowledge_tests`) are not reconciled — unclear whether S/M/G is meant to become a specYaml profile.
- specYaml runtime is minimal: only `load_document` + `json_schema`; no writer, no profile-loading, no lint execution in code (LINT.md is spec-only).

## Start Here
Open `/home/jp/proyectos/hum-ecosystem/core/specyaml/src/specyaml/models.py` — it is the concrete, executable definition of the typed spec language everything else maps to; then `/home/jp/proyectos/hum-ecosystem/core/code2specyaml/MAPPING_CONTRACT.md` for the code↔spec transform contract.

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Recon-only task; produced standardized index at review/parts/02-core-specyaml.md following TEMPLATE.md sections 0-6 plus required Start Here, covering exactly the 5 assigned subdirs. No source files in scope were modified."
    }
  ],
  "changedFiles": [
    "review/parts/02-core-specyaml.md",
    ".pi/agent/sessions/--home-jp-proyectos-gemini_test--/subagent-artifacts/progress/f9a1271b/progress.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [
    {
      "command": "ls/read/grep over core subdirs",
      "result": "passed",
      "summary": "Read READMEs, contracts, and top-level source for specyaml, code2specyaml, turn_extractor, knowledge, knowledge_tests"
    }
  ],
  "validationOutput": [
    "specyaml/src/specyaml/models.py defines SpecificationDocument Pydantic suite (verified by read)",
    "code2specyaml/MAPPING_CONTRACT.md defines CodeEntity/CodeRelation IR and IR->specYaml mapping (verified by read)"
  ],
  "residualRisks": [
    "Deep-dive omitted for FORMAT.md/PROFILES.md/ANCHORS.md and core.spec.yml bodies (listed but not fully read) due to breadth-over-depth mandate"
  ],
  "noStagedFiles": true,
  "diffSummary": "Added recon index markdown and progress note; no code changes.",
  "reviewFindings": [
    "no blockers",
    "note: extract_ast.py output does not validate against specyaml models.py (roundtrip gap) - flagged in section 6"
  ],
  "manualNotes": "specYaml is the typed language (Pydantic-backed, JSON-Schema-derivable). A second typing model (S/M/G Tractarian) lives in knowledge_tests and is not yet reconciled with specYaml."
}
```
