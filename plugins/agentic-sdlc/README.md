# Agentic SDLC

A skill-driven pipeline plugin for coding-agent hosts. Point it at a task — free text, a
ticket reference, or a greenfield idea — and it drives that task through requirements,
planning, TDD implementation, code review, QA, and functional verification, stopping at a
review-ready branch. It never opens or merges anything on your behalf; handoff is the finish
line, not a PR.

Every judgment point in the pipeline runs a cheap deterministic check before it ever spends a
model call. Cheap checks first, model judgment second, human judgment always available — that
ordering is the core design bet of this plugin.

> Why stop at a branch instead of a PR? Because "ready for review" and "opened for review" are
> different claims, and the second one has side effects (notifications, CI runs, reviewer time)
> that shouldn't fire until something — human or `mr-creator` — actually decides to make them.

## Before you install

- **`superpowers` ≥ 5.0.7 is a hard prerequisite.** The pipeline borrows its brainstorming,
  plan-writing, subagent-driven-development, and TDD sub-skills directly rather than
  reimplementing them. First run halts immediately with an install hint if the version
  requirement isn't met.
- **`repo-guides` must run first.** The pipeline reads `.agentic/guides/project.md`,
  `.agentic/guides/standards/git-workflow.md`, and `.agentic/guides/quality-gates.md` at
  multiple phases; if they're missing, the run halts rather than guessing at your conventions.
- **Feature branches only.** Claude Code and Codex CLI hosts must run this plugin's flows
  against a feature branch in the current checkout. Do not create a git worktree for it —
  the pipeline assumes one working tree per run.
- **Codex CLI** needs `plugin_hooks = true` set under `[features]` in its global config before
  skill-based entry points will fire correctly.
- Registered in the `agentic-os` marketplace at `./plugins/agentic-sdlc`
  (`.claude-plugin/marketplace.json` is the catalog entry).

## Oversight, three ways

Every run picks one of three levels of human involvement — hands-on, hands-off, or
inline-and-fast — and that choice is fixed for the run's lifetime (mid-flow switching is not
supported yet; see Roadmap). In practice the choice cuts across four concrete entry points,
because the "inline-and-fast" level splits into a task-sized flow and an even lighter one.

### Four operational modes

| Mode | Entry point | Fits | Pace | Subagents in play |
|---|---|---|---|---|
| HITL | `sdlc-start` | Production, regulated changes | User-paced — every gate asks you | Zero during implementation |
| Autonomous | `sdlc-autonomous` | Greenfield work, batch runs | Model-paced | Dispatched on ambiguity, risk, or boundary conditions |
| Task (v0.5) | `sdlc-task` | User-classified XS/S/M work | Inline, same session | One (review only) |
| Light (v0.1) | `sdlc-light` | Simple, unambiguous tasks | Inline, same session | One (review only) |

`sdlc-doctor` and `sdlc-status` aren't modes — they're utility entry points for environment
checks and run inspection, covered below.

## How a run actually moves

Two orchestrators do the driving. `sdlc-pipeline` runs the heavy, ten-phase flow behind
`sdlc-start` and `sdlc-autonomous` — the only thing that differs between those two hosts is
which answer `decision-router` gives at each gate. `sdlc-task` is its own lighter
six-stage orchestrator, and `sdlc-light` strips it down further still.

### The heavy pipeline — `sdlc-pipeline`, Phase 0–9

| Phase | Does | Writes |
|---|---|---|
| 0 | Environment doctor check, one-time memory load | `.agentic/agentic-sdlc/doctor.json` |
| 1 | `requirements-intake` normalizes the input | `requirements.md` |
| 2 | Branch setup on the current checkout | — |
| 3 | `complexity-scoring` rates the task 6–36 | `complexity.json` + routing decision |
| 4 | Brainstorming — **skipped when the score is ≤ 14** | `design.md` |
| 5 | `superpowers:writing-plans` | `plan.md` |
| 6 | TDD implementation, one commit per task | per-task commits + `evidence/<task-id>.json` |
| 7 | Three-lens code review | review bundle + `code-review-final.json` |
| 8 | `qa-gates` + `feature-verification` | `qa-report.md` + verification evidence |
| 9 | Handoff | branch left review-ready |

> The complexity score is the fork in the road: 6–14 skips straight to planning, 15–36 forces
> the brainstorming/spec phase first. There's no in-between tier — the gate is binary on
> that one number.

### The task flow — `sdlc-task`, Stage 0–6

| Stage | Does | Writes |
|---|---|---|
| 0 | Pre-flight — reads the cached doctor result, **loads no memory** | — |
| 1 | Brainstorm-lite | `spec.md` |
| 2 | Plan | `plan.md` |
| 3 | Inline TDD — no subagent dispatch, no per-task evidence file | commits |
| 4 | Inline code review — one round plus one fix-up pass; a second `request-changes` escalates | — |
| 5 | Validate — `qa-gates`, plus `feature-verification` only if the task was flagged `--ui` | — |
| 6 | Handoff | branch left review-ready, `.state.json.phase` moves to `maintenance` |

Both `sdlc-task` and `sdlc-light` additionally expose a `mode: "sync"` entry point (see
Reconciliation, below) — call it after someone hand-edits the code post-completion, before a PR
gets opened.

### Light mode — `sdlc-light` (v0.1)

Drops complexity scoring and the spec/brainstorming step entirely. In their place: a capped
clarifying-question check — if the task is genuinely unclear, Light mode asks a bounded number
of questions up front instead of running a full spec pass. Everything past that point mirrors
the task flow's inline review and validate stages.

## Judgment gates

`decision-router` is the single chokepoint every gate calls through — no phase implements its
own approval logic. It resolves a gate in a fixed order:

1. **Mode is `hitl`?** Ask the user directly via the host's question mechanism and stop there.
   No fast-path, no stand-in, ever.
2. **Deterministic evidence check.** Missing a required screenshot, console errors present, or
   an explicit FAIL/INCONCLUSIVE result — any of those reject the gate, logged with
   `source: "deterministic"`. A clean pass or an N/A result falls through to the next step.
3. **Fast-path eligibility.** Most gates have none. Where a gate defines low-risk
   preconditions and they're all met, auto-approve with `source: "fast-path"` — no model call.
4. **Dispatch the matched stand-in subagent** for a verdict, then run the escalation check
   below on the result. The subagent's verdict is preserved in the audit trail regardless of
   whether escalation later overrides the outcome — logged as `prior_subagent_verdict` if a
   human re-decides it.

Every verdict is one of three values: `approve`, `request-changes` (carries a follow-up list),
or `abort` — `abort` is terminal and halts the run outright.

| Gate ID | Fires at | Resolved by | Fast-path |
|---|---|---|---|
| `requirements.ambiguous` | Phase 1 | `story-proxy` | none |
| `spec.clarification` | Phase 4 | `story-proxy` | none |
| `spec.approved` | Phase 4 | `lead-proxy` | none |
| `plan.approved` | Phase 5 | `lead-proxy` | none |
| `code-review.final` | Phase 7 | `code-review-orchestrator` | none |
| `code-review.check` | Phase 7 | `code-review-orchestrator` | findings-only outcomes only |
| `qa.drift` | Phase 8 | `lead-proxy` | none |
| `feature.verification` | Phase 8 | `lead-proxy` | auto-approves on all-green evidence |
| `qa.ready` | Phase 8 exit | deterministic | always — no model call, ever |

`qa.ready` is the one gate that's purely mechanical: if every upstream evidence file is green,
it resolves with zero model involvement.

### Code review never gets a stand-in

Every other gate can fall through to a single stand-in subagent. `code-review.final` and
`code-review.check` don't — `code-review-orchestrator` resolves both of them inline, in HITL
*and* autonomous mode alike, by fanning out three parallel review-lens subagents (blind,
edge-case, acceptance), adjudicating their output itself, and persisting one verdict. No human
proxy substitutes for that fan-out; the orchestrator *is* the resolver.

> If the orchestrator can't actually run — empty diff, every lens failed, or it can't write its
> verdict file — it safe-fails to a low-confidence `request-changes` rather than silently
> approving. A gate that can't evaluate anything should never read as a pass.

### Escalation

Even in autonomous mode, a gate verdict can still land in front of a human when:

- the returned confidence is low,
- the verdict's risk flags intersect the run's configured escalation list, or
- the matched stand-in returns malformed JSON twice in a row.

Default autonomous escalation triggers are `security` and `breaking-change`
(`--escalate-on security,breaking-change` on the CLI to override). When escalation fires, the
human's answer overrides the subagent's verdict — but the subagent's original verdict stays in
the audit trail as `prior_subagent_verdict`, never silently discarded.

Each stand-in subagent runs at a configurable model tier — economy, standard, or premium — so
you can trade cost against rigor per role rather than per run.

## Memory

Loaded exactly once, at Phase 0 of the heavy pipeline, capped at a `memory_brief` size of
≤ 6KB, and propagated from there into every subagent dispatched later in the run.
`sdlc-task` Stage 0 explicitly skips this — the lightweight flow runs with no memory load at
all. The `role-memory` skill is what actually owns the store: durable facts live under
`.agents/memory/<role>/`, with an episodic day-by-day log under `.agents/memory/sdlc/daily/`.

## Reconciling plans with reality

Plans drift the moment someone hand-edits code after "completion." `sdlc-task` and
`sdlc-light` both expose a `mode: "sync"` entry point for exactly that: it reconciles the live
`spec.md` / `plan.md` against whatever changed inline, before a PR gets opened on top of a
stale plan.

Resume and sync both key off the same state markers:

- `.state.json.phase = "maintenance"` — set once a task-flow run reaches handoff.
- `last_sync_commit` — the commit `mode: "sync"` last reconciled against.
- `meta.json.phases[N]` — per-phase status entries (e.g. `"running"`) on heavy-pipeline runs,
  what makes resume and `sdlc-status` possible in the first place.

## Feature verification is not optional for UI work

A prior release (v0.2) had a real gap: autonomous mode could mark a user-visible feature
"ready" without anything actually exercising it. From v0.3 onward, Phase 8 unconditionally
invokes `feature-verification` for any change touching a user-visible surface — there's no
autonomous-mode shortcut around it anymore. The lightweight task flow keeps this opt-in,
gated behind the `--ui` flag, since not every XS/S task touches a rendered surface.

`feature-verification` reuses existing end-to-end coverage where it exists, generates focused
Playwright coverage where it's missing and generation is feasible, and always captures
screenshots, console output, and network errors into
`evidence/verification/<feature>.json`.

## Skill catalog

| Skill | Kind | Role |
|---|---|---|
| `sdlc-start` | Entry point | Begin a HITL run |
| `sdlc-autonomous` | Entry point | Begin an autonomous run |
| `sdlc-task` | Entry point + orchestrator | Begin (or sync) a task-flow run |
| `sdlc-light` | Entry point + orchestrator | Begin (or sync) the lightest flow |
| `sdlc-status` | Entry point | Inspect or resume a heavy-pipeline run |
| `sdlc-doctor` | Entry point | Force-refresh the environment check |
| `sdlc-pipeline` | Orchestrator | Drives Phase 0–9 for both HITL and autonomous hosts |
| `requirements-intake` | Phase skill | Normalizes input into `requirements.md`, adapter-driven ticket lookup |
| `complexity-scoring` | Phase skill | Produces the 6–36 score and routing decision |
| `decision-router` | Cross-cutting | Resolves every gate; owns the audit ledgers |
| `code-review-orchestrator` | Phase skill | Three-lens fan-out + adjudication for the heavy pipeline |
| `code-review` | Phase skill | Single-round inline review used by the task flow |
| `qa-gates` | Phase skill | Runs the project's own lint/build/test gates |
| `test-heal` | Support skill | Repairs failing or flaking tests surfaced by `qa-gates` |
| `feature-verification` | Phase skill | Mandatory verification for user-visible changes |
| `role-memory` | Support skill | Reads/writes `.agents/memory/<role>/` |
| `mr-creator` | Handoff skill | Commits, pushes, opens the PR/MR — adapter-driven |
| `mr-watch` | Handoff skill | Watches an open PR/MR to green |
| `repo-guides` | Prerequisite | Builds `.agentic/guides/*`; must run before the pipeline can |
| `product-owner` | Support skill | Turns a raw idea into a structured story |

### Agent catalog

These are the stand-ins `decision-router` dispatches when a gate can't fast-path and isn't in
HITL mode:

| Agent | Stands in for | Resolves |
|---|---|---|
| `story-proxy` | Product owner | `requirements.ambiguous`, `spec.clarification` |
| `lead-proxy` | Tech lead | `spec.approved`, `plan.approved`, `qa.drift`, `feature.verification` |
| `sizing-analyst` | — | Feeds the 6–36 score and routing decision into `complexity-scoring` |
| `guide-sync` | — | Updates `.agentic/guides/*` after a change lands, so the next run starts current |

## Configuration — `.agentic/agentic-sdlc/config.json`

| Field | Controls |
|---|---|
| `schema` | Config schema version |
| `mode_defaults.autonomous.escalate_on` | Risk-flag categories that force escalation (default: `security`, `breaking-change`) |
| `mode_defaults.autonomous.max_clarifying_questions_per_phase` | Cap on questions a phase may ask before it must proceed or escalate |
| `memory.role` | Which `.agents/memory/<role>/` store the run reads and writes |
| `memory.auto_write_on` | Events that trigger an automatic memory write |
| `review.strategy` | Which lens configuration `code-review-orchestrator` uses |
| `review.max_fix_rounds` | Cap on fix-and-recheck rounds before a review gate escalates |
| `feature_verification.allow_dynamic_playwright` | Allow generating Playwright coverage on the fly when none exists |
| `feature_verification.app_start_command` | Command that boots the app under test |
| `feature_verification.base_url` | Base URL `feature-verification` targets |
| `feature_verification.command` | Command that runs the verification suite |
| `integrations.ticket.enabled` | Turn the ticket-backend adapter on or off |
| `integrations.ticket.adapter` | Which ticket adapter `requirements-intake` loads |
| `integrations.github.enabled` | Turn GitHub integration on or off |
| `integrations.github.command` | Command used for GitHub-side actions |
| `doctor.ttl_days` | Days before `doctor.json` is considered stale and re-run |

Plan lines written in Phase 5 / `sdlc-task` Stage 2 all follow one format, so tooling can
parse them: `Test-first: yes/no — <test>`.

## Invocation markers

| Marker | Means |
|---|---|
| `--greenfield` | Input is an idea, not a ticket — skip ticket lookup |
| `--escalate-on security,breaking-change` | Override the autonomous escalation list for this run |
| `--ui` | Flag a task-flow task as touching a user-visible surface — enables `feature-verification` |
| `--slug <name>` | Custom directory slug instead of an auto-generated one |
| `mode: "hitl"` | Explicit HITL dispatch |
| `mode: "autonomous"` | Explicit autonomous dispatch |
| `mode: "sync"` | Reconcile planning docs against post-completion edits |

## Repository layout

```
.agentic/agentic-sdlc/doctor.json          environment check cache
.agentic/agentic-sdlc/config.json          plugin configuration
.agentic/guides/project.md                 repo-guides output, read at multiple phases
.agentic/guides/standards/git-workflow.md  branch/commit conventions
.agentic/guides/quality-gates.md           lint/build/test gate definitions
docs/superpowers/runs/<run-id>/            heavy-pipeline run directory
docs/superpowers/tasks/<date>-<slug>/      task-flow task directory
docs/superpowers/tasks/*/.state.json       task-flow state marker
docs/superpowers/specs/                    spec documents
docs/superpowers/plans/                    plan documents
.agents/memory/sdlc/                       role memory store for this plugin
.agents/memory/sdlc/daily/                 episodic day-by-day log
.agents/memory/<role>/                     any other role's memory store
evidence/<task-id>.json                    per-task TDD evidence (heavy pipeline)
evidence/verification/<feature>.json       feature-verification evidence
<run_dir>/gate-plan.json                   cached gate resolution plan for a run
```

Run/task-dir files worth knowing by name: `meta.json`, `requirements.md`, `complexity.json`,
`design.md`, `plan.md`, `review-bundle.json`, `qa-report.md`, `decisions.jsonl`,
`code-review-final.json`, `code-review-check.json`, `spec.md`, `.state.json`.

## What's not here yet

- No PR/MR is ever opened or merged by this plugin — every mode's terminal state is a
  review-ready branch. Use `mr-creator` when you're ready to open one.
- No mid-flow mode switching — pick HITL, autonomous, task, or light, and that's the run.
- The task and light flows deliberately skip: complexity scoring, per-task subagents and
  evidence files, two-round code review, `feature-verification` (unless `--ui`), and the
  Phase-0 memory load.
- `sdlc-status` currently covers heavy-pipeline runs only — task/light-flow runs aren't listed
  or resumable through it yet.
- No per-run HTML report generation yet — `sdlc.html` is a static, hand-maintained reference
  covering the architecture, both flows, the gate state machine, the TDD evidence cycle, and
  resume-safety; it is not generated per run.
- Git worktrees must never be created for this plugin's branch flows — one working tree, one
  run.

## Roadmap (all targeted at v2)

- Mid-flow mode switching.
- `sdlc-status` support for task/light-flow runs, not just the heavy pipeline.
- Native PR/MR opening at handoff, instead of handing off to `mr-creator` as a separate step.
- Automatic promotion of recurring lessons out of the daily memory log into curated,
  long-lived memory.
- A report-builder skill that generates a per-run static HTML report. Not implemented today —
  `sdlc-report.html` is a placeholder for that future output, distinct from the already-shipped
  `sdlc.html` reference.

## Depends on

- `superpowers` (≥ 5.0.7) — brainstorming, plan-writing, subagent-driven-development, and TDD
  sub-skills are borrowed directly, not reimplemented.
- `repo-guides` — must run before this plugin's first phase.
- `product-owner` — for turning a raw idea into a story before it ever reaches this pipeline.
- `mr-creator` / `mr-watch` — handoff and post-handoff monitoring, invoked separately.
- `guide-sync` — keeps `.agentic/guides/*` current after a change lands.

## License

Apache-2.0.
