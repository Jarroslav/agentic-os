# decision-router

Shared gate-resolution helper. It does not run phases itself — `sdlc-pipeline`, `sdlc-task`, and other orchestrating skills call it every time their flow hits a judgment gate, and it hands back a verdict plus an audit record.

## Use It For

- Resolving a single judgment gate decision — `spec.approved`, `plan.approved`, `code-review.final`, and other gate ids defined in the pipeline's gate contract.
- Keeping one consistent, auditable verdict trail no matter which path produced the decision: a human in hitl mode, or an automated/subagent path in autonomous mode.
- Forcing escalation on any decision flagged low-confidence or high-risk — in either mode.

> This skill is infrastructure. You don't call it by name; it's invoked internally at each gate inside `sdlc-pipeline` and `sdlc-task` runs.

## How To Ask

You don't ask for this directly — there's nothing to type. What you'll see depends on the run's mode:

- **hitl mode** — the pipeline stops and prompts you for a decision at each judgment gate. Answer it; your response becomes the recorded verdict.
- **autonomous mode** — gates resolve without prompting you. The exception is `code-review.final` and similarly judgment-heavy gates, which get routed to a subagent stand-in instead of a human. You'll only be pulled in if a decision is flagged low-confidence or high-risk — escalation happens regardless of mode.

## What It Needs

| Input | Required | Notes |
|---|---|---|
| `gate_id` | yes | Which gate is being resolved, e.g. `spec.approved`, `plan.approved`, `code-review.final` |
| `mode` | yes | `hitl` or `autonomous` — selects the resolution path |
| `run_dir` | yes | Absolute path to the current run's state directory |
| `context` | yes | Task description, artifact refs, phase number, and risk flags for the decision |

Every resolved verdict is appended to two audit files under the run directory:

| Output | Format |
|---|---|
| `decisions.jsonl` | Append-only verdict log |
| `events.jsonl` | Append-only event log |

> Callers supply all four inputs per call. `decision-router` doesn't define the full gate catalog or the schema of `context` beyond these four fields — that lives with the orchestrating skill.
