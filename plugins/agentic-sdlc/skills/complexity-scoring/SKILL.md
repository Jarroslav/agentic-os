---
name: complexity-scoring
description: |-
  A thin gate in front of the complexity-assessor agent: only calls it when the pipeline's own heuristics can't confidently classify the task. Returns a normalized {score, routing, breakdown}; a 6-14 score skips straight to writing-plans, 15-36 goes through brainstorming first.
version: 0.2.0
license: Apache-2.0
authors:
  - agentic-os
---

# complexity-scoring

Hands the current task off to the bundled `complexity-assessor` agent and returns a normalized result. When cheap heuristics already produce a high-confidence route, the pipeline can bypass this skill altogether.

## Inputs

- `task_description` — verbatim from Phase 1 requirements-intake output
- `feature_area` — short keyword summary (e.g. "provider integration SSO")
- `repo_path` — absolute path to the current checkout

## Behavior

Call the Agent tool with `subagent_type: complexity-assessor`, passing:

```
task_description='<input>'
feature_area='<input>'
```

Take the agent's structured output and normalize it to:

```json
{
  "score": <integer 6..36>,
  "breakdown": {
    "component_scope": <1..6>,
    "requirements_clarity": <1..6>,
    "technical_risk": <1..6>,
    "file_change_estimate": <1..6>,
    "domain_familiarity": <1..6>,
    "review_burden": <1..6>
  },
  "routing": "writing-plans" | "brainstorming" | "split-required",
  "rationale": "<verbatim from agent>"
}
```

Routing thresholds:

- score 6..14 → `writing-plans` (skip Phase 4 brainstorming)
- score 15..36 → `brainstorming` (Phase 4 produces design doc, then writing-plans)
- agent flags `SPLIT REQUIRED` → `split-required` (pipeline halts; user must decompose)

## Output

Write to `<run_dir>/complexity.json` and return the parsed object.

## Constraints

- Once this skill is invoked, leave the actual scoring to the agent rather than judging complexity yourself — heuristic routing is `sdlc-pipeline`'s job, not this skill's.
- If the agent's output comes back malformed, retry once with a stricter format prompt. A second failure falls back to score=18 (Medium) with `routing: brainstorming` as the safe default, with `rationale` noting that the fallback fired.
