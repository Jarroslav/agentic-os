---
name: decision-router
description: |-
  The one entry point every judgment gate in the SDLC flow calls through. Under hitl mode it always asks the user via AskUserQuestion — no deterministic shortcut, fast-path, or stand-in subagent substitutes for that. Under autonomous mode it tries cheap deterministic checks and fast-path approval first, falling back to a stand-in subagent only when needed. Every verdict, with its context, is recorded to decisions.jsonl and events.jsonl, and the escalation rule is enforced throughout.
version: 0.4.0
license: Apache-2.0
authors:
  - agentic-os
---

# decision-router

Settles a single gate decision, in either HITL or autonomous mode. Which mode is active determines the chain of resolution:

- **HITL judgment gates:** confirm the gate id is valid, then hand the question to the user. Nothing else stands in for the user here — no fast-path, no deterministic approval, no subagent stand-in.
- **Autonomous judgment gates:** work through the three resolution paths below, cheapest first.

1. **Deterministic** — a structural pass/fail check that needs no model call.
2. **Fast-path** — the risk classifier already flagged this as low-risk, so approve without dispatching a subagent.
3. **Subagent** — hand full context to whichever stand-in agent matches the gate.

Every call returns a verdict in the canonical shape below, and every call appends an entry to `decisions.jsonl` plus a matching `decision.recorded` event to the run's `events.jsonl` (best-effort) — carrying along the context that was used to either ask the question or resolve it outright.

## Inputs

```
{
  gate_id:   "requirements.ambiguous" | "spec.clarification" | "spec.approved"
           | "plan.approved" | "code-review.final" | "code-review.check" | "qa.drift"
           | "feature.verification",
  question:  "<natural-language prompt>",
  options?:  ["<MCQ option 1>", "..."],
  context: {
    task:         "<original task>",
    artifacts:    "<ArtifactRefs — see sdlc-pipeline>",
    phase:        <integer>,
    risk_flags:   ["security" | "breaking-change" | "scope-explosion"],
    memory_brief: "<slice from .agents/memory/sdlc/>",
    fast_path?:   { "reason": "<low-risk classification description>" }
  },
  mode:      "hitl" | "autonomous",
  run_dir:   "<absolute path>",
  escalate_on: ["security", "breaking-change", ...]
}
```

## Gate -> stand-in mapping (autonomous, subagent path)

| Gate ID | Subagent |
|---------|----------|
| `requirements.ambiguous` | `product-owner-stand-in` |
| `spec.clarification` | `product-owner-stand-in` |
| `spec.approved` | `tech-lead-reviewer` |
| `plan.approved` | `tech-lead-reviewer` |
| `code-review.final` | `code-reviewer` |
| `code-review.check` | `code-reviewer` |
| `qa.drift` | `tech-lead-reviewer` |
| `feature.verification` | `tech-lead-reviewer` |

`qa.ready` never goes through this routing table — the pipeline works it out deterministically instead. It's only emitted once feature-verification has either been skipped (nothing user-visible changed) or has come back with `verified: true`. There is no path from a user-visible change to handoff that skips recorded verification evidence.

## Resolution order

### Step 1 — HITL mode short-circuit

When `mode === "hitl"`, start by treating an unrecognized `gate_id` as a structural failure, not a judgment call, and reject it outright. Every gate_id that IS a recognized judgment gate gets a call to `AskUserQuestion`, passing `question`, `options`, and a compact bundle of prior context pulled from `context` — the task, artifact refs/summaries, phase, risk flags, a memory brief summary, and any `fast_path` hint that happens to be set. Translate whatever the user picks into:

```json
{ "decision": "<user selection>", "rationale": "(provided by user)", "follow_ups": [], "confidence": "high", "source": "hitl" }
```

Nothing further in the chain runs after this: no deterministic evidence check, no reading of `context.fast_path`, no subagent dispatch — HITL mode never touches any of those. Write the same prior context to both `decisions.jsonl` and `events.jsonl`, then return.

### Step 2 — Autonomous: deterministic verification check

#### For `gate_id === "feature.verification"`:

1. Load every file under `<run_dir>/evidence/verification/*.json` along with `<run_dir>/feature-verification-plan.json`.
2. **If `feature-verification-plan.json` reports `tool: "unconfigured"`** AND some verification-evidence file has `result: "BLOCKED"` → return `request-changes` with `follow_ups: ["install Playwright or configure feature_verification.command"]`. Treat this as a hard escalation even in autonomous mode — shipping UI with no verification tooling in place is a genuine engineering failure, not a formality to wave through.
3. **If any per-feature evidence has `result: "FAIL"`** → `request-changes` with `follow_ups: [<console_errors>, <network_failures>]`, so the follow-up fix-up task has something concrete to retry against.
4. **If any per-feature evidence has `result: "INCONCLUSIVE"`** (say, a test that exists but only confirms the page loads) → `request-changes` with `follow_ups: ["expand the verification test to cover the changed behavior"]`.
5. **If any per-feature evidence is missing `screenshot_path`** → `request-changes` (a PASS without a screenshot receipt isn't a PASS).
6. **Every evidence file is PASS, screenshots are all present, console errors and network failures are both zero, and no risk flags apply** → return a deterministic `approve`, log it, stop here.
7. **Every evidence file is PASS but risk flags are present anyway** → don't stop; move on to Step 4 so a subagent can read the evidence and confirm the scope is really as safe as it looks.

Step 2 does nothing for any gate other than `feature.verification` — for those, skip straight to Step 3 or Step 4.

### Step 3 — Fast-path approval (autonomous)

When `context.fast_path` is set — meaning the pipeline already classified this gate as low-risk upstream — return:

```json
{ "decision": "approve",
  "rationale": "<context.fast_path.reason>",
  "follow_ups": [],
  "confidence": "high",
  "verdict.source": "fast-path" }
```

No subagent gets dispatched for this path. Log it and return.

### Step 4 — Subagent dispatch (autonomous)

Dispatch whichever subagent the mapping table names, via the Agent tool, with:

- `description`: a short summary that includes the `gate_id`
- `prompt`: the complete inputs block (task, question, options, **artifacts as ArtifactRefs**, memory_brief, phase, risk_flags). Hand over paths and summaries — never inline the raw spec/plan bodies themselves.

Parse whatever the subagent prints to stdout as JSON. If that parse fails, retry once with a prompt that demands stricter formatting. If it fails a second time, escalate straight to the user via an HITL prompt, no matter which mode is running.

Tag the resulting verdict with `verdict.source: "subagent"`.

## Review round contract

`code-review.final` is the only gate that reviews the full diff. It's handed the review bundle assembled by `sdlc-pipeline` and comes back with findings, each carrying a stable ID.

`code-review.check` is narrower — a targeted recheck. It's handed the original finding IDs, the fix-up diff, and the fix-up evidence, and its job is just to confirm those specific findings got resolved. It must not restart a full review from scratch unless the fix-up diff itself introduces a new high-risk flag.

## Evidence schema (validated by sdlc-pipeline before review)

```json
{
  "schema": 1,
  "task_id": "<id>",
  "test_first": <boolean>,
  "failing_test_command": "<string>",
  "failure_excerpt": "<string, ~500 chars>",
  "implementation_summary": "<string>",
  "passing_command": "<string>",
  "passing_excerpt": "<string, ~500 chars>",
  "files_touched": ["<path>", "..."],
  "diff_lines_added": <integer>,
  "diff_lines_removed": <integer>
}
```

Required fields: `schema`, `task_id`, `test_first`, `failing_test_command`, `failure_excerpt`, `passing_command`, `passing_excerpt`, `files_touched`. If any of these is absent, the verdict is `request-changes`.

## Verdict shape (always)

```json
{
  "decision": "approve | request-changes | abort | <option-text>",
  "rationale": "<1-3 sentences>",
  "follow_ups": ["<optional items>"],
  "confidence": "high | medium | low",
  "risk_flags": ["<optional flags>"],
  "source": "hitl | deterministic | fast-path | subagent"
}
```

## Escalation rule

Once Step 4 (the subagent path) produces a verdict, kick it back up to the user — call AskUserQuestion regardless of which mode is active — if **any** of these hold:

- `verdict.confidence === "low"`
- `verdict.risk_flags ∩ inputs.escalate_on !== ∅`
- The subagent returned malformed JSON twice in a row

Whatever the user answers overrides the subagent's verdict and becomes the recorded decision — tagged `source: "hitl"`, with a `prior_subagent_verdict` field kept alongside it for the audit trail.

Verdicts from Step 2 (deterministic evidence) and Step 3 (fast-path) never go through this escalation check — they're either plain facts or were already pre-classified by the pipeline upstream.

## Audit log

Append a single line to `<run_dir>/decisions.jsonl`:

```json
{"ts":"<ISO>","gate_id":"<id>","mode":"<mode>","verdict":{...},"escalated":<bool>,"prior_context":{...}}
```

`prior_context` must carry enough detail that someone could later reconstruct why the question was asked, or why it resolved the way it did: `question`, `options`, `context.phase`, `context.risk_flags`, artifact refs (paths, summaries, signatures), `context.fast_path` when present, and any prior autonomous verdict that HITL escalation ended up overriding. Don't inline whole multi-page artifacts here.

Also append a line to `<run_dir>/events.jsonl`, following the run event ledger contract defined by `sdlc-pipeline`:

```json
{
  "schema": 1,
  "ts": "<ISO>",
  "event": "decision.recorded",
  "run_id": "<id>",
  "phase": <context.phase>,
  "actor": "decision-router",
  "summary": "Decision recorded for <gate_id>: <decision>",
  "artifacts": ["decisions.jsonl"],
  "data": {
    "gate_id": "<id>",
    "mode": "<mode>",
    "decision": "<verdict.decision>",
    "source": "<verdict.source>",
    "escalated": <bool>,
    "prior_context": {
      "question": "<question>",
      "options": ["<option>", "..."],
      "phase": <context.phase>,
      "risk_flags": ["<flag>", "..."],
      "artifact_refs": ["<path-or-ref>", "..."],
      "fast_path": "<context.fast_path if supplied>",
      "prior_autonomous_verdict": "<subagent/deterministic verdict if overridden>"
    }
  }
}
```

If either file fails to write, log a warning to stderr and keep going — decision logging must never be what blocks the pipeline. When `decisions.jsonl` or `events.jsonl` entries turn up missing or malformed, `sdlc-status` surfaces them as audit warnings, not as run failures.

## Output

Return the verdict object back to whoever called this skill.

## Constraints

- Always log a `decisions.jsonl` entry and its matching `events.jsonl` `decision.recorded` event, on a best-effort basis.
- Never modify the input artifacts — this skill only decides, it doesn't edit.
- An unrecognized `gate_id` returns `decision: "abort"` with `rationale: "unknown gate"` and `confidence: "low"`, forcing an escalation.
- In HITL mode, every known judgment gate always asks the user and records `source: "hitl"` — fast-path, deterministic approval, and subagent approval are all off-limits for those gates in autonomous mode's sense.
- Steps 2 and 3 never dispatch a subagent and never spend tokens on a model call.
