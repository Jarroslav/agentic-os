# Approved staging amendment

Approved by the operator in this task on 2026-09-20 ("approved, continue").
This amendment now governs execution order. It does not reset review budgets.

## Problem

The current Stage 0 gate requires a complete, independently observable evaluation
of coordination, messaging, recovery, installation and host enforcement before
implementation of the runtime and host adapters in Stages 1–6. The baseline has
mostly skill instructions and artifact validators. The evaluation harness still
lacks observation channels for most assertions. The host adapters also need
actual startup/authentication/hook certification; offline filesystem canaries
alone cannot establish this.

No live trials have run. No numerical baseline grade exists. The existing
experimental evaluator must not be represented as ready.

## Proposed change to ordering

1. Before framework changes, archive the original baseline commit and dependency
   snapshots. Freeze the 25 assertion definitions, weights, four scenario task
   specifications, fixture inputs, fault cases, acceptance thresholds and
   evaluation budget. Independently review these definitions for neutrality.
2. Implement Stages 1–6 on the existing branch, keeping their separate commits,
   exact-tree blind reviews and two-remediation-cycle limits. Develop the
   observation adapters alongside the product interfaces they observe. Treat
   incomplete host certification as an explicit limitation, not a passing check.
3. Before any scored live trial, finish and independently review the executable
   observers and host certification. Freeze that single evaluator. It must
   support behavior observations against both original legacy source and the
   candidate; absent capabilities remain unverified. It must not award points
   for merely possessing the new runtime or SQLite files.
4. Run the 24 baseline trials against the original immutable snapshot, then the
   24 candidate trials against the reviewed candidate snapshot, using identical
   frozen evaluator, tasks, permissions and compatible dependency snapshots.
   Baseline runs occur later chronologically; they still execute original code.
5. Apply all original final acceptance criteria. If reliable host observation
   remains unavailable, report an incomplete result and do not claim acceptance.

This explicitly changes the requirement that all 24 baseline trials finish
before Stage 1. It does not claim Stage 0 has passed under the original plan.
The original review findings and consumed remediation cycle remain recorded.

## What does not change

- Branch `codex/framework-reliability`; original baseline
  `dabd182e049cc6fb52007da988bf03762130c459`.
- Python 3.10+, SQLite, canonical contracts, read-only product MCP server,
  bounded dispatch/retry/message policies, and existing SDLC/QA scope.
- 48 scored live trials, 900 seconds each; additional model trials require a
  budget extension. No uncounted model smoke tests.
- Five dimensions, 25 assertions, 100 points; at least 90 per host and 16 per
  dimension; all critical vetoes; unexecuted assertions earn no points.
- No silent fixture, rubric, permission or observer changes between baseline
  and candidate. A mismatch invalidates comparability; no automatic reruns.
- Fresh blind reviews and required CI, content-index, changelog and originality
  checks. No publishing, merging, release, or fabricated completion claims.

## Tradeoff

This permits implementation to progress while the evaluation adapters mature.
It increases the risk that observer implementation is influenced by candidate
code. Frozen behavioral definitions, independent review, legacy compatibility,
negative controls and one identical final evaluator mitigate that risk. They do
not eliminate it, which is why this ordering change needs explicit approval.
