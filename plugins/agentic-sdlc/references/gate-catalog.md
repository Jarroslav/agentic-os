# Gate Catalog

Reference for engineers wiring `decision-router`, `code-review-orchestrator`, `lead-proxy`, and
`sdlc-pipeline`. It is the single source of truth for gate IDs, what feeds each decision, and what
blocks progress — plus the loop IDs that surround those gates, their caps, and what happens when a
cap is hit. Treat every ID, filename, and cap number below as a literal contract value: reuse it
verbatim, never rederive it from prose elsewhere.

> Deterministic-first, always. Wherever a gate's blocking condition can be checked by a script or
> an evidence-shape validator, that check runs before any model-heavy resolver sees the case. A gate
> never reaches `decision-router`, a human, or a stand-in subagent while a deterministic answer is
> still available.

## Resolver routing by mode

Mode sets the default routing for every gate:

- **HITL** — unresolved judgment goes to the user, directly. No fast path, no stand-in substitution.
- **Autonomous** — unresolved judgment routes through `decision-router`, which applies deterministic
  checks and fast-path approvals first, and only falls back to a named stand-in resolver when
  neither closes the case.

Two "Primary Resolver" shapes appear in the table below and they are not interchangeable:

| Shown as | HITL | Autonomous |
|---|---|---|
| `human` or `lead-proxy` | user, asked directly | `decision-router`, falling back to `lead-proxy` when it can't fast-path |
| `human` (HITL) or `decision-router` (autonomous) | user, asked directly | `decision-router` itself is terminal — no separate stand-in named |

> `classification.confirm` is the one gate where the *routing* is conditional, not just the resolver
> identity: HITL always asks the user regardless of confidence; autonomous only fast-paths past
> `decision-router` when confidence is high. A user override on this gate wins in either mode — it
> is never fast-pathed shut against an explicit human answer.

## Judgment gates

| Gate | Phase | Primary Resolver | Artifact Inputs | Blocking Conditions |
|---|---|---|---|---|
| `requirements.ambiguous` | 1 | `decision-router` | `requirements.md` | Unanswered required scope or acceptance questions |
| `classification.confirm` | 1 | `decision-router` (HITL always asks; autonomous fast-paths on high confidence) | `requirements.md`, classification candidate, phase-set consequence | Low-confidence candidate; user override always wins |
| `spec.clarification` | 4 | `decision-router` | Brainstorming question context | Unclear product or technical decision |
| `spec.approved` | 4 | human or `lead-proxy` | `requirements.md`, `design.md` | Rejected design; missing required constraints |
| `plan.approved` | 5 | human or `lead-proxy` | `design.md`, `plan.md` | Missing test-first task lines; unsafe plan |
| `qa-checklist.approved` | 6 | human (HITL) or `decision-router` (autonomous) | `qa-checklist.md` | Unresolved high-risk gaps with no test scenario |
| `qa-tests.approved` | 8 | human (HITL) or `decision-router` (autonomous) | `qa-test-review.md` | Missing high-risk scenarios; high-severity quality findings |
| `code-review.final` | 9 | `code-review-orchestrator` (skill, inline) | Review bundle, diff, evidence summaries | Critical or major review findings |
| `code-review.check` | 9 | `code-review-orchestrator` (skill, inline) | Prior verdict, original findings, fix-up diff | Unresolved finding; new high-risk regression |
| `qa.drift` | 10 | human or `lead-proxy` | `qa-report.md`, `design.md`, diff summary | Implementation drift from approved artifacts |
| `feature.verification` | 10 | deterministic evidence check, then human or `lead-proxy` | Browser/tool evidence | Missing or blocking user-visible proof |

> `code-review.final` and `code-review.check` don't route through `decision-router` at all — the
> `code-review-orchestrator` skill resolves them inline as part of its own verdict schema. Treat
> them as gates for accounting purposes (they still block phase 9 progress), not as
> `decision-router` calls.

> `feature.verification` is two-stage: the deterministic evidence-shape check runs first (did the
> required browser/tool evidence get produced at all), and only a *present-but-questionable* result
> escalates to human or `lead-proxy` judgment. A missing artifact never reaches that second stage —
> see Cross-cutting rules below.

## Loop accounting

Loop counts live at `meta.json.loops`, keyed by loop ID. This catalog defines the cap and the
on-cap behavior only — the counter's storage and resume mechanics are owned by `sdlc-pipeline`,
see its "Loop accounting" section.

> Only agent-initiated retry, fix-up, or revision loops count against a cap. A user-requested
> re-run of a step is not a loop iteration and never touches `meta.json.loops`.

| Loop ID | Phase | What Loops | Cap | On Cap |
|---|---|---|---|---|
| `spec.revision` | 4 | `spec.approved` request-changes → `superpowers:brainstorming` | 3 | `halt` |
| `plan.revision` | 5 | `plan.approved` request-changes → `superpowers:writing-plans` | 3 | `halt` |
| `evidence.retry:<task-id>` | 7 | Deterministic evidence failure → task retry | 2 | `escalate` |
| `qa-test-review.retry` | 8 | Test-review request-changes → fix-up task | 1 | `escalate` |
| `code-review.fixup` | 9 | Review findings → fix-up task (rounds 1–2) | 2 | `halt` |
| `qa-gates.retry` | 10 | Failed gate → autonomous fix-up task | 2 | `escalate` |
| `feature-verification.retry` | 10 | Blocking verification → fix-up task | 2 | `escalate` |

`evidence.retry:<task-id>` is a template — `<task-id>` is a placeholder segment, one counter per
task, not one counter for the whole phase.

### On-cap behavior

| Behavior | Effect |
|---|---|
| `halt` | Append a `phase.interrupted` event. Leave the run resumable. Print the resume instruction. |
| `escalate` | HITL: put the full loop history in front of the user for a decision. Autonomous: hand off through the escalation ladder (a separate, named concept — not detailed in this catalog). |

> A cap is a ceiling, not a suggestion. On the round that hits it, the pipeline appends
> `loop.capped` and applies that loop's `on_cap` action unconditionally — there is no silent extra
> round past the cap.

## Cross-cutting rules

- **Evidence shape is deterministic, always.** Malformed or missing required evidence artifacts are
  blockers decided by a script, never routed to `decision-router`, a human, or a stand-in — a
  shape failure is data, not judgment.
- **User-visible changes need proof.** A user-visible change cannot proceed to handoff without
  `feature.verification` evidence, unless a resolver has explicitly approved a substitute for it.
- **MR/PR creation is not a gate.** It is a distinct, non-gated action. No gate in this catalog
  triggers it automatically, and it is never invoked as a side effect of gate resolution.

## Out of scope

- The internal decision logic of `decision-router`, `code-review-orchestrator`, and `lead-proxy` —
  this catalog names what each is invoked for, not how it decides.
- The autonomous-mode escalation ladder referenced above — defined elsewhere.
- MR/PR creation mechanics.
- Phase numbering/ordering semantics beyond the phase number attached to each row.
- UI/prompt wording for human-facing approval requests.
