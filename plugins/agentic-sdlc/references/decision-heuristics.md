# Decision Heuristics for agentic-sdlc Stand-ins

This document encodes the decision rules each stand-in subagent uses when resolving a gate in autonomous mode. Stand-ins return verdicts in the format defined by `skills/decision-router/SKILL.md`.

## product-owner-stand-in

Used for `requirements.ambiguous` and `spec.clarification` gates.

**Rules (in priority order):**

1. **Maximize user-stated intent.** Prefer the option that most directly fulfills the explicit task description. Do not infer needs the user did not state.
2. **Minimize scope.** When two options both fit the intent, pick the smaller one. Never invent features.
3. **Counter-propose if no fit.** If none of the offered options fit, return `decision: "request-changes"` with a concrete counter-proposal in `follow_ups`.
4. **Defer ambiguity to the user.** If the answer requires a value-judgment outside the task description (e.g. target persona, monetization model, brand voice), return `confidence: "low"` so the router escalates.

**Risk flags this stand-in must raise:**

- `scope-explosion` — chosen option significantly broadens deliverables vs the task description.

## tech-lead-reviewer

Used for `spec.approved`, `plan.approved`, `qa.drift`, and `feature.verification` gates.

**For spec/plan approval:**

1. Invoke the `spec-reviewer` skill (if available in the host environment) on the artifact and use its `APPROVED` / `NEEDS WORK` verdict directly.
2. If `spec-reviewer` is unavailable, apply these checks inline:
   - Every spec requirement maps to at least one task in the plan.
   - No placeholders (`TBD`, `TODO`, "implement later") in the artifact.
   - Each implementation task in the plan has a `Test-first: yes/no` line; if `yes`, the failing test is described concretely.
   - Architecture matches the spec; no scope additions.
3. Verdict: `approve` if all checks pass; `request-changes` with itemized issues otherwise.

**For qa.drift:**

1. Read the QA gate report and the diff between spec and implementation.
2. Drift requires `spec-refinement` only if any of: public contract changed, types/method signatures changed, features added/removed.
3. Cosmetic drift (comments, internal helper names, refactor that preserves contracts) → `decision: "approve"` with no follow-up.

**Risk flags this stand-in must raise:**

- `breaking-change` — the artifact alters a public contract or migration-affecting schema.
- `security` — the artifact introduces a credential, network egress, file-system reach, or auth code path not covered by existing patterns.

## Escalation rule (autonomous mode)

The `decision-router` escalates to the human regardless of mode when **any** is true:

- The stand-in returned `confidence: "low"`.
- The stand-in raised a `risk_flags` entry that intersects the run's `escalate_on` list (default: `security`, `breaking-change`).
- The stand-in returned a malformed verdict twice in a row.

## TDD compliance check (used by tech-lead-reviewer and code-reviewer)

A task is TDD-compliant when:

- The task plan line shows `Test-first: yes` and a concrete failing-test description.
- In the diff, the failing test was added in a commit that precedes the implementation commit (or staged before the implementation in a single commit, with both visible in the diff).
- The test asserts on observable behavior, not on implementation internals.

A task that ships without these signals must be rejected with `decision: "request-changes"`.
