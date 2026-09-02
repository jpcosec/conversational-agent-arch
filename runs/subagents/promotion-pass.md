# Promotion Pass — Drawer → Active

Run role: deskops supervisor (routing/review only; no source edits).
Scope: promote the 8 drawer tasks the prior audit marked `b · promover`; keep ambiguous/mixed/seed items deferred. Deskops CLI only; no manual file edits.

## Method
- Recovered board/drawer state (`deskops show board`, `git status`, `ls desk/drawer/tasks`).
- Cross-checked the target list against the prior audit in `runs/subagents/task-audit-review.md`. All 8 requested ids map exactly to the audit's **b · promover** verdicts; every deferred item maps to **a (seed)** or **c (ambiguous/mixed)**. The request is consistent with the audit.
- Promoted each target with `deskops promote drawer-task-to-active-task <id> --root .`. No hand editing of task content.

## Result: 6 of 8 promoted, 2 blocked by pre-existing residue

### Promoted successfully (now `active` on Board, at `execution-ready`)
1. `task-concurrencia-el-turn-id-de-la-ui-colisiona-entre-requests-simultaneas`
2. `task-concurrencia-ensure-user-pierde-el-mensaje-del-primer-contacto`
3. `task-el-turn-id-en-vivo-tn-no-coincide-con-el-persistido-uuid`
4. `task-una-kb-sin-embeddings-falla-en-silencio-y-nadie-avisa`
5. `task-verificar-si-el-known-gap-donpeppe-saludo-unico-sigue-vigente`
6. `task-vitali-no-tiene-piso-de-seguridad-ningun-ruleatom-conversation-security`

Verified via `deskops list tasks --root .` — all six appear as `active` with an `...-execution-ready` checklist gate. On-disk drawer copies were removed by the CLI (`git status` shows them as ` D` deletions pending commit).

### Blocked — could not be promoted this pass
7. `task-ingestion-declarativa-de-traits-desde-el-formulario-registro-source-form`
8. `task-perfilador-pre-filtrar-traits-candidatos-por-similitud-semantica`

Both are genuinely execution-ready per the audit, but promotion **fails** with:
```
Unexpected: Refusing to overwrite existing document:
desk/routines/routine-task-ingestion-...-source-form.md
```
Root cause: **stale untracked bundle residue from a prior aborted promotion** already exists on disk for exactly these two ids — the full bundle (routine + ~32 primitives: checklists/conditions/edges/operators + a duplicate drawer copy) is present as **untracked** files, but the active task was never created and neither id is on the Board. `deskops promote` refuses to overwrite the pre-existing routine, so it aborts.

Evidence:
- `git ls-files desk/routines/ | grep -E 'ingestion|perfilador'` → empty (files are untracked, not committed).
- `deskops list tasks` → neither id present; Board has no reference to them.
- `deskops doctor` flags this exact set under "Untracked desk documents" (34 entries for these two ids).

This is a workspace-state repair, not a promotion decision. Clearing the residue requires deleting untracked files (a write-side file operation). **This supervisor role has no edit/write tools and bash is restricted to read-side use, so I did not remove the residue.** Recommended fix by an executor lane (or `deskops doctor --repair` after review): remove the stale untracked bundle+drawer duplicates for these two ids, then re-run `deskops promote drawer-task-to-active-task` for each. Once residue is cleared the promotion should succeed identically to the other six.

## Remaining deferred in drawer (correctly NOT promoted)

Seeds (deliberately vague / gated on other work) — audit verdict **a**:
- `seed-dividir-current-kb-agent` — deferred until spec2viz work resumes.
- `seed-mas-subagentes-al-loop` — "scope por definir"; too vague.
- `seed-profundizar-la-kb` — broad, no operative scope.

Ambiguous / mixed (would widen scope if promoted as-is) — audit verdict **c**:
- `task-evento-adverso-el-conversador-debe-decir-que-un-profesional-del-programa-registrar-el-evento` — likely **stale**: the data layer already contains the required phrase (`knowledge/atoms/rule-antonia-eventos-adversos.md:791`); needs revalidation, not coding.
- `task-grounding-el-conversador-afirma-atributos-de-productos-que-la-kb-no-declara` — mechanism undecided (runtime policy vs per-KB GateCriterion).
- `task-identidad-no-unificada-entre-canales-el-mismo-usuario-es-dos-usuarios` — depends on an undecided canonical person key; no empirical evidence yet.
- `task-la-conversacion-no-existe-como-entidad-en-el-esquema` — mixes immediate `session_id` plumbing with a conversation-entity/TTL/migration redesign; split recommended.
- `task-mindmap-no-hay-escritura-de-atoms-desde-la-ui` — mixes a read-only UX cleanup with an unresolved product decision on persisted editing; split recommended.
- `task-reconstruir-kb-de-vitali-dudas-de-contenido-y-residuo-de-tools` — mixes an executable P5b cleanup with open business questions (locations, prices, catalog, TZ); split recommended.

## Board / working-tree state after this pass
- Active board gained 6 new tasks at `execution-ready` (routing is truthful).
- No files staged; all changes are working-tree only (`deskops promote` performed adds/deletes on disk).
- No source/task content edited by hand.
- Two blocked promotions remain, plus their pre-existing untracked residue, awaiting a write-capable lane or `deskops doctor --repair`.

## Residual risks
- The pre-existing untracked residue for the two blocked ids predates this run; `deskops doctor` also reports `desk/tasks/Board.md (data_mutation)` and the 6 promoted drawer sources as `missing` in the drawer store index — expected transient state until the promotion changes are committed via the normal closeout gate.
- No commit was created (out of scope for this promotion pass; supervisor did not self-retire or force a closeout).
