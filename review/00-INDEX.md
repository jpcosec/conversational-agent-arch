# Review master index — typed-language knowledge agent

Scope reviewed (deep, via subagents): `hum-ecosystem/{hum,hum-core,core,tools}`, `Matrix`, `knowledge`.

## Per-scope recon indexes
- `parts/01-hum-core.md` — MIND+HARNESS: Lisp G-first agent + wiki→OWL compiler.
- `parts/02-core-specyaml.md` — MIND: `specYaml` typed doc language + code2spec + turn_extractor.
- `parts/03-sldb-marcado.md` — DATA: sldb reversible-markdown store; marcado prose ASG; UIs.
- `parts/04-kgdb-ontology.md` — MIND: kgdb graph+query DSL, ontology facets, ontomap 6D edges, tractatusIR.
- `parts/05-projections-ui.md` — INTERACTION: graph_ui, spec2viz, hum-scrapper, repopackage.
- `parts/06-deskops.md` — HARNESS: task lifecycle, atoms/pills/rituals, graph surfaces.
- `parts/07-matrix-theory.md` — THEORY: Tractatus boolean-matrix knowledge machine (V_i × S_i).
- `parts/08-knowledge-repo.md` — INSTANCE: working KB (atoms + provenance + views) on sldb+deskops.

## The two-axis model you asked for
- **The mind** (substrate): typed knowledge itself.
  - Data layer: `tools/sldb` (reversible Markdown ⇄ Pydantic, `.sldb` store).
  - Graph layer: `tools/kgdb` (typed nodes/edges + `StructuredQuery` DSL).
  - Type/ontology layer: `core/specyaml` (Pydantic doc language), `tools/ontology` facets, `tools/ontomap` 6D edges, `Matrix`/`tractatusIR` (truth×sense typing).
- **How we interact** (projection/agency):
  - Projections: `tools/spec2viz` (spec→IR→HTML/mermaid), `tools/graph_ui` (typed node registry + editable graph), `sldb-ui`.
  - Prose annotation: `tools/marcado` (overlay semantic markers on unmodified text).
  - Ingestion: `tools/hum-scrapper`, `core/code2specyaml`, `core/turn_extractor`.
  - Orchestration: `tools/deskops` (workflow harness), `knowledge` (concrete KB instance).

## The recurring "typed language" through-line (most important finding)
The same idea appears independently in ~6 places; convergence, not duplication:
1. `hum/agent/ir.lisp` — typed s-expr kinds `(unl model relation command thought)`.
2. `core/specyaml/src/specyaml/models.py` — Pydantic `SpecificationDocument` (core `extra=forbid`, extensions `extra=allow`).
3. `tools/sldb` — `StructuredNLDoc` reversible `⸢rev•field⸥` markers + typed fields.
4. `tools/kgdb` — `KnowledgeNode` + `VocabularyTerm` (open vocab, closed structure) + query DSL.
5. `tools/ontomap` — `CanonicalEdge6D` (who/what/where/when/how/why) + OWL axioms.
6. `Matrix`/`tractatusIR` — `V_i` truth × `S_i` sense masks; `sinnvoll/sinnlos/unsinnig` typing states.

## Known fragmentation (must reconcile before building)
- 3 incompatible edge models: kgdb `Edge`, ontomap `Edge6D`, tractatusIR relations.
- 2 marker syntaxes: sldb `⸢rev•field⸥` vs marcado `<!-- ns:class -->`.
- No shared IRI/identity scheme (`sldb://`, `wikipu:`, `ontomap.io#`, tractatus `C_/D_`).
- `knowledge` graph snapshot has 137 nodes but **0 edges** — edges are claimed in atoms, not materialized.
- specYaml roundtrip gap: `extract_ast.py` output does not validate against `models.py`.
- `sldb-refactor-worktree` proposes a Clojure immutable-graph kernel — future churn risk.

See `PROPOSAL.md` (Part 2) and `TASK-TREE.md` (Part 3).
