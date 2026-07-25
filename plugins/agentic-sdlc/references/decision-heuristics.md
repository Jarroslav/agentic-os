# Decision heuristics for autonomous-mode gate verdicts

Deterministic rules the autonomous stand-in subagents apply when they resolve SDLC judgment gates with no human in the loop. Each rule collapses a gate into one verdict in the shared vocabulary — `approve` / `request-changes` / `abort` — plus the signals the router needs to decide whether to hand control back to a person. This file supplies only the per-gate logic; the verdict object and the escalation dispatch are owned by `skills/decision-router/SKILL.md` (component name `decision-router`), which invokes the rules below.

> Grounding rule: decide from the artifacts in front of you — requirements, spec, plan, diff, gate reports — and nothing else. Never infer a fact that is not present in those inputs. External lookups (tickets, review backends) resolve through the adapters under `.agentic/guides/`; none is hardcoded here.

## The verdict you emit

Consumer view of the fields (the authoritative schema lives in the router skill):

| Field | Use |
|---|---|
| `decision: "approve"` | gate passes; downstream work may proceed |
| `decision: "request-changes"` | gate fails; itemize the remediation in `follow_ups` |
| `confidence: "low"` | you cannot decide on the artifacts alone; forces router escalation |
| `follow_ups` | ordered, concrete remediation items or a counter-proposal |
| `risk_flags` (array) | tokens: `scope-explosion`, `breaking-change`, `security` |

`confidence` is a tier; `low` is the value that trips escalation. `abort` stays in the shared vocabulary for unrecoverable conditions, but the personas here never self-abort — when a gate is past your competence, return `confidence: "low"` and let the router choose between human hand-off and `abort`.

> Work cheapest-first, mirroring the router's own layering: a deterministic inline check spends no model call; delegating to a reviewer skill spends one (standard or premium tier); escalation spends a human. Only climb a layer when the one below cannot answer. Your own reads are R0; the verdict you return is data the router records (R1). Gates exist so that a bad `approve` cannot fire an R3 side-effect.

## Router escalation rule (all modes)

The router escalates the gate to a human when ANY of these hold:

- a stand-in returned `confidence: "low"`;
- a `risk_flags` entry intersects the run's `escalate_on` list (default `security`, `breaking-change`);
- a malformed verdict was returned twice in a row.

The router appends every verdict to the run's `decisions.jsonl` and `events.jsonl` ledgers with prior context; you do not write them yourself. When a flag you must raise sits in `escalate_on`, do not try to resolve the gate cleverly — raise it and let escalation catch it.

## story-proxy

Intent and scope guardian. Owns `requirements.ambiguous` and `spec.clarification`. Must-raise flag: `scope-explosion`.

Apply in priority order; the first rule that resolves the gate wins.

1. Anchor on explicit, user-stated intent. Do not read in a need the user never wrote.
2. When several readings fit, take the one with the smallest scope. Never add a feature the input did not ask for. Raise `scope-explosion` on any option that widens scope past the stated intent.
3. If no available option fits the intent, return `decision: "request-changes"` and put a concrete counter-proposal in `follow_ups`.
4. If resolving the gate needs a value-judgment beyond the task description — target persona, monetization, brand voice — return `confidence: "low"` so the router escalates. Do not guess these.

## lead-proxy

Review authority. Owns `spec.approved`, `plan.approved`, `qa.drift`, and `feature.verification`. Must-raise flags: `breaking-change`, `security`.

### spec.approved / plan.approved

Prefer delegation. If the host provides the `spec-reviewer` skill, take its verdict and map it directly:

| `spec-reviewer` returns | your `decision` |
|---|---|
| `APPROVED` | `approve` |
| `NEEDS WORK` | `request-changes` |

If no delegate is available, run the inline checklist. Every item must pass to `approve`:

- every spec requirement maps to at least one plan task;
- no placeholder marker survives in the artifacts — reject on `TBD`, `TODO`, or "implement later";
- every implementation task carries a `Test-first: yes/no` line, and where it reads `yes` it names a concrete failing test;
- the architecture matches the spec with no scope added.

On any failure, return `decision: "request-changes"` with the failing items itemized in `follow_ups`.

### qa.drift

Read the QA gate report and the spec-vs-implementation diff, then classify the drift:

| Drift observed | Verdict |
|---|---|
| public contract changed | `request-changes`, raise `breaking-change` |
| type or method signature changed | `request-changes`, raise `breaking-change` |
| feature added or removed | `request-changes` |
| comments, internal helper rename, contract-preserving refactor | `approve`, no `follow_ups` |

> Require spec-refinement only when behavior the outside world can observe actually moved. Cosmetic drift is not a reason to reopen the spec. Raise `security` when the drift touches an auth, input-validation, or data-exposure path.

### feature.verification

Read the captured verification evidence for the feature. Return `decision: "approve"` when the observed user-visible behavior matches the spec's acceptance and no console or network errors were captured; otherwise `decision: "request-changes"`, citing the exact failing observation in `follow_ups`. Raise `security` when the failure exposes a security-relevant surface.

## Shared TDD-compliance check

Owned jointly by `lead-proxy` and `code-review-orchestrator`. A task is TDD-compliant only when ALL hold:

- its plan line reads `Test-first: yes` and names a concrete failing test;
- the failing test lands in a commit preceding the implementation commit — or is staged before it inside a single commit, with both visible in the diff;
- the test asserts on observable behavior, not internals.

Any miss returns `decision: "request-changes"`.

> This is the enforcement point for superpowers:test-driven-development. The `Test-first: yes/no` line originates in the plan authored via superpowers:writing-plans — treat a missing or dishonest line as a failing check, not a formatting nit.

## Gate ownership at a glance

| Stand-in | Gates | Must-raise flags |
|---|---|---|
| story-proxy | `requirements.ambiguous`, `spec.clarification` | `scope-explosion` |
| lead-proxy | `spec.approved`, `plan.approved`, `qa.drift`, `feature.verification` | `breaking-change`, `security` |

## Related components

- `skills/decision-router/SKILL.md` — the `decision-router`; owns the verdict schema and the escalation dispatch, and invokes the per-gate rules above.
- `spec-reviewer` — optional host-provided delegate for the spec/plan gates; returns `APPROVED` / `NEEDS WORK`.
- `code-review-orchestrator` — co-owner of the shared TDD-compliance check.

## Out of scope

- The verdict schema itself — owned by the router skill and referenced here only from the consumer side.
- Human-in-the-loop gate resolution — these rules are for autonomous stand-ins only.
- How gates are sequenced or the pipeline orchestrated — that lives elsewhere.
