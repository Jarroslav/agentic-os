# QA Planner

Per-feature QA planning and review. Operates in three modes invoked automatically by the pipeline — generating a checklist before implementation, reviewing written tests for quality, and updating the health snapshot after QA gates pass.

## Use It For

- Generating a `qa-checklist.md` scoped to the feature being built, covering affected modules, risk flags, and known coverage gaps.
- Reviewing new and changed tests against the checklist to catch missing scenarios or weak assertions.
- Keeping `qa-health.md` current after each feature run.

## How To Ask

This skill is invoked automatically:

- `sdlc-pipeline` Phase 6 (`--checklist`), Phase 8 (`--review-tests`), Phase 11 (`--update`)
- `sdlc-task` Stage 5 (`--checklist`), Stage 7 (`--review-tests`), Stage 10 (`--update`)

It is not intended for direct user invocation. If you need to set up the QA foundation first, run the `qa-foundation` skill.

## What It Produces

| Artifact | Mode | Location |
| --- | --- | --- |
| `qa-checklist.md` | `--checklist` | `<run-dir>/qa-checklist.md` |
| `qa-test-review.md` | `--review-tests` | `<run-dir>/qa-test-review.md` |
| Updated `qa-health.md` | `--update` | `.agentic/guides/testing/qa-health.md` |

## What It Needs

- `.agentic/guides/testing/qa-strategy.md` and `.agentic/guides/testing/qa-health.md` must exist. Run the `qa-foundation` skill to generate them.
- `<run-dir>/requirements.md` must exist for `--checklist` mode.
- `<run-dir>/qa-checklist.md` must exist for `--review-tests` mode.
