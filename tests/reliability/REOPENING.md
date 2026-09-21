# Stages 3–4 reopening ledger

Starting commit: `43d2a58`. Branch: `codex/framework-reliability`.
Authorization: operator said "yes, re-open and continue" on 2026-09-21,
in response to one bounded remediation round and fresh blind reviews.

## Rules

- One implementation round, then independent correctness/recovery and
  enforcement/contracts reviews with no inherited conversation.
- Capture the staged tree before review; do not modify it while reviewing.
- Neither passing unit tests nor a fail-closed stub establishes stage acceptance.
- Unresolved acceptance gaps remain blocking. No extra fix cycle is assumed.
- Original live budget remains 48 trials, with none executed.

## Confirmed findings before remediation

- Completion succeeds with no gates or command evidence.
- Mailbox authorization compares two caller-supplied strings.
- The dispatch ceiling is supplied per call, so omission restores the default.
- Schema/contract metadata is written but not checked on reopening a database.
- Peer deadlines can exceed the registry ceiling and recovery can repeatedly
  change revisions for already escalated assignments.
- Run cancellation does not propagate to every unfinished assignment.
- Originality attestation verification failed for 24 of 530 tracked files.
- MCP content drift check failed: both plugins' new host/store modules were
  missing from the content index, with stale changelog and CLI entries.

A fresh `check-provenance.py --require-store` scan on the pre-remediation
working tree passed (535 tracked files, zero failures/warnings). Attestation
must be regenerated after final changes; this scan alone does not renew it.

## Remaining scope beyond containment fixes

Full acceptance still requires authenticated host dispatch records; executable
gate and source-bound command verification; active-time/concurrency/retry
admission; durable scheduling; meaningful legacy import and external outcome
reconciliation; deterministic installer operations; workflow integration; and
independent live observers. A restriction that blocks an unsupported operation
prevents a false success but does not implement that operation.

## Round 1

Candidate implementation finished. Before remediation, nine added regressions
produced eight failures. After remediation, 60 runtime tests pass. Public
completion and mailbox delivery are disabled pending trusted host contracts.
Persisted dispatch ceilings, version validation, finite bounded deadlines,
run-scoped question correlations, terminal assignment protection, idempotent
timeout recovery, and run cancellation propagation have regression coverage.
Question correlations currently allow one request/response pair; two-round
reuse is not implemented. This candidate does not establish stage acceptance.

An interrupted-initialization fault injection now exits at the injected DDL
statement and successfully reopens the partial database. Raw checks are
retained under `/tmp/agentic-reopen-*.log`. Unaffected evaluator, T0, and
acceptance matrix checks passed (80, 109, and 99 respectively); the MCP suite
passed 204 tests and content drift was rebuilt. Review verdicts must bind to
the final staged tree after packaging and attestation.

## Round 2 — host trust and dispatch admission

The operator approved continuation on 2026-09-21. This round adds signed,
short-lived host dispatch records with identity, run, assignment, and purpose
bindings. Valid records unlock mailbox reads and trusted completion only when
the configured host key verifies them; caller-supplied identities remain
insufficient. Completion also requires an approved host gate, successful named
evidence, and no unfinished assignments.

Dispatch reservations now have persistent in-flight leases. SQLite enforces
the registry concurrency ceiling, per-worker timeout ceiling, idempotent finish,
timeout recovery, and no reservation refund after timeout. Deterministic runtime
proof is now 63 tests. These changes are a tested implementation checkpoint;
host adapters, workflow integration, independent blind review, and live trials
remain required for stage acceptance.

## Round 3 — runtime integration controls

The operator approved continuation on 2026-09-21. The versioned CLI now loads
the host key from the adapter environment, supports the second bounded
question/reply round, and exposes capability requirements that fail closed.
Active execution exhaustion atomically transitions a running run to
`waiting_for_user`; it no longer leaves only a transient error. Deterministic
runtime proof is now 67 tests. These changes still do not certify real host
dispatch hooks or command capture.

## Round 4 — evidence provenance

Host-signed evidence records are now persisted with each receipt and required
by trusted completion. A caller-only receipt cannot satisfy a signed completion
gate, and the schema migration preserves existing databases by adding the new
column during initialization. Deterministic runtime proof is now 68 tests. The
remaining evidence gap is extraction from real Claude/Codex traces rather than
caller-supplied JSON.

## Round 5 — complete run snapshots

Run exports now include assignments, peer messages, evidence receipts, and
dispatch leases alongside transitions, decisions, and external actions. The
export remains a regenerable, revision-labelled view and does not become an
authority for mutations. Runtime proof remains 74 tests.

## Round 6 — explicit trace receipts

The shared runtime now exposes a strict command-trace parser. It accepts only
an explicit `agentic.command.completed` event containing the run revision,
command, working directory, source hash, exit status, and host record. Arbitrary
assistant prose or malformed events are rejected. Deterministic runtime proof
is now 74 tests; wiring this adapter to real Claude/Codex stream events remains
live host integration work.
