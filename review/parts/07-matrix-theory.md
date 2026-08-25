# Recon index: Matrix — Typed-Language / Knowledge-Machine Theory Repo

## 0. One-line purpose
`/home/jp/proyectos/Matrix` is a research/theory monorepo proposing a Wittgenstein-Tractatus-grounded, boolean-matrix "knowledge machine" (Matrix / MEEL Engine) that compiles natural-language propositions into typed, context-local logical coordinates (`V_i` truth × `S_i` sense) as a discrete symbolic layer to overcome the limits of continuous LLM embeddings.

## 1. Repos / dirs covered
- `/home/jp/proyectos/Matrix/Matrix` — active Python engine (Matrix Engine / operational model, kernel, SHRDLU prototype).
- `/home/jp/proyectos/Matrix/Neurips_peiper` — NeurIPS 2026 position paper (source markdown: intro, sections, discussion, rebuttal).
- `/home/jp/proyectos/Matrix/paper_v2` — SLDB editorial-composition pipeline for the paper (sources→notes→paragraphs→sections→manuscript) + astro/UI app.
- `/home/jp/proyectos/Matrix/review` — reviewer-response drafts for the paper submission.
- `/home/jp/proyectos/Matrix/TractatusKnowledgeMachine` — Obsidian/SLDB atomic knowledge base (SSOT ontology of the whole theory) + Tractatus↔Algebra isomorphism atoms.
- `/home/jp/proyectos/Matrix/limits_of_continuous_llm_training` — literature review (Spanish) on limits of continuous LLM training + bib catalog.
- `/home/jp/proyectos/Matrix/plan_docs` — implementation issues/specs (ISSUE-001..005) for engine features.
- `/home/jp/proyectos/Matrix/spec` — YAML specs/diagrams of TKM architecture, routing, lifecycle.
- `/home/jp/proyectos/Matrix/Old` — legacy/superseded material.
- `/home/jp/proyectos/Matrix/stitch_draft.md`, `/home/jp/proyectos/Matrix/stitch_comment.md` — UI mockups (Tailwind HTML) + design notes for paper_v2 "Editorial Column Browser".

## 2. Layer classification
- MIND (knowledge/library/ontology/typed-language substrate):
  - `/home/jp/proyectos/Matrix/TractatusKnowledgeMachine/atoms` — the ontology/SSOT of concepts, types, operations.
  - `/home/jp/proyectos/Matrix/Matrix/src/operational_model` + `kernel` — the typed logical engine (V_i/S_i matrices, MEEL).
  - `/home/jp/proyectos/Matrix/Matrix/schemas/schema.yaml` — schema definitions.
- DATA (sldb-style document/state layer):
  - `/home/jp/proyectos/Matrix/paper_v2` (sources/notes/paragraphs/sections/manuscript SLDB atoms + `models.py`).
  - `/home/jp/proyectos/Matrix/TractatusKnowledgeMachine/sldb_models` (`spec.py`, `composition.py`).
  - `.sldb/` state dirs across `Matrix/`, `TractatusKnowledgeMachine/`, `paper_v2/`, `review/`.
- INTERACTION (projection/UI/agent):
  - `/home/jp/proyectos/Matrix/paper_v2/astro_app` — web projection of the paper composition.
  - `/home/jp/proyectos/Matrix/stitch_draft.md` — Tailwind HTML "Editorial Column Browser" mockups.
  - `/home/jp/proyectos/Matrix/Matrix/prototypes/shrdlu` — controlled-English → kernel dialogue prototype.
- HARNESS (workflow/orchestration):
  - `/home/jp/proyectos/Matrix/paper_v2/build_pipeline.py`, `run/`, `runs/`, `deltas/`.
- OTHER:
  - `/home/jp/proyectos/Matrix/Neurips_peiper`, `review`, `limits_of_continuous_llm_training` (papers/lit review).

## 3. Descriptive index (the core deliverable)

### Matrix Engine (active code)
- `/home/jp/proyectos/Matrix/Matrix/README.md` — working; primary entry doc. Defines "Minimal Agglomerative Text Retrieval Index", the `V_i`/`S_i`/`W_i`/`D_i` model, s-expression runtime surface, `sinnvoll/sinnlos/unsinnig` statuses.
- `/home/jp/proyectos/Matrix/Matrix/src/operational_model/` — working; proposition-first runtime: `Thing`, `Relation`, `Proposition`, `Fact`, `WiGame`, `Context`, `RoutingProjection`.
- `/home/jp/proyectos/Matrix/Matrix/src/operational_model/kernel/` — working; formula, boolean, bitwise, typed-assertion layers.
- `/home/jp/proyectos/Matrix/Matrix/prototypes/shrdlu/proto.py` — proto; lowers controlled English into kernel/runtime ops (blocks-world).
- `/home/jp/proyectos/Matrix/Matrix/schemas/schema.yaml` — working; schema definition (typed structure).
- `/home/jp/proyectos/Matrix/Matrix/docs/` — architecture/concepts/data_models/operations/storage_boundary docs (per README map).

### NeurIPS paper (theory source)
- `/home/jp/proyectos/Matrix/Neurips_peiper/Intro.md` — idea/working; the clearest full narrative of the Tractatus→boolean-matrix theory (things vs facts, sign vs symbol, tripartition of sense, `V_i`/`S_i`, lettuce/spinach/carrot/celery worked example, disambiguation via dimension addition, hierarchical routing).
- `/home/jp/proyectos/Matrix/Neurips_peiper/sections/00_abstract.md` … `10_appendix.md` — paper sections (abstract, SOTA, intro, philosophical foundation, proposed representation, discussion, conclusion, appendix).
- `/home/jp/proyectos/Matrix/Neurips_peiper/references.bib`, `bibtex.md` — bibliography.
- `/home/jp/proyectos/Matrix/Neurips_peiper/Discussion.md`, `rebuttal_response.md` — discussion + reviewer rebuttal.

### paper_v2 (composition pipeline)
- `/home/jp/proyectos/Matrix/paper_v2/README.md` — working; SLDB composition chain sources→notes→paragraphs→sections→manuscript; `__compositions__` digests + `![[transclusions]]`.
- `/home/jp/proyectos/Matrix/paper_v2/models.py` — SLDB doc models: `PaperSourceDoc`, `WritingNoteDoc`, `SectionParagraphDoc`, `PaperSectionDoc`, `PaperManuscriptDoc`.
- `/home/jp/proyectos/Matrix/paper_v2/build_pipeline.py` — regenerates atoms + `build/paper.composed.md`, `validation_report.json`, `compose_report.json`.
- `/home/jp/proyectos/Matrix/paper_v2/astro_app/` — INTERACTION projection.

### TractatusKnowledgeMachine (ontology SSOT)
- `/home/jp/proyectos/Matrix/TractatusKnowledgeMachine/atoms/Propuesta_Indice.md` — working; the master taxonomy/index of ~200 atoms across Antecedentes, Aplicaciones, Computacion, Filosofia, Fuentes, Matematica, Teoria_de_Bases_de_Datos, Isomorfismo_Tractatus_Algebra.
- `/home/jp/proyectos/Matrix/TractatusKnowledgeMachine/atoms/Isomorfismo_Tractatus_Algebra/` — 6 atoms mapping Tractatus props to algebra/JAX: `01_El_Mundo_como_Espacio_Tensor`, `02_Hecho_Atomico_como_Mintermo`, `03_Espacio_Logico_como_Arquitectura_JAX`, `04_Forma_Logica_como_Matriz_Si`, `05_Sentido_Sinn_como_Region_Tensorial`, `06_Absurdo_Unsinnig_como_Violacion_Sintactica`.
- `/home/jp/proyectos/Matrix/TractatusKnowledgeMachine/atoms/predicates-5w1h.yaml` — predicate/relation vocabulary (5W1H).
- `/home/jp/proyectos/Matrix/TractatusKnowledgeMachine/sldb_models/spec.py` — `CompositionSpecDoc` (StructuredNLDoc template with `⸢rev•…⸥` typed slots).
- `/home/jp/proyectos/Matrix/TractatusKnowledgeMachine/sldb_models/composition.py` — composition model.
- `/home/jp/proyectos/Matrix/TractatusKnowledgeMachine/Raw/` — `llm studio/`, `roadmap/`, `UniversalGrammarFormalization/`, `Viejos/` (raw drafts).

### limits_of_continuous_llm_training (lit review)
- `/home/jp/proyectos/Matrix/limits_of_continuous_llm_training/README.md` — index + central "límites" mermaid diagram (semantic / statistical / uncertainty-boundary limits → neuro-symbolic V_i×S_i solution).
- `01_theoretical_limits_continuous_embeddings.md` — Model Collapse (Shumailov 2024), Octopus Test (Bender & Koller 2020), Symbol Grounding (Harnad 1990), Energy Models (LeCun 2022).
- `02_hallucination_benchmarks_and_metrics.md` — FActScore, HaluEval, SelfCheckGPT, Orgad 2025.
- `03_neuro_symbolic_and_fol_translations.md` — FOL translation, knowledge graphs.
- `04_wittgenstein_and_knowledge_representation.md` — tractarian fact ontology, `Sinnvoll/Sinnlos/Unsinnig`, private-language critique.
- `05_bib_references_catalog.md` — 28-reference annotated catalog.

### spec (YAML architecture)
- `/home/jp/proyectos/Matrix/spec/architecture.yaml` — TKM layered architecture (NL → Parsing → Grounding → Ontological(OWL) → Context(W_i) → Matrix(V_i,S_i) → Operational(W*)).
- `/home/jp/proyectos/Matrix/spec/proposition_lifecycle.yaml` — state machine: `unvalidated`→`unsinnig`/`sinnlos_tautology`/`sinnlos_contradiction`/`sinnvoll_true`/`sinnvoll_false` with guards on `S_i`/`M_i`.
- `/home/jp/proyectos/Matrix/spec/hierarchical_routing.yaml`, `tkm_atom_routing_tree.yaml`, `structural_masks.yaml`, `interaction_flow.yaml`, `system_reflection.yaml`, `whitepaper_self_logic.yaml`, `solar_system_*.yaml` — routing/mask/reflection specs + worked domain examples.

### plan_docs (implementation issues)
- `/home/jp/proyectos/Matrix/plan_docs/issues/Index.md` + `ISSUE-001_bitwise_boolean_matrix.md`, `ISSUE-002_rule_matrix_compiler.md`, `ISSUE-003_matrix_deductive_inference.md`, `ISSUE-004_matrix_transitive_closure.md`, `ISSUE-005_block_matrix_omnirepresentation_wigame.md` — engine feature specs.

### review + Old
- `/home/jp/proyectos/Matrix/review/` — reviewer responses (`response1..3`, `summary.md`, `synthesized_reviews_analysis.md`, `related_papers/`).
- `/home/jp/proyectos/Matrix/Old/` — legacy.

## 4. Typed-language angle
The whole repo IS a typed-language proposal. Concrete artifacts:
- **Typed logical IR / data model:** `/home/jp/proyectos/Matrix/Matrix/src/operational_model/` core types `Thing`, `Relation`, `Proposition`, `Fact`, `WiGame`, `Context`, `RoutingProjection`; kernel typed-assertion layer under `.../kernel/`.
- **S-expression surface grammar:** runtime commands `(create symbol …)`, `(create relation …)`, `(create li …)`, `(ingest …)`, `(assert …)`, `(check …)` (README) + atom `S_Expressions` / `Source_Code_..._s_expressions_py`.
- **Canonical relational form:** `aRb` / `(R a b)` — the general typed relational form.
- **Sense/type masks:** `S_i` = applicability/sense mask (= "logical form / syntax matrix"), `V_i` = truth matrix, `D_i` = discriminative mask; namespaces `kern:{symbol}` vs `W_i` symbols (`kernel_symbol_policy`).
- **Type-state / typing atoms:** `/home/jp/proyectos/Matrix/TractatusKnowledgeMachine/atoms/Computacion/Bitwise_Hardware/Tipado_Typestate`, `.../Optimizacion_y_Seguridad/Sistema_Tipos_Ti`.
- **Proposition typing states (tripartition):** `sinnvoll/sinnlos/unsinnig` formalized as a state machine in `/home/jp/proyectos/Matrix/spec/proposition_lifecycle.yaml`.
- **Schema:** `/home/jp/proyectos/Matrix/Matrix/schemas/schema.yaml`.
- **SLDB StructuredNLDoc typed templates:** `/home/jp/proyectos/Matrix/TractatusKnowledgeMachine/sldb_models/spec.py` and `/home/jp/proyectos/Matrix/paper_v2/models.py` (Pydantic `Field`-typed doc types with `⸢rev•…⸥` slot markers).
- **Grammar/sense as computable rules:** atoms `Matematica/Gramatica_y_Sentido/{Alfabeto_Sigma,Gramatica_Formal,Reglas_de_Produccion_Sintactica}`; `Gramatica_Universal_UNL`.
- **Ontology bridges:** `Parser_OWL2Matrix` / `owl2matrix.py`, OWL ontological layer in `spec/architecture.yaml`.

## 5. Stealable / reusable for a knowledge agent
- **Truth × Sense separation:** encode every proposition with two boolean layers — `V_i` (is it true) and `S_i` (is it even applicable/well-typed in this context). Lets an agent reject `unsinnig` (out-of-schema) inputs distinct from `false`. See `/home/jp/proyectos/Matrix/Neurips_peiper/Intro.md`, `/home/jp/proyectos/Matrix/spec/proposition_lifecycle.yaml`.
- **Proposition lifecycle state machine** (`spec/proposition_lifecycle.yaml`) — directly reusable as a validation gate: structural check (`S_i[o,p]`) before factual check (`M_i[o,p]`), with tautology/contradiction detection.
- **Context-local worlds `W_i` as hierarchical routing/index** — treat a knowledge tree as combinations of truth+sense matrices; boolean-semiring matmul for co-occurrence, ambiguity detection (`W⊗Wᵀ − I` then collapse), and disambiguation by adding discriminating dimensions. (`Intro.md`.)
- **Layered pipeline** NL → parse → ground → ontology → context → matrix → operational (`spec/architecture.yaml`) — a clean agent architecture blueprint.
- **Atomic knowledge base pattern:** `/home/jp/proyectos/Matrix/TractatusKnowledgeMachine/atoms/Propuesta_Indice.md` — a large, taxonomized, wikilink-connected SSOT (Obsidian + SLDB models) is a ready template for a typed knowledge-agent's memory.
- **SLDB composition pipeline** (`paper_v2/models.py`, `build_pipeline.py`) — typed doc models + transclusion/composition mechanism for building larger structured docs from atoms, with validation reports.
- **Controlled-English lowering** (`prototypes/shrdlu/proto.py`) — pattern for turning NL into typed s-expression operations.
- **Rule/inference kernel** (`plan_docs/issues/ISSUE-002..004`): bitwise boolean matrices, rule-matrix compiler, matrix deductive inference, transitive closure — the compute primitives of a symbolic reasoning agent.
- **Sinnvoll/Sinnlos/Unsinnig tripartition** as a first-class validation taxonomy for agent outputs (hallucination-as-representability-failure framing).

## 6. Open questions / gaps
- LLM integration is admittedly theoretical: atoms `Integracion_LLM_en_Training_e_Inferencia_Aun_No_Demostrada`, `Integracion_Teorica_con_LLMs_y_Trabajo_Futuro` flag it as not-yet-demonstrated.
- Two parallel doc systems (Obsidian atoms vs SLDB models vs paper_v2) — unclear which is canonical SSOT vs derived; `Old/` and `Raw/Viejos/` suggest churn.
- SLDB dependency is external (`../../../hum-ecosystem/tools/sldb/src` per paper_v2 README) — not vendored here; needed to run pipelines.
- Engine README notes some tests require optional JAX; maturity of `matrix_layer` JAX arch (`03_Espacio_Logico_como_Arquitectura_JAX`) vs pure-python core is unclear.
- Scalability of tensor expansion (dimension-per-disambiguation) is acknowledged as an issue (`Algoritmo_Minimizacion_ER`, `Eje_B_Escalabilidad`) but not resolved in read material.
- Did not open full PDFs/datasets, `Matrix/docs/*` bodies, section bodies beyond intro/abstract, or astro_app source (out of scope / size limits).
```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Produced a single recon index at /home/jp/proyectos/gemini_test/review/parts/07-matrix-theory.md following TEMPLATE.md sections 0-6 exactly, covering all required subdirs and stitch files with explicit absolute paths; no other files changed."
    }
  ],
  "changedFiles": [
    "review/parts/07-matrix-theory.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [],
  "validationOutput": [
    "Recon index written with all TEMPLATE.md headings (## 0 through ## 6); large PDFs/datasets not read per instructions."
  ],
  "residualRisks": [
    "LLM-integration claims are theoretical per repo's own atoms; SSOT canonicity across Obsidian/SLDB/paper_v2 unclear; SLDB tool is external and unvendored."
  ],
  "noStagedFiles": true,
  "diffSummary": "Added review/parts/07-matrix-theory.md: standardized recon index of the Matrix theory repo (typed-language / Tractatus knowledge-machine / LLM-limits).",
  "reviewFindings": [
    "no blockers"
  ],
  "manualNotes": "Best single entry point for the theory is /home/jp/proyectos/Matrix/Neurips_peiper/Intro.md; the ontology SSOT is /home/jp/proyectos/Matrix/TractatusKnowledgeMachine/atoms/Propuesta_Indice.md; the runnable engine types live in /home/jp/proyectos/Matrix/Matrix/src/operational_model/."
}
```