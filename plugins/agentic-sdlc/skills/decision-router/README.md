# Decision Router

Resolves judgment gate decisions in either human-in-the-loop (HITL) or autonomous mode, recording every verdict to the run audit trail in `decisions.jsonl` and `events.jsonl`.

## Use It For

- Routing spec and plan approval gates to the user in HITL mode.
- Delegating code review to a subagent stand-in in autonomous mode.
- Escalating low-confidence or high-risk decisions regardless of mode.
- Providing a consistent, auditable approval record for every judgment gate.

## How To Ask

This skill is invoked automatically by `sdlc-pipeline`, `sdlc-task`, and related skills at each judgment gate. It is not normally called directly.

## What It Needs

- `gate_id` — one of the defined gate identifiers (e.g. `spec.approved`, `plan.approved`, `code-review.final`).
- `mode` — `hitl` or `autonomous`.
- `run_dir` — absolute path to the current run state directory.
- `context` — task description, artifact refs, phase number, and risk flags.
