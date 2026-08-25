# Part 3 — Task tree + ease evaluation

Not a Gantt. A dependency tree. Assume slow iteration: ship the minimum, then branch.
Legend: effort `E1`=hours, `E2`=days, `E3`=weeks. `blocked-by` = hard dep.

```
ROOT: framework to work over typed language
│
├─ 0. DECIDE canonical core  (gate for everything)              [E1] cheap, high-leverage
│   ├─ 0.1 Pick node/edge model = kgdb KnowledgeNode+Edge       [E1]
│   ├─ 0.2 Pick one IRI/identity scheme                         [E1]
│   └─ 0.3 Declare sldb = authoring/store, kgdb = graph         [E1]
│        (just a decision doc; unblocks 1,2,3)
│
├─ 1. MIND SPINE  (blocked-by 0)
│   ├─ 1.1 Stand up sldb store + 1 doc model (AtomDoc)          [E1]  STEAL, already works
│   ├─ 1.2 Author ~10 real atoms by hand                        [E1]  proves the loop
│   ├─ 1.3 Run existing sldb→kgdb semantic-export               [E2]  GLUE, edges are the risk
│   │      └─ 1.3a FIX: materialize edges (knowledge repo has 0)[E2]  real work, see gap
│   └─ 1.4 kgdb StructuredQuery over the 10 atoms               [E1]  STEAL
│
├─ 2. READ PROJECTION  (blocked-by 1.1; nice-to-have 1.3)
│   ├─ 2.1 spec2viz graph_html static site from store           [E1]  STEAL, zero-dep
│   └─ 2.2 (later) graph_ui editable typed-node view            [E3]  heavy TS app, defer
│
├─ 3. TYPED-LANGUAGE DIFFERENTIATORS  (blocked-by 1.1)
│   ├─ 3.1 Add S_i/V_i fields to AtomDoc                        [E1]  ROB (schema only)
│   ├─ 3.2 Proposition lifecycle gate (unsinnig/sinnlos/…)      [E2]  ROB from Matrix yaml
│   └─ 3.3 Source→Sample→Atom provenance + grounding state      [E2]  STEAL from knowledge repo
│
├─ 4. ORCHESTRATION  (blocked-by 1.1; independent of 2,3)
│   ├─ 4.1 Adopt deskops task lifecycle for authoring           [E1]  STEAL, already installed
│   ├─ 4.2 Zero-context subagent bundle for atom authoring      [E2]  STEAL pattern
│   └─ 4.3 Weak-answers refinement pass loop                    [E1]  STEAL
│
├─ 5. AGENCY  (blocked-by 1.4 + 3.2; the "agent" proper)
│   ├─ 5.1 G-first loop: query kgdb before LLM                  [E2]  ROB from hum core.lisp
│   ├─ 5.2 Typed s-expr / typed-JSON LLM output contract        [E2]  ROB from ir.lisp
│   └─ 5.3 Compile relation→edge, command→tool                  [E3]  ROB, harder
│
├─ 6. INGESTION  (independent; pick one when needed)
│   ├─ 6.1 conversation→atoms (turn_extractor)                  [E2]  ROB
│   ├─ 6.2 code→spec (code2specyaml)                            [E2]  ROB (roundtrip gap to fix)
│   └─ 6.3 web→atlas (hum-scrapper)                             [E3]  heavy deps, defer
│
└─ 7. ANNOTATION  (independent, additive)
    └─ 7.1 marcado overlay linking prose spans → atoms          [E2]  ROB
```

## Critical path (smallest end-to-end value)
`0 → 1.1 → 1.2 → 2.1`  = a hand-authored typed KB you can browse. **~1-2 days, mostly stealing.**
Then `1.3/1.3a` (edges) is the first real engineering, and the current known gap.

## Ease ranking (do first = high value / low effort)
| Task | Value | Effort | Verdict |
|---|---|---|---|
| 0. Decide core | very high | E1 | do first, blocks all |
| 1.1 sldb store | high | E1 | steal, works today |
| 2.1 graph_html site | high | E1 | instant visible payoff |
| 4.1 deskops lifecycle | high | E1 | already installed |
| 3.1 S_i/V_i fields | high | E1 | the differentiator, cheap |
| 1.3a edge materialization | high | E2 | first real work / known gap |
| 3.2 lifecycle gate | med-high | E2 | ROB from Matrix |
| 3.3 provenance chain | high | E2 | steal from knowledge repo |
| 5.1 G-first loop | high | E2 | makes it an "agent" |
| 5.3 command→tool | med | E3 | powerful but risky, defer |
| 2.2 graph_ui editor | med | E3 | big TS app, defer |
| 6.3 web scraper | low-now | E3 | heavy deps, defer |

## Hard risks to schedule around
- **Edge materialization** (1.3a): the graph is empty in the one real instance; this is the make-or-break.
- **Core-model fragmentation** (task 0): if not decided first, every downstream task forks.
- **sldb Clojure refactor**: build on the CLI, not internal Python APIs, to survive it.
- **specYaml roundtrip gap**: don't rely on code2specyaml output validating until fixed.

## Suggested first slice (one sitting)
1. Task 0 decision doc.
2. Task 1.1 + 1.2 (sldb + 10 atoms).
3. Task 2.1 (graph_html view).
Stop. Evaluate. Then decide edges (1.3a) vs differentiators (3.1/3.3).
