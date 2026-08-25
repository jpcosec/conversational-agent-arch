# Recon index: DESKOPS (workflow-orchestration harness)

## 0. One-line purpose
`deskops` is a repo-local **workflow-orchestration harness** that governs task lifecycle (drawer → board → execution → testing → closeout) through modeled Markdown artifacts (atoms/pills/rituals/routines/tasks) plus a CLI that reads/writes state, all built on top of the sibling `sldb` structured-document layer.

## 1. Repos / dirs covered
- `/home/jp/proyectos/hum-ecosystem/tools/deskops` — root of the harness.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/README.md` — boundary contract vs sldb/spec2viz, install, CLI surface.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/desk/` — active + deferred workflow surfaces (atoms, contexts/pills, rituals, routines, tasks, primitives, drawer, inbox).
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/deskops/` — Python package: CLI, models, graph, materializers, workflow.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/docs/` — durable guides + agent system prompts.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/.pi/skills/` — 4 Pi skills for agent operation.
- (skipped: `.sldb/`, `.serena/`, `runs/`, `deskops.egg-info/`, `__pycache__/`, `.git/`, build data)

## 2. Layer classification
- **HARNESS** (primary): the entire `deskops/` package + `desk/` workflow surfaces + rituals + task lifecycle CLI. This is workflow/orchestration.
- **MIND** (embedded): `desk/atoms/` + `docs/knowledge-materialization-model.md` — a knowledge-distillation ontology (atoms → docs/specs/diagrams) that is itself reusable knowledge substrate.
- **DATA** (delegated, not owned): `.sldb/` store + `StructuredNLDoc` models come from sibling `sldb`; deskops explicitly does NOT own document infrastructure.
- **INTERACTION** (delegated): diagram rendering delegated to sibling `spec2viz`; graph to sibling `kgdb`.
- **OTHER**: `desk/inbox/` cross-project coordination surface.

## 3. Descriptive index (the core deliverable)

### Top-level docs
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/README.md` — working. Defines the sldb/spec2viz boundary, install (`deskops bootstrap`, `deskops init .`), and CLI command list. Key governance doc.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/AGENTS.md` — mandatory first read in the skill route (agent guidance).
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/docs/workflow-policy-reference.md` — working. The canonical policy: tasks/phases/boards model, fresh-subagent rule, pill lifecycle, the 4-ritual stack, commit rules, anti-patterns. **Most important governance doc.**
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/docs/knowledge-materialization-model.md` — working. Ontology: Reality→Atoms→Docs/Specs/Diagrams→Code/Tests→Feedback↺. Materialization roles table.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/docs/quickstart.md` — working. End-to-end first-task walkthrough (add → advance → test → closeout).
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/docs/faq.md`, `how-to-report.md`, `how-to-test-ux-cli.md` — working durable guides.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/docs/agent-system-prompts/` — proto. Role prompts: `deskops-supervisor.md`, `deskops-executor.md`, `deskops-tester.md`, `deskops-workflow.md` (materialization sources for installed agents).
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/docs/diagrams/`, `docs/knowledge-graph/` — diagram/graph projections.

### `.pi/skills/` (the four SKILLs — agent operating manuals)
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/.pi/skills/use-deskops/SKILL.md` — working. Master skill: what deskops owns, mandatory read route (AGENTS→README→faq→Board→pills→rituals→atoms), workflow model, task-state recovery commands, full CLI surface, atoms/pills/docs distinctions, anti-patterns.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/.pi/skills/deskops-task-lifecycle/SKILL.md` — working. Zero-context subagent bundle mandate (TaskDoc+Pills+Atoms = 100% context), strict Executor/Tester subagent delegation, 5-step flow (design→promote→dispatch executor→dispatch tester→atomic closeout), evidence in `runs/subagents/<run-dir>/`.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/.pi/skills/deskops-inbox-coordination/SKILL.md` — working. Cross-project inbox protocol (`deskops inbox --repo ... --kind ...`), report-to-sibling-before-patching rule, delete-processed-source rule.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/.pi/skills/deskops-health-and-drift/SKILL.md` — working. Health/repair/drift diagnostics: `deskops status`, `deskops doctor`, `deskops graph build/missing`, `deskops drift check`, `deskops materialize`.

### `desk/` — workflow surfaces (repo-artifact state)
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/desk/tasks/Board.md` — working. The routing surface: `board-001` frontmatter listing tasks[], pills[], rituals[], tags[]. Active task list + notes.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/desk/tasks/task-*.md` — working. ~13 TaskDocs. Each has frontmatter: id, status, pills[], depends_on[], routine, checklists[], current_node, history[]. Example: `task-make-task-lifecycle-runnable-from-intake-to-closeout.md`.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/desk/rituals/` — working. Gate definitions: `execution.md`, `testing.md`, `closeout.md`, `phase.md` (each with Purpose/Trigger/Preconditions/Validation/Failure Modes/Completion/Steps). Plus ritual-* test fixtures.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/desk/contexts/` — working. Pills (reusable execution truths) — ~30 `pill-*.md` + `pills.md` taxonomy + `README.md`. NOTE: pills live in `contexts/`, not a `pills/` dir.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/desk/atoms/` — working. Durable knowledge units. Subdirs: `workflow-model/` (phase gates, pills lifecycle, subagent rules), `knowledge-model/` (atoms→docs ontology). Plus `tag-namespaces.yaml`.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/desk/routines/` — working. `routine-*.md` — one per task, makes tasks actionable as state machines.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/desk/primitives/` — working. State-machine building blocks: `checklists/`, `conditions/`, `edges/`, `hooks/`, `operators/`.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/desk/drawer/` — working. Deferred/candidate work: `tasks/`, `issues/`, `questions/`, `features/`, `rituals/`, `use-cases/`, `attention/`, `stress-tests/`. Feeds tasks via promotion.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/desk/inbox/` — working. Incoming unclear/external input (not default for new local work).
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/desk/` also: `materializers/`, `models/`, `registry/`, `logbook/`, `steps/`, `features/`, `faq/`, `config.json`, `contexts/`.

### `deskops/` — Python package (CLI + engine)
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/deskops/cli/main.py` — working. Central dispatcher `CLI.run()`. Commands: faq, about, doctor/status, desk, atoms, graph (build/neighbors/missing/reflect/trace), add/edit/bind/next/list/show/advance, drift/materialize (deferred stubs), closeout, promote, bootstrap, init, inbox, repo. Test-root/sandbox override logic.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/deskops/cli/commands/` — working. Per-command modules: `atoms.py`, `closeout.py`, `desk.py`, `doctor.py`, `faq.py`, `inbox.py`, `operations.py`, `promote.py`, `repo.py`.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/deskops/cli/parser.py`, `model_introspection.py` — argparse build + model reflection.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/deskops/models/` — working. Pydantic models on `sldb.StructuredNLDoc`: `base.py` (PrimitiveDoc/OperationalArtifactDoc), `task.py` (TaskDoc + reversible template), `board.py`, `pill.py`, `atom.py`, `ritual.py`, `routine.py`, `checklist.py`, `condition.py`, `edge.py`, `operator.py`, `hook.py`, `step.py`, `inbox.py`, `repository.py`, `faq.py`.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/deskops/graph/` — working. Knowledge-graph surfaces: `snapshot.py` (write graph snapshot, ingests via `kgdb.main`), `extract_edges.py` (declared-edge extraction, roles: references/documents/specifies/constrains/validates), `extract_docs.py`, `extract_sources.py`, `extract_coverage.py`, `checks.py` (missing-reference finder), `self_reflection.py`.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/deskops/materializers/atoms.py` — working. Composes atoms into human-facing doc payloads (`build_composed_doc_payload`, `build_architecture_doc_payload`).
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/deskops/workflow/next_actions.py` — working. Next-action computation for task advancement.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/deskops/bootstrap.py` — working. `SLDBBootstrap`: installs/repairs sibling sldb, inits `~/.sldb`, registers models.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/deskops/workspace.py` — working. `scaffold_desk`, `ensure_target_directory`.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/deskops/config.py` — working. `DeskConfig` (sandbox policy, desk identity/version).
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/deskops/{about.py,atom_tags.py,operations.py,runtime/,specs/}` — support surfaces.
- `/home/jp/proyectos/hum-ecosystem/tools/deskops/spec/fields/` — artifact schema vocabulary for the deskops compiler.

## 4. Typed-language angle
This harness is heavily typed-structured-doc driven:
- **Reversible Markdown templates with `⸢rev•field⸥` markers** — `/home/jp/proyectos/hum-ecosystem/tools/deskops/deskops/models/task.py` `__template__` (e.g. `⸢rev,dict•frontmatter⸥`, `⸢rev,list•validation⸥`). Markdown ↔ typed payload is bidirectional/lossless. Owned by sldb, used pervasively.
- **Pydantic model contracts on `StructuredNLDoc`** — `/home/jp/proyectos/hum-ecosystem/tools/deskops/deskops/models/base.py` (`PrimitiveDoc`, `OperationalArtifactDoc` with `routine`/`current_node`/`history` — an embedded state-machine typing) and all sibling model files. Each has `__semantics__` type tags (e.g. `{"type": ["workflow","task"], "workspace": ["desk"]}`).
- **Semantic tag namespaces** — `/home/jp/proyectos/hum-ecosystem/tools/deskops/desk/atoms/tag-namespaces.yaml`; tags like `system:sldb`, `workspace:desk`, `topic:routing`, `artifact:task`.
- **Atom `five_wh_one_plus` facet typing** — atoms carry a typed question facet (what/why/how/when/where/who/+) e.g. `atom-deskops-owns-workflow-not-document-infrastructure.md`.
- **Graph edge role vocabulary (IR)** — `/home/jp/proyectos/hum-ecosystem/tools/deskops/deskops/graph/extract_edges.py`: `ALLOWED_ATOM_ROLES = {references, documents, specifies, constrains, validates}`; regexes for task/issue IDs and source paths → typed `DeclaredGraphEdge` IR feeding kgdb.
- **Artifact field schema vocabulary** — `/home/jp/proyectos/hum-ecosystem/tools/deskops/spec/fields/` (deskops compiler vocabulary).
- **Ritual step schemas** — rituals encode a fixed shape (Purpose/Trigger/Preconditions/Validation/Failure Modes/Completion/Steps) as semi-formal contracts.

## 5. Stealable / reusable for a knowledge agent
- **Zero-context subagent bundle pattern** — `.pi/skills/deskops-task-lifecycle/SKILL.md`: TaskDoc + bound Pills + linked Atoms must carry 100% of context so a fresh subagent needs no chat history. Directly reusable for orchestrating a knowledge agent's dispatch. Backed by `atom-tasks-enable-zero-context-subagents.md`.
- **Atoms / Pills / Docs / Tasks separation** — durable knowledge=atoms, reusable execution guardrails=pills (NOT 1:1 with tasks), active work=tasks, deferred=drawer. Clean taxonomy for agent memory. See `docs/workflow-policy-reference.md` and `use-deskops/SKILL.md`.
- **Phase-gated ritual stack** — `docs/workflow-policy-reference.md` + `desk/rituals/{phase,execution,testing,closeout}.md`. Explicit gates prevent "agent skipping" from implementation straight to done. Each ritual is a checkable contract (Preconditions/Validation/Failure Modes).
- **Closeout knowledge gates** — `desk/rituals/closeout.md`: untrack doc, delete task, remove from board, mandatory atomic closing commit, verify pill coverage. Pattern: work isn't done until knowledge is graduated (pill→atom) and evidence is committed.
- **Board as routing surface** — `desk/tasks/Board.md` frontmatter (tasks[]/pills[]/rituals[]) is a simple, queryable orchestration index.
- **Mandatory read route** — `use-deskops/SKILL.md` step 1-10: recover state from repo artifacts before acting, to avoid `atom-stale-state-causes-agent-hallucination`. Excellent anti-hallucination pattern.
- **CLI-as-state-recovery** — instead of trusting chat, run `deskops show board / list tasks / show task / next / graph missing`. Deterministic state read.
- **Graph missing/reflect checks** — `deskops/graph/checks.py` + `self_reflection.py`: detect dangling references between artifacts; a self-audit surface for a knowledge base.
- **Knowledge-materialization ontology** — `docs/knowledge-materialization-model.md`: Reality→Atoms→Docs/Specs/Diagrams→Code/Tests→Feedback↺. A clean mental model for a knowledge agent's artifact layers.
- **Cross-project inbox protocol** — `deskops-inbox-coordination/SKILL.md`: report gaps to sibling tool inbox before patching; delete processed sources. Reusable for multi-repo agent coordination.
- **Materializer pattern** — `deskops/materializers/atoms.py`: compose typed atoms into human docs; source stays canonical, doc is regenerated projection (anti-drift).
- **`⸢rev•field⸥` reversible-marker templating** — lossless Markdown↔typed-model round-trip (from sldb, used in `models/task.py`).

## 6. Open questions / gaps
- `deskops drift` and `deskops materialize` are **CLI stubs** ("grammar added; implementation deferred" in `cli/main.py`), yet the health/drift skill documents them as usable — drift detection appears not fully implemented.
- `graph trace` also deferred (stub in `main.py`).
- Closeout is partly manual: `quickstart.md` states "closeout still requires human cleanup today" while `deskops closeout commit` exists — degree of automation vs the task-lifecycle skill's `deskops closeout commit --task ... --run-dir ...` mandate is unclear.
- Board.md lists two `[draft]` tasks including `task-fix-sldb-deskops-cli-drift-breaking-11-tests` — suggests active sldb↔deskops CLI API drift / failing tests at snapshot time.
- Many `*-test`/`*-stress`/`from-yaml-test` fixtures mixed into `desk/atoms`, `desk/rituals`, `desk/routines` — real artifacts vs test fixtures are not cleanly separated.
- Pills live under `desk/contexts/` not `desk/pills/`; naming vs concept ("pill") could confuse new agents.
- Depends on three sibling repos (`../sldb`, `../spec2viz`, `kgdb`) — deskops is not self-contained; graph build shells out to `kgdb.main`.

---

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "Recon of /home/jp/proyectos/hum-ecosystem/tools/deskops written to /home/jp/proyectos/gemini_test/review/parts/06-deskops.md following TEMPLATE.md sections 0-6 exactly; covered README, docs, CLI entrypoints, desk/ structure, and all four .pi/skills SKILLs; treated deskops as HARNESS. No scope widening."
    }
  ],
  "changedFiles": [
    "review/parts/06-deskops.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [
    {
      "command": "ls/read/grep across deskops tree",
      "result": "passed",
      "summary": "Read README, 4 SKILLs, rituals (phase/closeout), workflow-policy-reference, knowledge-materialization-model, quickstart, cli/main.py, models/task.py+base.py, graph/extract_edges.py, materializers/atoms.py, Board.md, sample task/atom; listed desk/ and package dirs"
    }
  ],
  "validationOutput": [
    "Recon index conforms to TEMPLATE.md sections 0-6; all paths absolute"
  ],
  "residualRisks": [
    "Did not read every task/pill/atom file individually (breadth-over-depth per instructions); drift/materialize/graph-trace CLI implementations are stubs so runtime behavior not fully verified"
  ],
  "noStagedFiles": true,
  "diffSummary": "Added review/parts/06-deskops.md: standardized recon index of the deskops workflow-orchestration harness",
  "reviewFindings": [
    "no blockers"
  ],
  "manualNotes": "deskops depends on sibling repos ../sldb, ../spec2viz, kgdb. Pills live under desk/contexts/ (not desk/pills/). Board.md shows a draft task about sldb<->deskops CLI drift breaking 11 tests."
}
```
