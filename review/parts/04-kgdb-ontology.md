# Recon index: GRAPH + ONTOLOGY tools (kgdb / ontology / ontomap / tractatusIR)

## 0. One-line purpose
Four candidate substrates for a MIND/typed-language layer: `kgdb` (deterministic graph persistence + typed query language), `ontology` (facet contracts + OWL reasoning/audit over a wiki), `ontomap` (6-dimensional RDF/OWL edge model with multi-format round-trip), and `tractatusIR` (a Tractarian propositional IR — concepts, dimensions, bit-signatures, grammar-of-sense).

## 1. Repos / dirs covered
- `/home/jp/proyectos/hum-ecosystem/tools/kgdb` — graph persistence, traversal, and typed structured-query substrate (NetworkX-backed, Pydantic contracts).
- `/home/jp/proyectos/hum-ecosystem/tools/ontology` — domain semantics: facet schemas, OWL reasoning backend, structural/energy audit, cleansing detection.
- `/home/jp/proyectos/hum-ecosystem/tools/ontomap` — multidimensional ontological graph over RDF/OWL; 6D reified edges; Mermaid/PlantUML/OWL round-trip.
- `/home/jp/proyectos/hum-ecosystem/tools/tractatusIR` — Tractatus-based intermediate representation (formal propositional model, bit-signatures, Common Lisp prototype `graphlang`).

## 2. Layer classification
- MIND (primary): `kgdb` typed contracts + query language; `ontology` facet contracts; `ontomap` 6D edge model + OWL core; `tractatusIR` propositional IR / typed-language substrate.
- DATA: `kgdb` persisted NetworkX graph JSON (`kgdb.graph.json`); ingest of SLDB semantic export (bulk handoff contract).
- INTERACTION: `ontomap/ontoviewer.html`, Mermaid/PlantUML/OWL-viz converters (visualization projections).
- HARNESS: `ontology` energy/structural/cleansing audits (drift + lifecycle gate feeders); `kgdb` validation API for downstream (deskops/hum/truth_machine).
- OTHER: `tractatusIR/lisp` prototype runtime; `tractatusIR/paper`, `atomos` doc corpus.

## 3. Descriptive index (the core deliverable)

### kgdb
- `/home/jp/proyectos/hum-ecosystem/tools/kgdb/README.md` — working; authoritative spec of the SLDB↔KGDB boundary, node/edge vocab, CLI, and ingest/query contracts.
- `/home/jp/proyectos/hum-ecosystem/tools/kgdb/src/kgdb/contracts/base.py` — working; `Edge`, `SystemIdentity`, `VocabularyTerm` (regex-constrained downstream vocabulary token). The minimal typed graph primitive.
- `/home/jp/proyectos/hum-ecosystem/tools/kgdb/src/kgdb/contracts/node.py` — working; `KnowledgeNode` (identity + edges + 8 named facet slots) and `FacetPayload` (extra-allowed, attribute-addressable, defaulting). Ontology-independent facet container.
- `/home/jp/proyectos/hum-ecosystem/tools/kgdb/src/kgdb/query/language.py` — working; `StructuredQuery`, `FacetFilter`, `FieldCondition`, `GraphScope`, `RelationFilter` — the declarative typed query DSL.
- `/home/jp/proyectos/hum-ecosystem/tools/kgdb/src/kgdb/query/executor.py`, `neighborhood.py`, `server.py` — working; query execution, neighborhood traversal, query server.
- `/home/jp/proyectos/hum-ecosystem/tools/kgdb/src/kgdb/ingest/sldb.py` — working; `sldb_semantic_export_to_snapshot` converts SLDB export → graph snapshot.
- `/home/jp/proyectos/hum-ecosystem/tools/kgdb/src/kgdb/graph/utils.py` — working; NetworkX serialization helpers.
- `/home/jp/proyectos/hum-ecosystem/tools/kgdb/src/kgdb/contracts/persistence.py`, `io.py` — working; graph bundle persistence + IO.
- `/home/jp/proyectos/hum-ecosystem/tools/kgdb/src/kgdb/main.py` — working; CLI `kgdb {get,list,query,edges,ingest,ingest-sldb}` (console_script `kgdb = kgdb.main:main`).
- `/home/jp/proyectos/hum-ecosystem/tools/kgdb/contracts/schemas/sldb_kgdb_semantic_export.schema.json` — working; the v1 ingest contract schema.
- `/home/jp/proyectos/hum-ecosystem/tools/kgdb/contracts/schemas/kgdb_graph_bundle.schema.json` — working; persisted graph bundle schema.
- `/home/jp/proyectos/hum-ecosystem/tools/kgdb/contracts/schemas/sldb_document_payload.schema.json` — working; SLDB document payload schema.
- `/home/jp/proyectos/hum-ecosystem/tools/kgdb/contracts/integration.contract.yaml` — working; declares `sldb_kgdb_semantic_export` v1 dependency.
- `/home/jp/proyectos/hum-ecosystem/tools/kgdb/contracts/queries/sldb/*.json` — working; 5 example structured queries (proofs of graph questions).
- `/home/jp/proyectos/hum-ecosystem/tools/kgdb/contracts/fixtures/sldb_kgdb_semantic_export.v1.json` — working; canonical fixture.

### ontology
- `/home/jp/proyectos/hum-ecosystem/tools/ontology/README.md` — thin; "Domain semantics, reasoning, facets, cleansing detection, and energy services extracted from wikipu."
- `/home/jp/proyectos/hum-ecosystem/tools/ontology/src/ontology/contracts/facets.py` — working; **the facet type catalog**: `IOFacet`, `ASTFacet`, `SemanticFacet`, `ADRFacet`, `TestMapFacet`, `ComplianceFacet`, `SourceFacet`, `GitFacet`. Strongly-typed dimensions of a knowledge node.
- `/home/jp/proyectos/hum-ecosystem/tools/ontology/src/ontology/contracts/` — working; also `wiki_nodes.py`, `energy.py`, `findings.py`, `proposals.py`, `audit_io.py`.
- `/home/jp/proyectos/hum-ecosystem/tools/ontology/src/ontology/facets/registry.py` — working; `FieldSpec`, `FacetSpec`, `InjectionContext`, `FacetRegistry`, `build_default_registry()` — facet schema registry + injection framework (`scanner.py`, `builder.py`, `injectors.py`, `validator.py`).
- `/home/jp/proyectos/hum-ecosystem/tools/ontology/src/ontology/reasoning/owl_backend/extractor.py` — working; `markdown_to_rdf()` extracts frontmatter/wikilinks → RDF triples (`WIKIPU` namespace, `KnowledgeNode` class). Also `export.py`, `frontmatter.py`, `wikilinks.py`, `annotations.py`, `import_export.py`.
- `/home/jp/proyectos/hum-ecosystem/tools/ontology/src/ontology/reasoning/structural.py` — working; `StructuralAuditor.audit_orphans/audit_redundancy`, `run_structural_audit`.
- `/home/jp/proyectos/hum-ecosystem/tools/ontology/src/ontology/reasoning/reasoner.py`, `auditor.py` — working; OWL reasoning + consistency/inference.
- `/home/jp/proyectos/hum-ecosystem/tools/ontology/src/ontology/energy/audit.py` — working; systemic-energy audit: FFT metrics, Jaccard redundancy, code/doc drift (`run_energy_audit`).
- `/home/jp/proyectos/hum-ecosystem/tools/ontology/src/ontology/cleansing/rules.py` — working; cleansing detection rules.
- `/home/jp/proyectos/hum-ecosystem/tools/ontology/src/ontology/validation/engine.py`, `artifacts.py` — working; facet-proposal validation.
- `/home/jp/proyectos/hum-ecosystem/tools/ontology/src/ontology/main.py` — working; CLI `ontology {energy,reason,cleanse-detect,validate-facet}` (console_script `ontology = ontology.main:main`).
- `/home/jp/proyectos/hum-ecosystem/tools/ontology/contracts/schemas/ontology_audit_result.schema.json`, `kgdb_graph_bundle.schema.json` — working; audit + shared graph-bundle schemas.

### ontomap
- `/home/jp/proyectos/hum-ecosystem/tools/ontomap/README.md` — working; full architecture doc of the multidimensional ontological graph.
- `/home/jp/proyectos/hum-ecosystem/tools/ontomap/spec.md` — working; conceptual spec (nodes, 6D edges, Pydantic/JSON schema).
- `/home/jp/proyectos/hum-ecosystem/tools/ontomap/ontology/core.ttl` — working; **OWL core**: `onto:Entity` + 4 disjoint subclasses (`Actor`/`Zone`/`Artifact`/`Process`), `OntologyEdge` reification, 6 dimension properties + concrete sub-properties with axioms (Transitive/Irreflexive/Asymmetric).
- `/home/jp/proyectos/hum-ecosystem/tools/ontomap/ontology/edge_model.py` — working; `CanonicalEdge6D` Pydantic model + `WHERE_PROPS`/`WHAT_PROPS` sub-property maps + `to_rdf()`/`to_ttl()` reification export.
- `/home/jp/proyectos/hum-ecosystem/tools/ontomap/ontology/projection.py` — working; `ProjectionFormat`, `LensType`, `ProjectionFilter`, `ProjectionConfig`, `ProjectedGraph` — typed projection/lens model.
- `/home/jp/proyectos/hum-ecosystem/tools/ontomap/ontology/workspace.ttl` / `example.ttl` — working; concrete instance graphs.
- `/home/jp/proyectos/hum-ecosystem/tools/ontomap/converters/{dims.py,mermaid.py,puml.py,owl_viz.py}` — working; dimension↔OWL mapping and Mermaid/PlantUML/OWL-viz load/dump (round-trip 36/36 edges).
- `/home/jp/proyectos/hum-ecosystem/tools/ontomap/queries/projections.sparql` — working; standard SPARQL projections (composition tree, dependency DAG, sequence flow, cycle check).
- `/home/jp/proyectos/hum-ecosystem/tools/ontomap/cli.py` — working; `python cli.py parse <input> <output>` with format auto-detect by extension.
- `/home/jp/proyectos/hum-ecosystem/tools/ontomap/ontoviewer.html` — proto; interactive viewer.

### tractatusIR
- `/home/jp/proyectos/hum-ecosystem/tools/tractatusIR/README.md` — NOTE: this root README describes the `graphlang` Lisp prototype, not the whole dir (misleading; actual IR lives in `atomos/`, `specs/`, `formal-propositional-model.md`).
- `/home/jp/proyectos/hum-ecosystem/tools/tractatusIR/formal-propositional-model.md` — proto/spec; **core IR grammar**: facts as typed atomic propositions (subject/predicate/object/context/logical_form/truth_status/masks), 3 relation levels, grammar-of-sense (Γ), signature types, partial semantic operations.
- `/home/jp/proyectos/hum-ecosystem/tools/tractatusIR/specs/spec_main.md` — proto; the discriminative semantic representation model (concept+context+features; vertical/local/horizontal dimensions).
- `/home/jp/proyectos/hum-ecosystem/tools/tractatusIR/specs/` — proto; subdirs `concepts`, `database`, `data_model`, `formalization`, `operations`, `tractatus`, plus `contradiction_log.md`, `_index.md`.
- `/home/jp/proyectos/hum-ecosystem/tools/tractatusIR/atomos/` — proto; atomized doc corpus (00_meta, 05_tractatus, 10_core, 15_heuristics, 20_formal, 30_operations, 40_persistence, 50_examples, 90_indices). Key: `10_core/{concept,dimension,value,context,signature_types,fact_relation_rule}.md`, `40_persistence/database_schema.md`, `20_formal/{matrix_model,masks,boolean_algebra,closure_and_partiality}.md`.
- `/home/jp/proyectos/hum-ecosystem/tools/tractatusIR/lisp/` — proto; Common Lisp runtime: `datype+operations/tractatus-signatures.lisp`, `encoding/{tractatus-parser,tractatus-nl2projection}.lisp`, `higher functions/{discrimination,inference,security,selection,update,versioning}.lisp`, `sin-mask+tractatus logic/tractatus-semantics.lisp`, `utils/{tractatus-db,demo}.lisp`, `tractatus.asd`.
- `/home/jp/proyectos/hum-ecosystem/tools/tractatusIR/{paper,legacy,raw,docs,lisp,test}` — mixed maturity; paper drafts, legacy, raw source corpus, spec docs, tests.

## 4. Typed-language angle
Concrete artifacts defining types / schemas / grammar / IR:

- **kgdb typed graph primitives**: `.../kgdb/src/kgdb/contracts/base.py` — `VocabularyTerm` (regex `^[A-Za-z][A-Za-z0-9_.:-]*$`), `Edge.relation_type`, `SystemIdentity.node_type`. Vocabulary is *downstream-defined* (open, not hard-coded).
- **kgdb facet container**: `.../kgdb/src/kgdb/contracts/node.py` — `KnowledgeNode` with 8 named facet slots + `FacetPayload` (attribute-addressable, `extra="allow"`, lazy defaults).
- **kgdb query grammar**: `.../kgdb/src/kgdb/query/language.py` — declarative typed query DSL (facet filters, relation filters, graph scope) serialized as JSON.
- **kgdb JSON Schemas**: `.../kgdb/contracts/schemas/{sldb_kgdb_semantic_export,kgdb_graph_bundle,sldb_document_payload}.schema.json`.
- **ontology facet type catalog**: `.../ontology/src/ontology/contracts/facets.py` — 8 strongly-typed facets with `Literal` enums (medium, direction, construct_type, status, test_type…). This is the concrete "typed structured doc" schema layer.
- **ontology facet registry / injection**: `.../ontology/src/ontology/facets/registry.py` (`FieldSpec`/`FacetSpec`/`FacetRegistry`).
- **ontomap OWL schema + axioms**: `.../ontomap/ontology/core.ttl` — classes, 6 dimensions as OWL properties with concrete sub-properties + reasoning axioms (Transitive/Irreflexive/Asymmetric), disjointness, SHACL prefix.
- **ontomap 6D edge type**: `.../ontomap/ontology/edge_model.py` — `CanonicalEdge6D` (who/what/where/when/how/why + `what_rel`/`where_rel` validated sub-properties).
- **ontomap SPARQL projections / lens types**: `.../ontomap/queries/projections.sparql`, `.../ontomap/ontology/projection.py` (`LensType`, `ProjectionConfig`).
- **tractatusIR IR grammar**: `.../tractatusIR/formal-propositional-model.md` — the propositional grammar (Sachverhalt: subject·predicate·object·context·logical_form·truth_status·masks); signature type algebra (`op_sem : Σ×Σ ⇀ Σ` partial, gated by grammar-of-sense Γ).
- **tractatusIR DB schema**: `.../tractatusIR/atomos/40_persistence/database_schema.md` — tables: concepts, dimensions, dimension_values, contexts, bit_dictionary, signatures, projection_ir, facts, relation_facts, derived_relations.
- **tractatusIR signature types**: `.../tractatusIR/atomos/10_core/signature_types.md` — ConceptSignature / QuerySignature / ContrastSignature / MaskSignature / RuleSignature (bits + valid_mask + observed_mask + context + type tag).

## 5. Stealable / reusable for a knowledge agent
- **Open vocabulary + closed structure** (kgdb): the split between a fixed schema (`KnowledgeNode`, `Edge`) and a *downstream-defined* `VocabularyTerm` for node/edge types. Lets a MIND layer stay schema-stable while domains extend vocab. `.../kgdb/src/kgdb/contracts/base.py`.
- **Declarative typed query DSL** (kgdb): `StructuredQuery` = `filters ∩ relations ∩ scope`, serialized to JSON, with 5 worked example queries as living proofs. Directly reusable as an agent's graph-question interface. `.../kgdb/src/kgdb/query/language.py`, `.../kgdb/contracts/queries/sldb/`.
- **Facet-per-dimension typing** (ontology): `IOFacet/ASTFacet/SemanticFacet/ADRFacet/TestMapFacet/ComplianceFacet/SourceFacet/GitFacet` — a ready catalog of typed dimensions for a code/doc knowledge node, with provenance (`SourceFacet` hash+timestamp) and drift status. `.../ontology/src/ontology/contracts/facets.py`.
- **Markdown-frontmatter → RDF extraction** (ontology): `markdown_to_rdf()` pipeline + wikilinks, a concrete "typed structured docs → graph" path. `.../ontology/src/ontology/reasoning/owl_backend/extractor.py`.
- **6-dimensional edge model** (ontomap): who/what/where/when/how/why with edge reification and OWL sub-property inference (transitive `contains`, asymmetric `dependsOn`). Elegant way to encode multi-aspect relations without node nesting. `.../ontomap/ontology/{core.ttl,edge_model.py}`.
- **Projection/lens pattern** (ontomap): same base graph → many SPARQL-filtered views (topology tree, dependency DAG, sequence, cycle-check). `.../ontomap/queries/projections.sparql`, `.../ontomap/ontology/projection.py`. Round-trip guarantee to Mermaid/PlantUML is a reusable serialization idea.
- **Grammar-of-sense / partial operations** (tractatusIR): the distinction between always-defined boolean bit ops vs partial semantic ops validated by Γ, and the fact/relation/rule three-level model. Strong conceptual scaffold for a typed-language MIND substrate. `.../tractatusIR/formal-propositional-model.md`.
- **Discriminative bit-signatures** (tractatusIR): concept = concept+context+minimal-distinguishing-features, expanded only on collision; similarity via `M_D · M_Dᵀ`. Compact typed encoding for concept identity. `.../tractatusIR/specs/spec_main.md`, `atomos/10_core/signature_types.md`.

## 6. Open questions / gaps
- **Overlap/duplication of edge models**: kgdb `Edge` (relation_type token), ontomap `CanonicalEdge6D` (6 dims), tractatusIR relation levels — three different relation ontologies with no unifying adapter. Which is canonical for MIND?
- **kgdb_graph_bundle.schema.json appears in both kgdb and ontology** contracts — confirm which is source of truth vs copy.
- **tractatusIR maturity**: mostly spec + Lisp prototype; no Python package / console_script found. Unclear if it is executable beyond `graphlang` Lisp smoke tests. README at root is misleadingly scoped to graphlang only.
- **ontology README is one line**; real surface (facets, reasoning, energy, cleansing) is undocumented at top level — recon relied on source.
- **ontomap not packaged** (`cli.py` invoked directly, no pyproject entry_point like kgdb/ontology) — integration story unclear.
- **Namespace fragmentation**: `sldb://`, `http://ontomap.io/ontology#`, `wikipu:` (ONTOLOGY_IRI), tractatus `C_/D_/V_` prefixes — no shared IRI/identity scheme across the four tools.
- Did not deep-read: `atomos/` full corpus, `tractatusIR/paper`, `tractatusIR/legacy`, kgdb executor/neighborhood internals, ontology reasoner OWL backend details (breadth over depth per task).

## Acceptance report

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Recon covers exactly the four requested dirs (kgdb, ontology, ontomap, tractatusIR); TEMPLATE.md sections 0-6 followed; no out-of-scope tools touched; large data/build dirs (.venv, __pycache__, .sldb, output) skipped."
    }
  ],
  "changedFiles": [
    "review/parts/04-kgdb-ontology.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [
    {
      "command": "ls / find / grep / read across the four tool dirs",
      "result": "passed",
      "summary": "Enumerated module layout, read READMEs, schemas, contracts, edge models, IR specs, CLI entrypoints."
    }
  ],
  "validationOutput": [
    "Confirmed console_scripts: kgdb=kgdb.main:main, ontology=ontology.main:main; ontomap+tractatusIR lack packaged entrypoints.",
    "Confirmed typed artifacts: kgdb contracts/base.py+node.py+query/language.py, ontology contracts/facets.py, ontomap core.ttl+edge_model.py, tractatusIR formal-propositional-model.md + atomos schema."
  ],
  "residualRisks": [
    "tractatusIR maturity uncertain (spec + Lisp prototype only); root README misleadingly scoped to graphlang.",
    "Edge-model duplication across kgdb/ontomap/tractatusIR not reconciled; kgdb_graph_bundle schema appears in two trees.",
    "Breadth-over-depth: atomos corpus, paper, legacy, and reasoner internals not deep-read."
  ],
  "noStagedFiles": true,
  "diffSummary": "Added review/parts/04-kgdb-ontology.md recon index for the GRAPH+ONTOLOGY tools.",
  "reviewFindings": [
    "no blockers"
  ],
  "manualNotes": "Output written to authoritative path review/parts/04-kgdb-ontology.md. Progress file updated. tractatusIR root README describes only the graphlang Lisp prototype; the real IR lives in atomos/, specs/, and formal-propositional-model.md."
}
```
