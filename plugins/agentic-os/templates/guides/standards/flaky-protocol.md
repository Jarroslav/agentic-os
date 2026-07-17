# Flaky / Red Test Protocol (Binding Runbook)

<!-- Scaffolded by agentic-os to .agentic/guides/standards/flaky-protocol.md.
     Single source of truth for how humans and AI agents act on ANY red or
     flaky test. Triage entry point: the test-failure-triage agent.
     Live ledger: docs/flaky-ledger.md (create on first use). -->

## The protocol

1. **Reproduce once, retries off.** Run the failing test solo with retries
   disabled, routed to its correct project/suite. (Whether the agent may run
   it, or must hand the command to a human/CI, is set by the autonomy matrix
   in `../policy/ai-policy.md`.)
2. **Classify** — TIMING / SELECTOR / DATA / ASSERTION-LOGIC / ENV, plus two
   integration-suite classes: **SHARED-STATE** (another suite mutated the
   same shared state — check ownership first) and **PROPAGATION** (mutation
   issued but not yet observable — async caches, eventual consistency).
   Decision signals live in the test-failure-triage agent contract.
3. **Ledger row before any fix** in `docs/flaky-ledger.md`: spec, work-item
   ID, cause class, evidence (error line + artifact path), proposed fix,
   target layer. Falsified hypotheses stay in the row — they save the next
   person hours.
4. **Fix at root cause — never weaken an assertion to pass.** Use traces,
   snapshots, and the application source before proposing a fix. If two
   fixes fail, question the frame, not the locator.
5. **Quarantine** (a `@flaky`-style tag) is allowed ONLY for ENV/product
   causes and MUST carry a linked bug in the tracker plus an expiry
   condition in its ledger row. No expiry, no tag.
6. **Product bug** → file it in the tracker (via the work-item-creator agent,
   human-gated), linked to the failing test case. The test stays
   red-by-design or is quarantined per rule 5 — it is never adjusted to
   paper over the product.
7. **Flake budget**: CI may keep retries on, but every passed-on-retry test
   gets a ledger row within the same week. Retries hide flakiness from the
   report, not from the ledger.

## ENV fast-paths (check BEFORE deep-diving code)

Operational characteristics of the test environment explain whole failure
classes. Keep a repo-specific list here as they are discovered (transient
5xx during autoscaling, scheduled data resets leaving empty catalogs, auth
state older than its TTL, saturation under full-suite load). Two rules:

- A **blocking ENV condition** (degraded/emptied environment) makes ALL
  results unreliable — stop triaging individual tests until it is resolved,
  and beware false passes (absence assertions passing for the wrong reason).
- Recurring ENV causes get a guard in global setup that fails fast with an
  explicit message, so the suite reports the condition instead of 40
  misleading failures.

## Repro ladder (cheapest first)

1. Single test solo, retries off — fails? deterministic bug.
2. Whole file solo — fails? intra-file state.
3. The owning group/suite — fails? cross-suite shared state.
4. Full run — fails only here? cross-group or load coupling.

A test that passes at step N but fails at N+1 tells you the failure's blast
radius — start triage at the boundary, not in the test body.

## Burn-in (definition of "fixed")

- The repaired file passes 3× locally/CI with retries off against the real
  test environment.
- If the cause class was SHARED-STATE: additionally run the colliding suites
  **simultaneously** and pass — that simulates the concurrency that produced
  the collision.
