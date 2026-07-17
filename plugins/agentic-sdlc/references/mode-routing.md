# Mode routing

How a run picks one of three modes, and precisely what the choice changes. This document governs entry routing and gate-resolution authority only. It never decides which phases run, which artifacts get written, or what any gate inspects — those are fixed across all modes.

> The one thing a mode changes is *who* resolves a judgment gate, not *whether* the gate exists or *what* it produces. Same phases, same artifacts, same gate ids (`spec.approved`, `plan.approved`, `qa.drift`, `code-review.final`, `requirements.ambiguous`, …) in every mode — only the resolver differs.

## The three modes

Each user-facing mode is bound to exactly one entry-point skill. Manual lifecycle skills (see below) sit outside mode routing and are invoked directly.

| Mode | Entry skill | Gate resolver | Fits |
|---|---|---|---|
| HITL | `sdlc-start` | the user, prompted through `decision-router` | production work, ambiguous requirements, regulated changes |
| Autonomous | `sdlc-autonomous` | deterministic checks + stand-in agents, with escalation | well-scoped, low-touch tasks |
| Task | `sdlc-task` | inline, one code-review round | work the user has already sized XS/S/M |

## Choosing a mode

Route by how much human judgment the work needs, not by size alone.

| Situation | Pick |
|---|---|
| Output ships to production, or requirements are unclear, or the change is regulated | HITL |
| Scope is clear and the user accepts hands-off execution | Autonomous |
| User has already classified the task as XS/S/M and wants a lean flow | Task |

## What differs at gates

Every judgment gate calls the same helper. Mode picks which resolution path that helper takes; the verdict is recorded to `decisions.jsonl` and `events.jsonl` (R1) regardless of mode.

**HITL** — `decision-router` puts each gate to the user and waits. No deterministic fast-path, no stand-in verdict, no auto-approval. The human is the sole authority on `spec.approved`, `plan.approved`, `code-review.final`, and every other gate.

**Autonomous** — `decision-router` first tries cheap deterministic checks and fast-path approvals. When judgment is genuinely required it falls back to a stand-in subagent (for example `story-proxy` on product-shaped gates, `lead-proxy` on `code-review.final`), and escalates to the user when the stand-in cannot clear the bar.

**Task** — no gate machinery beyond a single inline code-review round. Flow runs on the current feature branch without the heavier resolver logic.

## Precondition: the repo guides

Full-pipeline modes (HITL, autonomous) hard-require three guide files produced by the `repo-guides` skill:

- `.agentic/guides/project.md`
- `.agentic/guides/standards/git-workflow.md`
- `.agentic/guides/quality-gates.md`

> If any of the three is missing, a full mode **halts** and tells the user to run `repo-guides` first. There is no degraded run — a full pipeline without its guides is not a lighter pipeline, it is an ungrounded one.

Task mode does not enforce this upfront. It defers the check until it actually needs guide content, then reads what exists.

## Git safety: the branch guard

Every implementation-capable mode runs a branch guard before touching any repo file (the guard itself is R0 inspection; the edits it protects are R2). The guard reads:

- the current branch
- the configured base branch
- working-tree cleanliness, via `git status --porcelain`
- upstream ahead / behind / diverged state
- whether the target branch already exists

### Dirty tree — HITL

Offer five choices and act on the user's pick:

| Option | Effect |
|---|---|
| Stash | shelve changes, proceed clean |
| Commit first | land current changes, then proceed |
| Hard reset | discard changes — **only** on explicit confirmation |
| Continue dirty | proceed after a warning |
| Abort | stop the run |

### Dirty tree — autonomous

Stricter, no interactive menu:

- Halt on a dirty tree **unless** project policy explicitly permits auto-stash.
- Never hard-reset.
- Never proceed dirty when policy is silent.

### Base-branch refresh

When project policy allows a refresh: fetch the remote base → switch to the configured base → fast-forward only. If the update is not a clean fast-forward, **halt**.

### Reusing an existing target branch

Before reusing a branch that already exists, inspect it for unique commits and local edits, then choose:

| Choice | Meaning |
|---|---|
| Continue | build on the existing branch |
| Recreate | discard and branch fresh |
| Reconcile | integrate divergence before proceeding |
| Abort | stop |

### Where autonomous stops

Autonomous mode ends at branch-ready. It **recommends** `mr-creator` and stops there — it never opens, watches, or merges an MR/PR itself. Every external side-effect of that kind (R3) stays behind an explicit, human-driven handoff.

## Manual lifecycle skills

Invoked directly, outside mode routing:

| Skill | Routing note |
|---|---|
| `repo-guides` | builds `.agentic/guides/`; must run inside its required subagent context |
| `product-owner` | story drafting and refinement; ticket adapter used only when configured |
| `mr-creator` | commit + push + MR/PR creation; manual invocation only |
| `mr-watch` | watches CI, review feedback, rebases, and conflicts |
| `guide-sync` | dispatched after structural branch changes |

> Integrations are adapter-driven — no ticket or MR/PR backend is hardcoded. Adapters resolve from `.agentic/guides/`.

## Out of scope

- Phase order, artifact set, and gate content — fixed and mode-independent, defined elsewhere.
- MR/PR opening, monitoring, and merging in autonomous mode — explicitly excluded; hand off to `mr-creator` / `mr-watch`.
- Upfront guide enforcement and heavy gate machinery in task mode — deliberately omitted.
