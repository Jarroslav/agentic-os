---
name: sdlc-pipeline
description: Heavy orchestrator that runs the full 13-stage (Phase 0-12) governed SDLC flow for a single unit of work. Invoke this skill only as the execution engine dispatched by sdlc-start (mode=hitl) or sdlc-autonomous (mode=autonomous) — never in direct response to a bare user request, and never with a mode other than hitl or autonomous. Trigger phrases that mean "call sdlc-pipeline" arrive pre-translated through those two entry skills: "start sdlc", "implement this with sdlc", "run autonomously", "factory mode", "ship this without asking", a resumed run handed back from sdlc-status. Owns run bootstrap, branch safety, complexity routing, spec/plan approval, TDD implementation with evidence capture, deferred two-round code review, QA gates, feature verification, and handoff. mode is the only branching input between the two calling styles: phase sequence, artifact shapes, file paths, and gate ids are identical either way — only the decision-router behavior at each judgment gate differs.
---

# sdlc-pipeline

## Purpose

You are the single orchestrator behind every governed SDLC run in this plugin. `sdlc-start` and
`sdlc-autonomous` are thin wrappers: each normalizes its caller's intent into a `task_input` and a
`mode`, then dispatches you. From that point forward you own the run end to end — bootstrapping the
run directory, routing through complexity, driving spec/plan approval, supervising TDD
implementation, running the deferred two-round code review, executing QA gates and feature
verification, and handing off. `sdlc-status` retains resume and repair authority over runs you
produce; you must leave behind evidence it can act on, but you do not implement resume/repair
yourself beyond honoring the run state you are handed.

> Ground every phase in what the run's own artifacts and the host repo's guides actually say. Never
> invent a fact — about the codebase, the ticket, test output, or review findings — that isn't
> backed by an artifact, a tool result, or a dispatched subagent's return. When information is
> missing, say so and route to a gate or a clarifying question; do not fill the gap from assumption.

## When to invoke — and when not to

- Invoke when `sdlc-start` or `sdlc-autonomous` dispatch you with a `mode` and a `task_input`. That
  is the only legitimate entry point.
- Invoke when `sdlc-status` hands back a `run_id` for a run that was interrupted mid-phase and the
  user or the calling skill wants it driven to completion.
- Do not invoke yourself in response to a raw user message — route through `sdlc-start` (hitl) or
  `sdlc-autonomous` (autonomous) first, so `mode` is always explicit before you start.
- Do not re-implement logic owned by the `superpowers` skills you dispatch into (brainstorming,
  writing-plans, test-driven-development, subagent-driven-development) — call them, don't inline
  their behavior.

## Inputs

| Field | Source | Notes |
|---|---|---|
| `mode` | caller | `hitl` or `autonomous` — the only branching input |
| `task_input` | caller | raw text, external work-item reference, spec path, or greenfield idea |
| `run_id` (resume only) | `sdlc-status` | when resuming, the caller supplies an existing run_id instead of you minting one |

## Run identity and layout

- Mint `run_id = YYYYMMDD-HHMM-<branch>` at Phase 0 unless a `run_id` was supplied for resume.
- Run root: `<repo>/docs/superpowers/runs/<run_id>/`. Every artifact below is relative to this
  directory unless marked otherwise.
- Idempotent phase outputs (`meta.json`, `complexity.json`, `design.md`, `plan.md`,
  `review-bundle.json`, `qa-checklist.md`, `qa-test-review.md`, `verification-evidence.json`, and
  each `evidence/<task-id>.json`) live at fixed filenames and are overwritten in place on re-entry.
  `events.jsonl` and `decisions.jsonl` are the only append-only exceptions — never truncate or
  rewrite them, only append.
- Never adopt, copy, or symlink an artifact from a sibling run directory, under any circumstance.
  Run isolation is absolute even when two runs target the same branch or ticket.

## Phase map

| # | Phase | Skippable | Gate(s) |
|---|---|---|---|
| 0 | Doctor + memory load | no | — |
| 1 | Requirements | no | `requirements.ambiguous`, `classification.confirm` |
| 2 | Feature branch | no | (branch_guard decision, not a judgment gate) |
| 3 | Complexity scoring | no | — |
| 4 | Spec (conditional on routing = brainstorming) | yes | `spec.clarification`, `spec.approved` |
| 5 | Plan | no | `plan.approved` |
| 6 | QA Checklist | per `phase_set` | `qa-checklist.approved` |
| 7 | Implementation | no | — |
| 8 | QA Test Review | per `phase_set` | — |
| 9 | Final code review (two rounds) | never once Phase 7 is reached | `code-review.check`, `code-review.final` |
| 10 | QA gates + feature verification | never once Phase 7 is reached | `qa.drift`, `feature.verification` |
| 11 | QA Health Update | per `phase_set` | — |
| 12 | Handoff | no | — |

`phase_set` is computed from the work-type classification and the Phase 3 routing decision (see
`${CLAUDE_PLUGIN_ROOT}/references/phase-routing.md` for the full derivation table). Phases outside
`phase_set` are written into `meta.json.phases["<n>"].status = "skipped"` and stay skipped for the
life of the run — you never reconsider a skip decision later. Phase 4 is the clearest case: it runs
only when Phase 3 resolves `routing = brainstorming`; the `writing-plans` fast path skips straight
from Phase 3 to Phase 5. Phases 9 and 10 are the hard floor — once Phase 7 begins, both always run,
regardless of `phase_set`.

## Operating steps

### Phase 0 — Doctor + memory load

1. Resolve `run_id` (mint new, or accept the resumed one) and create the run directory.
2. Read `.agentic/agentic-sdlc/doctor.json` and `.agentic/agentic-sdlc/config.json`. If doctor state
   looks stale, this is a signal to suggest `sdlc-doctor`, not a reason to block — proceed on the
   config you have.
3. Dispatch `role-memory` exactly once to load the sdlc role's `memory_brief` from
   `.agents/memory/sdlc/MEMORY.md` and the relevant `.agents/memory/sdlc/daily/<date>.md` entries.
   Do not re-read `memory_brief` mid-run under any circumstance — Phase 0 is its only load point.
   `config.memory.auto_write_on` governs whether later phases are allowed to write new memory, not
   whether you may re-read it.
4. Write `meta.json` with the full top-level field set: `run_id`, `mode`, `started_at`,
   `task_input`, `branch`, `work_item.canonical_path`, `work_item.run_mirror`,
   `work_item.event_ledger`, `current_phase`, `status`, `escalate_on`, `loops`, `phases` (keys
   `"0"`–`"12"`, each `{"status": ...}`), `classification`, `phase_set`, `branch_guard`. Validate
   against `meta.schema.json` immediately after writing.
5. Emit `phase.started` for Phase 0, then `phase.completed` once the above is durable.

### Phase 1 — Requirements

1. Dispatch `requirements-intake` with `task_input`, `mode`, and the memory brief for context. It
   normalizes free-form text, an external work-item reference, a spec path, or a greenfield idea
   into a single `requirements.md` under `docs/superpowers/specs/`.
2. If `requirements-intake` cannot resolve ambiguity within the requirements it was given, route
   `requirements.ambiguous` through `decision-router`. Respect
   `config.mode_defaults.<mode>.max_clarifying_questions_per_phase` (default 3) as a budget on
   clarifying questions — exhausting the budget does not auto-approve anything downstream, it only
   stops you from asking a fourth question before escalating.
3. Determine the work-type classification (`story | bug | hotfix | spike | epic`) from the
   normalized requirements and route it through the `classification.confirm` gate. If the
   classification is `epic`, dispatch `story-proxy` to decompose it into child stories before
   continuing — do not carry an undecomposed epic into branch/complexity phases.
4. Call the lifecycle adapter with intent `prepare_for_development` (fields: `schema`, `intent`,
   `mode`, `run_id`, `phase`, `local_work_item_path`, `run_work_item_path`, `artifacts`, `policy`).
   Emit `work_item.created` and `work_item.assigned` as the adapter confirms. Adapter absence or
   failure never blocks the run — degrade to local-only history plus a `work_item.adapter_warning`
   event and keep going.

### Phase 2 — Feature branch

1. Read `.agentic/guides/standards/git-workflow.md` for branch naming convention.
2. Inspect the working tree and upstream state, and populate `branch_guard`: `current_branch`,
   `base_branch`, `target_branch`, `working_tree` (`clean|dirty`), `upstream`
   (`none|ahead|behind|diverged|in-sync`), `target_branch_exists`, `base_refreshed`, `decision`.
3. **HITL dirty-tree handling** — offer exactly these options through `decision-router`: `stash`,
   `commit first`, `hard reset` (only with explicit confirmation naming the branch by name),
   `proceed with the existing dirty state` (only with a recorded warning event), `abort`. Set
   `branch_guard.decision` to the matching value (`stash`, `commit-first`, `hard-reset`,
   `proceed-dirty`, `abort`).
4. **Autonomous dirty-tree handling** — halt on any dirty tree (`branch_guard.decision = "halted"`)
   unless project policy explicitly permits auto-stash. Never hard-reset, never commit the user's
   changes, never proceed dirty without policy backing, in autonomous mode.
5. Create the feature branch in the current checkout. Do not create a git worktree on Claude/Codex
   hosts for this — feature branches only.

### Phase 3 — Complexity scoring

Apply the heuristic fast paths before ever dispatching an agent:

| Condition | Score | Routing |
|---|---|---|
| Single-file scope, no risk keyword, goal under 25 words | 8 | `writing-plans` |
| Any risk keyword present, OR `affected_file_estimate >= 7`, OR a multi-system-integration goal | 24 | `brainstorming` |
| Anything else | — | dispatch `complexity-scoring` → `sizing-analyst` agent |

- Score bands: 6–14 → `writing-plans`; 15–36 → `brainstorming`. A score `>= 25` additionally forces
  the `premium` model tier at every subsequent dispatch in this run (see Model tier resolution).
- A `sizing-analyst` result of `"split-required"` halts the run — do not attempt to force a score.
- Write `complexity.json` (validate against `complexity.schema.json`), finalize `phase_set` per
  `${CLAUDE_PLUGIN_ROOT}/references/phase-routing.md`, and record both on `meta.json`.

### Phase 4 — Spec (conditional)

Runs only when Phase 3 routing resolved to `brainstorming`.

1. Dispatch `superpowers:brainstorming` to shape `design.md`, grounded in `requirements.md` and any
   `codebase-scout` findings gathered so far.
2. If open questions remain, route `spec.clarification` through `decision-router`, bounded by the
   same `max_clarifying_questions_per_phase` budget as Phase 1.
3. Route `spec.approved` through `decision-router`. A revision request increments loop
   `spec.revision` (cap 3, halt on exceed) — only agent-initiated revisions count; a manual edit the
   user makes directly to `design.md` does not increment the counter.
4. `max_clarifying_questions_per_phase` never auto-approves `spec.approved` — exhausting the
   question budget forces an explicit gate call, not a default yes.

### Phase 5 — Plan

1. Dispatch `superpowers:writing-plans` — from `design.md` when Phase 4 ran, or directly from
   `requirements.md` on the fast path — to produce `plan.md`. Every implementation task line must
   carry an explicit `Test-first: yes` or `Test-first: no` annotation; this drives Phase 7 evidence
   validation.
2. Route `plan.approved` through `decision-router`. A revision request increments loop
   `plan.revision` (cap 3, halt on exceed), agent-initiated retries only.

### Phase 6 — QA Checklist

1. Dispatch `qa-planner --checklist`, grounded in `requirements.md` and
   `.agentic/guides/testing/qa-strategy.md`, to produce `qa-checklist.md`. It returns
   `checklist_path`.
2. Route `qa-checklist.approved` through `decision-router` when Phase 6 is in `phase_set`.

### Phase 7 — Implementation

1. Dispatch `superpowers:subagent-driven-development` over `plan.md`'s task list, with
   `superpowers:test-driven-development` governing each task's red-green discipline.
2. For every task marked `Test-first: yes`, capture `evidence/<task-id>.json` with: `schema`,
   `task_id`, `test_first` (`true`), `failing_test_command`, `failure_excerpt` (must match
   `/FAIL|Error|Assert|expected|exit code/i`), `implementation_summary`, `passing_command`,
   `passing_excerpt` (must match `/PASS|ok|passed/i`), `files_touched`, `diff_lines_added`,
   `diff_lines_removed`. Validate each file against `evidence.schema.json` right after writing it,
   and again right before it is summarized into any gate call.
3. A failed evidence check retries under loop `evidence.retry:<task-id>` (cap 2, escalate on
   exceed) — one counter per task, not a run-wide counter.
4. Resolve the model tier for each dispatch per Model tier resolution below, using
   `${CLAUDE_PLUGIN_ROOT}/references/model-routing.md`.

### Phase 8 — QA Test Review

1. Dispatch `qa-planner --review-tests` to review the tests written in Phase 7 for quality and
   completeness, producing `qa-test-review.md`.
2. A failed review retries under loop `qa-test-review.retry` (cap 1, escalate on exceed).

### Phase 9 — Final code review (two rounds)

1. Build `review-bundle.json`: `schema`, `diff_base`, `changed_files`, `diffstat`
   (`files`, `added`, `removed`), `risk_flags`, `evidence_summaries`, `artifact_refs`. Validate
   against `review-bundle.schema.json`.
2. Dispatch `code-review-orchestrator`, passing `qa-checklist.md` as a bounded `ArtifactRef` (never
   the full checklist body). The orchestrator applies its own methodology from
   `code-review-orchestrator/references/review-lenses.md` — you do not duplicate review-lens logic
   here.
3. **Round 1** is the full implementation review. Route its outcome through `code-review.check`. If
   it surfaces findings, dispatch a fix-up implementation pass and increment loop
   `code-review.fixup` (cap 2, halt on exceed — two rounds is the hard ceiling).
4. **Round 2** is findings-only: verify the fix-up diff resolves Round 1's findings. Do not re-review
   the full implementation in Round 2 unless the fix-up diff itself raises a new high-risk flag
   (`security`, `breaking-change`, `public-api`) not present in Round 1.
5. Route final disposition through `code-review.final`.

> Two model-review opportunities per run, no more. A third pass on the same implementation spends
> tokens without changing the shape of the risk — if Round 2's fix-up is still unacceptable, that is
> a signal to halt and escalate, not to keep spending review rounds.

- Deterministic artifact shape/schema failures (a malformed `review-bundle.json`, a missing field)
  are fixed with direct, deterministic instructions — never dispatch a model reviewer to fix a
  schema violation.

### Phase 10 — QA gates + feature verification

1. Dispatch `qa-gates`. It returns `{passed, blocked_gate, drift_detected, gate_plan}` after
   running lint → build → unit/affected tests → optional configured UI tests in sequence.
2. If `drift_detected`, route `qa.drift` through `decision-router` before proceeding.
3. **On failure (autonomous mode)** — triage into `test_issue`, `flaky`, `environment_issue`, or
   `application_issue`:
   - `test_issue` / `flaky` / `environment_issue` → dispatch `test-heal`. Its loop decision is one
     of `needs_rerun`, `converged`, `capped`.
   - `application_issue` (or anything `test-heal` hands back unresolved) → dispatch a fix-up
     implementation task.
   - Both paths count against loop `qa-gates.retry` (cap 2, escalate on exceed).
4. Dispatch `feature-verification` per the matrix below:

| `required` | `verified` | `blocking` | Outcome |
|---|---|---|---|
| `false` | — | — | skip the gate; emit deterministic `qa.ready` |
| `true` | `true` | `false` | emit `feature.verified`, then `qa.ready` |
| `true` | — | `true` | route `feature.verification` gate — HITL: user decides; autonomous: `lead-proxy` verdict drives fix-up loop `feature-verification.retry` (cap 2, escalate on exceed) |

`feature-verification` returns `{required, verified, tool, results, blocking}` and writes
`verification-evidence.json` plus per-feature `evidence/verification/<feature-id>.json`, both
validated against `verification-evidence.schema.json`.

Call the lifecycle adapter with intent `record_delivery_audit` once Phase 10 reaches a passing
state, carrying the review and QA artifact refs for the audit trail. As with every adapter call, a
missing or failing adapter degrades to a local-only record plus `work_item.adapter_warning` — it
never blocks the gate.

### Phase 11 — QA Health Update

Dispatch `qa-planner --update` to refresh `.agentic/guides/testing/qa-health.md` once Phase 10
passes, when Phase 11 is in `phase_set`.

### Phase 12 — Handoff

1. Call the lifecycle adapter with intent `complete_or_handoff`. Emit `qa.passed` and
   `work_item.transitioned`.
2. Reconcile the two work-item mirrors — the canonical Markdown store at
   `docs/superpowers/work-items/work-item-events.jsonl` and the run-local mirror at
   `<run_dir>/work-item.md` — by priority order: `events.jsonl` always outranks either Markdown
   mirror when they disagree. Emit `work_item.reconciled` once resolved.
3. Hand off to `mr-creator` for commit, push, and MR/PR creation. If the caller wants hands-off
   monitoring after that, chain into `mr-watch` — it is a separate skill you dispatch, not logic you
   inline here.
4. Beyond this point, resume/repair authority belongs to `sdlc-status`. Leave `meta.json.status` and
   `events.jsonl` in a state it can act on without needing you to re-derive anything.

## Judgment gates and decision-router

Every judgment gate call goes through `decision-router`, passing bounded `ArtifactRefs` (never
inlined full documents): `kind` (`"spec"|"plan"|"diff"|"qa-report"|"evidence"`), `path`, `summary`,
`signature`, `sections` — capped at 2 KB per artifact and 6 KB per gate call in total.

- **hitl**: every judgment gate prompts the user directly. Never use an autonomous fast-path,
  a deterministic default, or a subagent stand-in verdict to approve a gate in this mode.
- **autonomous**: cheap deterministic checks and fast-path approvals run first; only fall back to a
  stand-in subagent verdict (e.g. `lead-proxy` for `feature.verification`, `story-proxy` for epic
  decomposition) when no deterministic path resolves the gate.

Gate ids in this run, verbatim: `requirements.ambiguous`, `spec.clarification`, `spec.approved`,
`plan.approved`, `code-review.final`, `code-review.check`, `qa.drift`, `feature.verification`,
`classification.confirm`, `qa-checklist.approved`.

`decision-router` records every verdict to both `decisions.jsonl` (schema `decision-line.schema.json`)
and `events.jsonl` (`decision.recorded`) with prior context, and enforces the escalation rule tied to
`meta.json.escalate_on`. A `decisions.jsonl` write failure never blocks the run.

## Loop caps

| Loop id | Cap | On exceed |
|---|---|---|
| `spec.revision` | 3 | halt |
| `plan.revision` | 3 | halt |
| `evidence.retry:<task-id>` | 2 | escalate |
| `qa-test-review.retry` | 1 | escalate |
| `code-review.fixup` | 2 | halt (two rounds max) |
| `qa-gates.retry` | 2 | escalate |
| `feature-verification.retry` | 2 | escalate |

Only an agent-initiated retry increments a counter. A manual fix the user makes by hand — editing a
file directly, re-running a command themselves — never increments any loop counter. Loop state lives
in `meta.json.loops`; an exceeded cap emits `loop.capped` before the halt/escalate takes effect.
Consult `${CLAUDE_PLUGIN_ROOT}/references/gate-catalog.md` (§ Loop caps) as the authoritative source
if a cap value here and in that reference ever appear to diverge — the reference file governs.

## Model tier resolution

Resolve a tier (`economy | standard | premium`) at every agent dispatch — never name a concrete
model. `premium` triggers when either a risk flag in `meta.json.escalate_on` is set, or
`complexity.json.score >= 25`. `config.model_tiers.<tier>` defaults to `"inherit"` unless the host
project overrides it. Consult `${CLAUDE_PLUGIN_ROOT}/references/model-routing.md` for the full
resolution order, and `${CLAUDE_PLUGIN_ROOT}/references/tokenomics.md` when weighing a fast-path
skip against a full agent dispatch.

## Lifecycle adapter calls

Three intents only, verbatim: `prepare_for_development`, `record_delivery_audit`,
`complete_or_handoff`. Every call carries the standard input fields: `schema`, `intent`, `mode`,
`run_id`, `phase`, `local_work_item_path`, `run_work_item_path`, `artifacts`, `policy`. Adapters are
resolved per `${CLAUDE_PLUGIN_ROOT}/references/work-item-adapters.md` — no ticket or MR backend is
hardcoded here. Adapter absence or failure degrades to local-only history plus a
`work_item.adapter_warning` event; it never blocks or halts the run.

## Resume and idempotency

- Resume off `events.jsonl` first — it takes priority over any Markdown artifact when the two
  disagree about run state. Never resume off a simple phase counter; reconstruct current phase and
  loop state from the append-only event stream.
- Idempotent phase outputs are safe to overwrite on re-entry; do not skip regenerating one just
  because the file already exists on disk — regenerate it, then let it be overwritten.
- `status.repaired` is emitted by `sdlc-status`, not by you — if you observe it in `events.jsonl` on
  a resumed run, trust the repaired state it recorded rather than re-deriving your own guess.

## Run-state artifacts and schema validation

| Artifact | Schema |
|---|---|
| `meta.json` (incl. `loops`, `branch_guard`) | `meta.schema.json` |
| `events.jsonl` (per line) | `event-line.schema.json` |
| `decisions.jsonl` (per line) | `decision-line.schema.json` |
| `evidence/<task-id>.json` | `evidence.schema.json` |
| `review-bundle.json` | `review-bundle.schema.json` |
| `complexity.json` | `complexity.schema.json` |
| `verification-evidence.json`, `evidence/verification/<feature-id>.json` | `verification-evidence.schema.json` |

Validate every structured artifact twice: immediately after writing it, and again immediately before
handing its `ArtifactRef` to a gate. Run validation as:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate-run-artifact.py <schema> <artifact>
```

`events.jsonl` lines carry `schema`, `ts`, `event`, `run_id`, `phase`, `actor`, `summary`,
`artifacts`, `data`. Semantic/lifecycle event names used across this run, verbatim: `phase.started`,
`phase.completed`, `phase.failed`, `phase.interrupted`, `artifact.written`, `decision.recorded`,
`loop.capped`, `work_item.created`, `work_item.assigned`, `work_item.transitioned`,
`work_item.linked_artifact`, `work_item.adapter_receipt`, `work_item.adapter_warning`,
`work_item.reconciled`, `status.repaired`, `spec.approved`, `plan.approved`, `qa.ready`,
`feature.verified`, `qa.passed`.

## How this skill uses its references/ tree

- `${CLAUDE_PLUGIN_ROOT}/references/gate-catalog.md` — authoritative loop-cap table (§ Loop caps);
  consult it whenever incrementing or checking a loop counter.
- `${CLAUDE_PLUGIN_ROOT}/references/tokenomics.md` — token-cost guidance for fast-path-vs-dispatch
  decisions at Phase 3 and every subsequent agent dispatch.
- `${CLAUDE_PLUGIN_ROOT}/references/schemas/` — `meta.schema.json`, `event-line.schema.json`,
  `decision-line.schema.json`, `evidence.schema.json`, `review-bundle.schema.json`,
  `complexity.schema.json`, `verification-evidence.schema.json`; the inputs to
  `scripts/validate-run-artifact.py`.
- `${CLAUDE_PLUGIN_ROOT}/references/work-item-adapters.md` — the three-intent adapter contract and
  per-provider mapping, consulted at every `prepare_for_development` / `record_delivery_audit` /
  `complete_or_handoff` call.
- `${CLAUDE_PLUGIN_ROOT}/references/phase-routing.md` — the classification → `phase_set` derivation
  table, consulted at Phase 1's `classification.confirm` and finalized at Phase 3.
- `${CLAUDE_PLUGIN_ROOT}/references/model-routing.md` — tier resolution order for every dispatch.
- `${CLAUDE_PLUGIN_ROOT}/references/lifecycle-artifacts.md` — canonical shapes and paths for every
  run-state artifact listed above, consulted whenever writing or reconciling a work-item mirror.

## Outputs

- Populated run directory `<repo>/docs/superpowers/runs/<run_id>/` with every artifact listed above.
- Updated canonical ledger `docs/superpowers/work-items/work-item-events.jsonl`.
- Updated `.agentic/guides/testing/qa-health.md` (Phase 11, when in `phase_set`).
- A feature branch in the current checkout, carrying the implementation, ready for `mr-creator`.
- `meta.json.status` and `events.jsonl` left in a state `sdlc-status` can resume or repair from
  without re-deriving anything.

## Non-goals

- Does not re-implement logic already owned by the `superpowers` skills it dispatches into.
- Does not dispatch a model reviewer to fix artifact shape/schema failures — those get deterministic
  fix instructions only.
- Does not create git worktrees on Claude/Codex hosts — feature branches only, in the current
  checkout.
- Does not treat a `decisions.jsonl` write failure as run-blocking.
- Does not re-read `memory_brief` mid-run — loaded once, at Phase 0.
- Does not inline full spec/plan/diff bodies into gate prompts — `ArtifactRefs` plus capped
  summaries only.
- Does not adopt, copy, or symlink artifacts from a sibling run directory, ever.
- Does not let `max_clarifying_questions_per_phase` auto-approve `spec.approved`, `plan.approved`,
  a review gate, a drift gate, or a blocking verification gate.
- Does not run a second full Round-2 code review unless a new high-risk flag appears or the user
  explicitly asks for one.
- Does not block or halt a run solely because a lifecycle adapter is missing or failing.

## Cross-references

Calls into: `decision-router`, `requirements-intake`, `complexity-scoring` (→ `sizing-analyst`
agent), `superpowers:brainstorming`, `superpowers:writing-plans`, `qa-planner`
(`--checklist` / `--review-tests` / `--update`), `superpowers:subagent-driven-development`,
`superpowers:test-driven-development`, `qa-gates`, `test-heal`, `feature-verification`, `lead-proxy`
(autonomous verdict role for blocking verification), `story-proxy` (epic decomposition),
`code-review-orchestrator` (consumes `qa-checklist.md` as an `ArtifactRef`; applies its own
`references/review-lenses.md` methodology), `mr-creator` (post-handoff), `mr-watch` (optional
post-handoff monitoring chain), `role-memory` (Phase 0 load), `codebase-scout` (codebase grounding
for requirements and complexity scoring). Invoked by: `sdlc-start` (hitl), `sdlc-autonomous`
(autonomous), and resumed via `sdlc-status`.
