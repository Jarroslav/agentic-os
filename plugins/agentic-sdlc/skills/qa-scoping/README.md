# QA Planner

The pipeline's QA brain, in three passes: what this change must get right,
whether the tests that arrived actually check it, and what the repo now knows
about its own coverage. Each pass is a mode, and the pipeline picks the mode —
you never have to.

## Use It For

- Deciding, before code exists, which scenarios a change is not allowed to break
  — narrowed to the modules and risks this change actually touches.
- Reading the tests that came back and saying whether they would catch the thing
  they claim to catch.
- Keeping the coverage record honest run after run, instead of letting it drift
  into fiction.

## How To Ask

You don't. Something else calls it:

- `sdlc-engine` Phase 6 (`--checklist`), Phase 8 (`--review-tests`), Phase 11 (`--update`)
- `sdlc-brief` Stage 5 (`--checklist`), Stage 7 (`--review-tests`), Stage 10 (`--update`)

If the QA foundation isn't in place yet, that's the `qa-baseline` skill's job —
run it first and this one will have something to reason from.

## What It Produces

| Artifact | Mode | Location |
| --- | --- | --- |
| `qa-checklist.md` | `--checklist` | `<run-dir>/qa-checklist.md` |
| `qa-test-review.md` | `--review-tests` | `<run-dir>/qa-test-review.md` |
| Updated `qa-health.md` | `--update` | `.agentic/guides/testing/qa-health.md` |

Both documents follow `references/qa-artifacts.md`.

## What It Needs

- The QA foundation: `.agentic/guides/testing/qa-strategy.md` and
  `.agentic/guides/testing/qa-health.md`. Without them the skill halts rather
  than inventing a strategy — run `qa-baseline` to produce them.
- `--checklist` reads `<run-dir>/requirements.md`.
- `--review-tests` reads the `<run-dir>/qa-checklist.md` written by the first
  mode, so the two run in order or not at all.
