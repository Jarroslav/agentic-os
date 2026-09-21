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
authority for mutations. Runtime proof remains 76 tests.

## Round 6 — explicit trace receipts

The shared runtime now exposes a strict command-trace parser. It accepts only
an explicit `agentic.command.completed` event containing the run revision,
command, working directory, source hash, exit status, and host record. Arbitrary
assistant prose or malformed events are rejected. Deterministic runtime proof
is now 76 tests; wiring this adapter to real Claude/Codex stream events remains
live host integration work.

## Round 7 — host trace receipt visibility

The offline Claude/Codex harness now exposes only explicitly valid command
receipts in its retained metadata and counts malformed receipt-shaped events
without trusting them. This is an evidence-input boundary, not host
certification: real host authentication, signed record issuance, and isolated
execution remain unverified.

## Round 8 — legacy ledger compatibility views

`legacy.export` now regenerates `meta.json`, `events.jsonl`, and
`decisions.jsonl` from SQLite without replacing user-owned specification files.
Editing a compatibility file cannot change runtime state. Existing skills still
need to call this operation at their integration points; direct legacy-ledger
writes remain an open Stage 6 migration item.

## Round 9 — legacy append guard

The QA E2E legacy event helper now detects an ancestor SQLite runtime and fails
before writing `events.jsonl`. Unmanaged legacy fixtures remain supported and are
tested separately. This closes one shipped dispatcher bypass; remaining workflow
call sites still require migration to runtime operations.

## Round 10 — metadata assembler guard

The QA E2E metadata assembler now applies the same managed-run fail-closed
boundary as the event helper. It cannot overwrite a runtime-derived
`meta.json`; unmanaged legacy smoke fixtures continue to pass.

## Round 11 — fenced QA phase events

The runtime now persists bounded coordinator-owned `event.record` entries and
projects them into legacy event views. The QA event helper uses that operation
when run ID, coordinator identity, lease epoch, and expected revision are
provided; missing context still fails closed. This gives the QA phase ledger a
real migration path instead of requiring direct JSONL mutation.

## Round 12 — canonical host evidence issuer

Host adapters now have a canonical issuer that validates an explicit command
completion event, signs only its command/evidence fields, and produces the
short-lived `evidence.record` claim accepted by SQLite. Prose and incomplete
events cannot be signed. Real Claude/Codex stream wiring remains external host
integration work. The issuer-to-SQLite acceptance path is covered by the runtime
tests, but actual host stream wiring remains unverified. `adapt_command_event`
now composes the issuer and parser into one adapter-facing operation. The
stream adapter extracts only explicit receipts and fails closed on malformed
JSON; host-specific launch wiring is still unverified.
