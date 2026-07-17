---
name: decision-router
description: Invoke this skill whenever an SDLC pipeline phase reaches a judgment gate and needs a resolved, logged verdict — spec approval, plan approval, QA drift, code review (final or check round), requirements ambiguity, spec clarification, or feature verification. Trigger phrases include "resolve this gate", "route this decision", "get a verdict for <gate_id>", "who approves this", "check the escalation rule", or "record this to decisions.jsonl". It is the single entry point for every recognized gate id in both hitl and autonomous modes. Do not invoke it for the `qa.ready` signal — that stays deterministic inside the calling pipeline and never enters this router's table.
---

# decision-router

Single shared resolver for every judgment gate in the SDLC pipeline. Given a gate id and a mode
(`hitl` or `autonomous`), it decides *how* the gate gets settled — human question, deterministic
check, fast-path approval, or dispatched stand-in reviewer — always returns one fixed verdict
shape, and durably records the outcome even when the normal resolution path fails.

> This skill decides and logs. It never edits a spec, plan, diff, or evidence file, and it never
> runs review-lens subagents itself — those live one level down, inside `code-review-orchestrator`.

## Operating modes

| Mode | Behavior |
|---|---|
| `hitl` | Every recognized gate goes to `AskUserQuestion`. No fast-path, deterministic shortcut, or stand-in substitutes for the human's answer. The two code-review gates are the one carve-out: run the inline `code-review-orchestrator` skill first to produce a report, then ask the human — the report informs the question, it never resolves the gate on its own. |
| `autonomous` | Resolution tries cheapest-first: deterministic check → pre-classified fast-path → dispatched stand-in subagent. Code-review gates are pinned to the inline skill and never fall through to fast-path or stand-in dispatch. |

An unrecognized gate id is a structural error in either mode, not a judgment call: reject
immediately, decision `abort`, confidence `low`, escalation forced.

## Gate catalog

`gate_id` is a frozen, shared-contract enum. Reuse these ids verbatim — never invent new ones,
never abbreviate them.

| Gate ID | Resolver | Kind |
|---|---|---|
| `requirements.ambiguous` | `story-proxy` | subagent |
| `spec.clarification` | `story-proxy` | subagent |
| `spec.approved` | `lead-proxy` | subagent |
| `plan.approved` | `lead-proxy` | subagent |
| `code-review.final` | `code-review-orchestrator` | skill (inline) |
| `code-review.check` | `code-review-orchestrator` | skill (inline) |
| `qa.drift` | `lead-proxy` | subagent |
| `feature.verification` | `lead-proxy` | subagent |

Three additional ids are recognized (valid for hitl's Step 1 and for the unrecognized-gate check)
but carry no resolver row: `classification.confirm`, `qa-checklist.approved`, `qa-tests.approved`.
In autonomous mode they have no stand-in to dispatch to — they resolve only through the
deterministic/fast-path steps upstream of dispatch.

A related but separate id, `qa.ready`, is never routed through this skill at all — see Non-goals.

## Resolution steps (autonomous mode, cheapest-first)

| Step | Applies in | Dispatches a subagent? | Spends a model call? | Subject to escalation rule? |
|---|---|---|---|---|
| 0 — code-review, inline skill | both modes | no (Skill tool, not Agent tool) | yes | yes, per its own sub-rules |
| 1 — HITL short-circuit | hitl only | no | n/a — human is final | n/a |
| 2 — deterministic evidence | autonomous, `feature.verification` only | no | no | no |
| 3 — fast-path | autonomous | no | no | no |
| 4 — stand-in dispatch | autonomous | yes | yes | yes |

Order of evaluation:

1. **Code-review gate?** Run Step 0 in both modes; never fast-pathed, never dispatched as a
   stand-in, in either mode.
2. **Mode is `hitl`?** Ask the human directly (Step 1). Skip everything below.
3. **Mode is `autonomous`, gate is `feature.verification`?** Apply the deterministic evidence
   sub-rules (Step 2) before considering fast-path or dispatch.
4. **Fast-path hint present** (`context.fast_path`) and gate is not code-review? Approve without
   dispatch (Step 3).
5. **Otherwise, gate is dispatchable?** Send full context to the mapped stand-in via the Agent
   tool (Step 4). Parse its stdout as JSON. Retry once on parse failure. A second parse failure
   escalates to the human regardless of mode.

Deterministic and fast-path outcomes skip the escalation rule entirely — they are either plain
facts already verified upstream, or pre-vetted approvals; only stand-in- and orchestrator-produced
verdicts need the escalation check.

## `feature.verification` deterministic sub-rules (autonomous only, in order)

Read `<run_dir>/feature-verification-plan.json` and `<run_dir>/evidence/verification/*.json`
(each evidence file carries `result` — `PASS|FAIL|INCONCLUSIVE|BLOCKED` — and `screenshot_path`).
Evaluate in this order, stopping at the first match:

1. Verification tool is `"unconfigured"` **and** any evidence result is `BLOCKED` → `request-changes`.
   This is a hard escalation even though the mode is autonomous.
2. Any evidence `result` is `FAIL` → `request-changes` with concrete follow-ups.
3. Any evidence `result` is `INCONCLUSIVE` → `request-changes`, asking for expanded coverage.
4. Any evidence entry is missing its `screenshot_path` artifact → `request-changes`.
5. All `PASS`, all screenshots present, zero console/network errors, no risk flags → deterministic
   `approve`. Stop here — do not fall through to stand-in dispatch.
6. All `PASS` but risk flags are present → do not stop; continue to Step 4 (stand-in dispatch) for
   confirmation.

## Escalation rule

Force any stand-in- or orchestrator-produced verdict back to a human question (`AskUserQuestion`)
when any of the following hold:

- `confidence` is `low`.
- The verdict's `risk_flags` intersect the caller-supplied `escalate_on` list.
- The stand-in returned unparseable output twice in a row (second parse failure).

The full escalation predicate — including how risk-flag intersection is computed and how the
"low confidence" threshold is read off a stand-in's structured return — is authored once in
`references/decision-heuristics.md`; do not re-derive it ad hoc, follow that reference.

## Human override and audit trail

A human's answer always wins and is tagged as the authoritative decision — even one delivered
after an automated verdict was already produced (e.g., the code-review report informed a human
answer, or an escalation surfaced a stand-in's low-confidence call). The superseded automated
verdict is preserved for audit under a resolver-specific field, never the reverse:

- `prior_subagent_verdict` — for gates resolved by a dispatched stand-in (`story-proxy`, `lead-proxy`).
- `prior_orchestrator_verdict` — for the two code-review gates, resolved by the inline
  `code-review-orchestrator` skill.

## Code-review gates (special case)

`code-review.final` and `code-review.check` never reach fast-path or stand-in dispatch, in either
mode, because the resolver itself needs to fan out further sub-work (parallel review-lens
subagents) that a single dispatched stand-in cannot do. Resolve them by invoking the
`code-review-orchestrator` skill inline via the **Skill tool** — never the Agent tool — passing:

- `gate_id`
- `original_task`
- `artifacts` — review bundle, diff/`diff_base`, spec/story, project guides, evidence summaries,
  optional QA report
- `memory_brief`
- `run_dir`
- on `code-review.check` only: `prior_verdict` — the full prior verdict object, or an ArtifactRef
  to `<run_dir>/code-review-final.json`. The orchestrator safe-fails without it.

`code-review.final` evaluates the whole change. `code-review.check` is a narrow re-verification of
previously identified findings plus their fix — it should not restart a full review unless the fix
itself introduces new high-risk concerns.

If the orchestrator produces no usable verdict, write the canonical safe-fail object in its place
(see Persistence below) rather than leaving the gate undecided.

## Inputs

| Field | Notes |
|---|---|
| `gate_id` | one of the enum values above |
| `question` | human-readable prompt, used verbatim by `AskUserQuestion` and carried into the event ledger |
| `options?` | optional choice list; when present, `decision` may be `<option-text>` instead of `approve/request-changes/abort` |
| `context.task` | grounding context for the gate |
| `context.artifacts` | ArtifactRefs — paths/summaries, never inlined bodies |
| `context.phase` | pipeline phase, carried into `events.jsonl` |
| `context.risk_flags` | flags checked against `escalate_on` |
| `context.memory_brief` | read from the per-role memory store |
| `context.fast_path?.reason` | presence alone triggers Step 3 (non-code-review gates only) |
| `mode` | `hitl` \| `autonomous` |
| `run_dir` | run-scoped directory all persisted files below are relative to; conventionally a run's directory under `.agentic/` |
| `escalate_on` | caller-supplied risk-flag list for the escalation rule |

## Outputs — verdict object

| Field | Notes |
|---|---|
| `decision` | `approve` \| `request-changes` \| `abort` \| `<option-text>` |
| `rationale` | grounded in `context` and any resolver output — never invented |
| `follow_ups` | concrete next actions, if any |
| `confidence` | `high` \| `medium` \| `low` |
| `risk_flags` | flags surfaced by the resolver |
| `source` | `hitl` \| `deterministic` \| `fast-path` \| `subagent` |

Code-review verdicts carry additional fields: `business_review`, `standards_review`, `findings`,
and on check rounds `finding_status`. Internally these are tagged `verdict.source: "skill"` when
produced autonomously by the orchestrator, or `"hitl"` when the orchestrator's report was
human-reviewed.

## Persistence

Every gate resolution appends one record to the decision log and one matching event to the run
ledger, best-effort — a write failure here must never block the pipeline.

**`<run_dir>/decisions.jsonl`** — append-only, one line per call:
```json
{"ts":"<ISO>","gate_id":"<id>","mode":"<mode>","verdict":{...},"escalated":<bool>,"prior_context":{...}}
```

**`<run_dir>/events.jsonl`** — append-only, contract owned by the pipeline orchestrator, event name
`decision.recorded`:
```json
{
  "schema": 1, "ts": "<ISO>", "event": "decision.recorded", "run_id": "<id>",
  "phase": <context.phase>, "actor": "decision-router",
  "summary": "Decision recorded for <gate_id>: <decision>",
  "artifacts": ["decisions.jsonl"],
  "data": {
    "gate_id": "<id>", "mode": "<mode>", "decision": "<verdict.decision>",
    "source": "<verdict.source>", "escalated": <bool>,
    "prior_context": {
      "question": "<question>", "options": ["<option>", "..."],
      "phase": <context.phase>, "risk_flags": ["<flag>", "..."],
      "artifact_refs": ["<path-or-ref>", "..."],
      "fast_path": "<context.fast_path if supplied>",
      "prior_autonomous_verdict": "<subagent/deterministic verdict if overridden>"
    }
  }
}
```

**`<run_dir>/code-review-final.json`** — final-round verdict, written by the orchestrator or, on
failure, by the safe-fail path below.

**`<run_dir>/code-review-check.json`** — check-round verdict, same rule.

**Canonical code-review safe-fail verdict** — written in place of a missing verdict, verbatim:
```json
{ "decision": "request-changes", "rationale": "<why the review could not run>", "confidence": "low",
  "risk_flags": [], "business_review": [], "standards_review": [], "findings": [] }
```
Add `"finding_status": []` on the check round. No wrapper fields (`source`, `follow_ups`,
`escalated`) belong inside this object — those live only in the `decisions.jsonl` entry.

## Evidence schema (validated upstream, before this skill sees it)

```json
{
  "schema": 1, "task_id": "<id>", "test_first": <boolean>,
  "failing_test_command": "<string>", "failure_excerpt": "<string, ~500 chars>",
  "implementation_summary": "<string>", "passing_command": "<string>",
  "passing_excerpt": "<string, ~500 chars>", "files_touched": ["<path>", "..."],
  "diff_lines_added": <integer>, "diff_lines_removed": <integer>
}
```
Required subset — missing any forces `request-changes`: `schema`, `task_id`, `test_first`,
`failing_test_command`, `failure_excerpt`, `passing_command`, `passing_excerpt`, `files_touched`.

## Dispatch and interaction mechanics

- **Stand-in dispatch** (non-code-review gates): use the **Agent tool**. Pass `description`
  (include the `gate_id`) and `prompt` (the full inputs block; artifacts as ArtifactRefs — paths
  or summaries, never inlined bodies). Parse the returned stdout as JSON; retry once on parse
  failure; escalate on a second failure.
- **Code-review gates**: use the **Skill tool** to invoke `code-review-orchestrator` inline — see
  Code-review gates above. This step spends a model call, same as a stand-in dispatch, but never
  runs as a dispatched subagent.
- **Human interaction**: `AskUserQuestion`, passed `question`, `options`, and a compact bundle
  drawn from `context`.

## Blast radius

R1 — run-artifact writes only. This skill appends to `decisions.jsonl` and `events.jsonl` under
`run_dir` and, for code-review gates, writes the verdict JSON files listed above. It never writes
repo files (R2) and never triggers external side effects (R3); it only reads upstream artifacts
(evidence files, verification plan) and resolver output before recording a decision.

## Non-goals

- Does not run review-lens subagents, write code, or generate specs/plans — it only routes to
  resolvers and records outcomes.
- Does not modify any input artifact (spec, diff, evidence, verification plan) — decision-only.
- Does not decide the `qa.ready` signal. That stays out of this routing table entirely — the
  calling pipeline decides it deterministically once verification work is done or skipped, and
  nothing reaches hand-off without recorded verification proof for user-visible changes.
- Does not allow any autonomous shortcut — fast-path, deterministic, or stand-in — to substitute
  for a human answer on a recognized gate when `mode` is `hitl`.
- Does not let the two code-review gates reach fast-path or stand-in dispatch, in either mode.

## Cross-skill dependencies

- **`sdlc-pipeline`** — assembles gate inputs (review bundle, ArtifactRefs, `memory_brief`), owns
  the `events.jsonl` ledger contract, decides `qa.ready` deterministically, and surfaces
  malformed or missing `decisions.jsonl`/`events.jsonl` entries as audit warnings (via a companion
  `sdlc-status` capability) rather than run failures.
- **`code-review-orchestrator`** — the skill invoked inline at Step 0; runs three parallel
  review-lens subagents itself, adjudicates standards/security, triages, and persists the verdict
  file.
- **Stand-in resolvers** — `story-proxy` (requirements/clarification gates), `lead-proxy`
  (spec/plan/drift/verification gates).
- **Memory** — reads `memory_brief` from the per-role memory store under `.agents/memory/sdlc/`.

## References tree

- `references/decision-heuristics.md` — the authoritative escalation predicate: how confidence
  levels are read from a resolver's structured return, how `risk_flags` intersection against
  `escalate_on` is computed, and how the two-strikes malformed-output rule is counted across a
  retry. Consult it before hand-rolling escalation logic anywhere else in the pipeline.
