# Test Heal

Repairs failing tests whose failure is the test's own fault — brittle
selectors, stale fixtures, timing flakiness — and only those. Never touches
application code, never re-runs the suite (that stays with `qa-gates`), and
returns real regressions to the pipeline untouched. Ends every pass with a
machine-readable `## Loop Decision` the orchestrator uses to drive the
heal→re-run loop under a hard cap.

## Use It For

- Fixing test-side failures (`test_issue`, `flaky`) that block `qa-gates`.
- Stabilizing flaky tests properly (condition waits, isolation) instead of
  `.skip` or retries.
- Separating "the test is wrong" from "the app is wrong" before anyone
  burns a review round on the wrong one.

## How To Ask

Invoked automatically by `sdlc-pipeline` Phase 10 (autonomous mode) when
`qa-gates` fails on test-side causes. Directly:

- "Heal the failing tests on this branch."
- "These tests fail because of selectors, fix the tests not the app."

## What It Needs

- The `gate_plan` from `qa-gates` (runner and commands — it never re-detects).
- The failing tests with output excerpts (`qa-report.md` or pasted).
- An active feature branch to commit the test fixes on.
