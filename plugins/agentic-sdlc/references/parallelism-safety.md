# Parallelism Safety

When it is sound to run several workers at once, and when the work has to go one at a
time. Read this before you fan out implementation subagents or wire up worker dispatch.

> Parallel execution earns speed only when each worker owns a clean slice and any failure
> points back to exactly one owner. Absent that, concurrency trades a little wall-clock for
> a lot of untangling.

## Audience

Parent orchestrators deciding whether to split a task across workers, and anyone
configuring how the pipeline dispatches them.

## Two checks, in this order

Evaluate both before dispatching. The ceiling comes first because it can rule out fan-out
outright, before you spend effort reasoning about safety.

| Order | Check | Source | Effect |
|-------|-------|--------|--------|
| 1 | Concurrency ceiling for the work classification | `references/phase-routing.md` | Caps worker count; `1` means serialize, full stop |
| 2 | Safe-parallelism preconditions | this document + `plan.md` | Gate the fan-out only when the ceiling already allows more than one worker |

> The ceiling is a hard maximum, never a quota to fill. A ceiling of 3 does not mean spawn
> three workers — it means never spawn a fourth. If the preconditions favor one worker, use one.

## Concurrency ceilings

Authoritative values live in `references/phase-routing.md`; mirrored here for convenience.

| Classification | Max concurrent workers |
|----------------|------------------------|
| hotfix | 1 |
| bug | 2 |
| spike | 1 |
| story | governed by the safety preconditions below plus the task waves declared in `plan.md` |
| epic children | run sequentially — one child at a time |

> Epic children are parallel-safe by construction, yet they are deliberately serialized.
> Running them one after another keeps token cost and review load bounded rather than letting
> a wide fan-out flood the reviewer.

## Safe-parallelism preconditions

Fan out **only when every one of these holds**:

- **Disjoint writes.** No two workers touch the same file, module, or generated artifact.
- **Owned, artifact-producing tasks.** Each task has a named owner and emits a concrete
  output you can point to.
- **Contracts already settled.** Shared schemas, APIs, and interface boundaries are decided
  and written into `plan.md` before any worker starts.
- **Attributable verification.** When a check fails, you can trace the failure to the single
  task that caused it — no ambiguity about which worker to blame.

If any precondition is uncertain, treat it as not met and serialize.

## Serialize instead when

Any one of these forces sequential execution regardless of the ceiling:

- Two tasks would edit the same source file or the same generated artifact.
- A task cannot start until another task's output exists — a real data dependency.
- A shared schema or API contract is still open for debate.
- The work is a single global migration or a repo-wide rewrite that inherently spans everything.

## Isolation by blast radius

Match the isolation mechanism to what each worker writes.

| Blast radius | What it covers | Isolation rule |
|--------------|----------------|----------------|
| R0 (read-only) | Exploration, inspection, questions | Fan out freely; concurrent reads need no coordination |
| R1 (run-artifact writes) | Appends to `decisions.jsonl` and `events.jsonl` under `.agentic/` | Serialize the appends — one writer at a time keeps the ledgers ordered and uncorrupted |
| R2 (repo file writes) | Source and doc edits under the working tree | Give each mutating worker its own git worktree so edits never collide mid-flight |
| R3 (external side-effects) | Anything reaching outside the repo | Always behind a judgment gate; never fanned out speculatively |

> Read-only fan-out is the cheapest and safest form of parallelism — lean on it. Mutation is
> where isolation matters: separate worktrees keep parallel writers from stepping on one
> another, and serialized ledger appends keep the audit trail coherent.

## Worker briefing contract

Every implementation worker you dispatch must be told, up front:

- It is **not alone** in the codebase — other workers are active at the same time.
- It **owns specific files and responsibilities** and works only within them.
- It **must not revert unrelated edits** made by anyone else.
- It **must adapt** to changes other workers introduce rather than assuming a frozen tree.
- It **must return** the paths it changed plus the verification evidence for its own task.

Omitting any of these invites a worker to overwrite a peer's work or hide what it touched.

## Integration ownership

One rule keeps concurrent results from corrupting each other:

> The parent orchestrator owns integration. It merges results, reruns validation across the
> combined change, and resolves conflicts. Subagents never merge, reset, or discard one
> another's changes — they hand their slice back and stop.

## Known-safe patterns

- **Independent implementation tasks** driven by `superpowers:subagent-driven-development`,
  each confined to its own files.
- **Per-module guide generation** via `repo-guides` in a monorepo — one subagent per module,
  writing into disjoint directories.
- **Separate read-only exploration questions** answered in parallel, with no writes at all.

## Related files

- `plan.md` — declares the shared contracts and task waves that gate story-level parallelism.
- `references/phase-routing.md` — the authoritative per-classification worker-ceiling table.
- `superpowers:subagent-driven-development` — origin of independent, parallelizable
  implementation tasks.
- `repo-guides` — per-module parallel guide generation.

## Non-goals

- How the ceiling values are derived — that reasoning lives in `references/phase-routing.md`.
- The mechanics of merging and conflict resolution — beyond assigning ownership to the parent,
  they are out of scope here.
- Parallelism policy for non-implementation work, and the internals of scheduling or queueing.
