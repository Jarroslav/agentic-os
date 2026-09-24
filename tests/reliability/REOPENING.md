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
JSON; host-specific launch wiring is still unverified. The reliability harness
can adapt retained raw traces through this same strict boundary.

## Round 13 — host-boundary adaptation seam

The reliability host runner now accepts an assignment-scoped evidence key,
identity, and validity window. When supplied, it adapts the retained stdout
stream immediately after process cleanup and exposes `adapted_receipts` plus
any adapter error in the run result. Partial or unordered evidence context is
rejected before launch. This wires the canonical adapter into the harness
without inventing host credentials or claiming that Claude/Codex already emit
the required events. Actual host startup, authentication, isolation, and
stream certification remain unverified.

## Round 15 — shared journal-aware installer operations

The versioned runtime now exposes `install.plan` and `install.apply`. Planning
is read-only and classifies create, unchanged, managed-replace, and
user-modified-preserve actions from current hashes and the install journal.
Application recomputes the plan, writes safe files atomically, preserves user
edits, and updates the journal. Both plugin bundles carry the same source;
interviews and stack-specific rendering remain skill-owned. Host certification
and full installer workflow trials remain unverified.

## Round 16 — journal-aware uninstall

The shared installer now exposes `install.remove`. At this checkpoint it removed
unchanged managed/generated files, preserved modified files, marked preserved
paths as user-owned in the journal, and validated explicit path lists. A later
contract correction made the current generic operation preserve generated
files with `owner: generated` so role removal can obtain the required individual
decision; it still removes unchanged managed files and marks modified managed
files as user-owned. The operation is
bundled into both plugins and covered by direct and versioned installer tests.
Full host-driven upgrade/uninstall workflow trials remain unverified.

## Round 17 — registry-bound gate decisions

`decision.record` now rejects identifiers absent from the canonical gate
registry before writing any decision. A public runtime test covers an accepted
`plan.approved` gate and an unknown-gate rejection, with bundle copies kept in
sync. Host approval authenticity and live gate interactions remain unverified.

## Round 14 — fenced trace ingestion

The host harness now exposes a coordinator-fenced ingestion helper for signed
adapted receipts. It advances the expected SQLite revision after each accepted
receipt and refuses to bypass the runtime evidence path. The fake-host test
covers launch, raw trace retention, signing, and authoritative evidence
ingestion together. This proves the adapter seam only; actual Claude/Codex
startup, authentication, isolation, and stream certification remain
unverified.

## Round 22 — cancellation closes dispatch leases

Cancelling a run now atomically marks all unfinished dispatch leases as
`cancelled` with a completion timestamp alongside assignment cancellation.
Recovery cannot treat those workers as still in flight after the run reaches a
terminal cancelled state. A runtime fault test covers the persisted lease
outcome; host interruption trials remain unverified.

## Round 18 — structured gate outcomes

Gate persistence now requires a structured value whose `decision` is one of
`approve`, `request-changes`, or `abort`. Primitive or unknown outcomes are
rejected before the coordinator revision changes. Public runtime tests cover
both accepted and malformed outcomes; actual human approval interactions
remain unverified.

## Round 21 — risk-aware decision source enforcement

Gate decisions now require an explicit source (`hitl`, `deterministic`,
`fast-path`, or `subagent`). An approval with non-empty risk flags is rejected
unless its source is `hitl`, so a risk-plus-fast-path payload cannot become a
successful gate without human escalation. Public runtime tests cover the
rejection path; live approval interaction remains unverified.

## Round 20 — approved-decision artifact binding

Approved `decision.record` values now require a non-empty `artifact_hashes`
map. The coordinator cannot persist a successful gate outcome without naming
the artifacts it approved; malformed approvals fail before revision advance.
Public runtime tests cover valid, missing-hash, and malformed outcomes. Live
artifact mutation and human approval trials remain unverified.

## Round 19 — completion artifact-hash binding

Trusted completion claims now require an `artifact_hashes` map covering every
cited evidence receipt. SQLite compares each claimed hash with the current
authoritative evidence row before allowing completion, so an approval for an
older artifact cannot satisfy the gate. Existing signed completion tests were
updated; live host approval and artifact mutation trials remain unverified.

## Round 23 — stale completion approvals are rejected

An adversarial regression now submits a signed completion claim whose approval
hash disagrees with the authoritative evidence hash. The claim is rejected
before the run can complete, while the matching hash still succeeds. This
proves the stale-approval defense in the executable runtime; host certification
and live-trial evidence remain unverified.

## Round 24 — infrastructure failures consume visible trial slots

The evaluator now reserves a trial after frozen host-profile comparison and
records an infrastructure-failed result when isolation or model certification
is unavailable. Profile drift still aborts before reservation. This preserves
the fixed denominator and prevents unavailable host capabilities from silently
turning into retryable missing data. A local baseline run recorded all 24 slots
as unverified infrastructure failures with a 0.0 demonstrated score; it does
not constitute a product-quality grade or candidate acceptance.

## Round 25 — explicit model identities bound into baseline profiles

After the operator supplied model choices, the baseline was re-frozen with
the selected Claude and Codex identities, preserved in the suite 7 manifest
archive cited in `READINESS.md`. All 24 slots were rerun under that immutable
profile and again recorded as infrastructure failures because host isolation
remains uncertified. The candidate freeze now links to this model-bound
baseline; candidate execution remains deferred until the isolation and hook
certification gate passes.

## Round 26 — bounded model-acceptance probes

Read-only startup probes reached Claude and Codex with their selected profiles
(exact model identifiers are preserved in the suite 7 manifest archive cited in
`READINESS.md`). Claude emitted its configured model identity before its budget
boundary; Codex completed the read-only probe and emitted usage. The profile identifiers are
recoverable from the cited manifest. These are
model/authentication observations only. They do not certify outer filesystem
isolation, global-instruction exclusion, or plugin-hook execution, so no
candidate slot was consumed.

## Round 27 — structured host control matrix

The shared runtime preflight now exposes a control matrix with a status,
enforcement boundary, and evidence description for state protocol,
coordinator identity, worker tool scope, artifact integrity, OS sandboxing, and
external effects. Existing capability names remain compatible, while new
consumers can require the precise control boundary instead of treating one
aggregate sandbox flag as proof. Unsupported host controls continue to fail
closed.

## Round 28 — settings merging moves into the shared installer

The canonical installer now exposes `install.merge-settings`. It recursively
merges objects, appends only missing array entries, preserves existing scalar
values, writes atomically, and records the resulting hash in the install
journal. Invalid JSON fails before mutation. The operation is versioned,
bundled into both plugins, and covered by direct and public-runtime tests.

The merge implementation also rejects object/array shape conflicts before
writing, including existing `null` and scalar values. The runtime proof is now
99 tests; the deterministic installer contract remains fail-closed on malformed
or incompatible settings.

## Round 29 — managed external adapter fencing

`scripts/external-action.py` now provides the coordinator-backed boundary for
managed ticket synchronization. It records an idempotent external intent,
invokes the declared adapter, and reconciles the outcome using the post-intent
revision. Successful and failed exits are durable; timeout and launch
uncertainty transition a running workflow to `reconciliation_required`. The
legacy `ticket-sync` hook uses this path only when lease context is supplied and
continues to fail closed otherwise. Three direct helper tests (including the
legacy hook environment mode) and the full hook
fixture cover the boundary; live adapter/backend behavior remains unverified.

## Round 30 — Linux bubblewrap containment adapter

The evaluator previously recognized only macOS sandbox-exec, so Linux hosts
could never produce containment evidence. A bubblewrap probe now passes 30
kernel-backed controls on the Ubuntu VM. These cover fixture-only writes, exact
auth reads, selected plugins and hooks, invisible host globals, a hidden
signing key, and descendant PID, mount and `setns` containment. Linux launches
are wrapped in the same boundary with a pinned `/usr/bin/bwrap`, hosts no
longer receive `AGENTIC_HOST_KEY`, and signed isolation receipts bind the clean
repository revision and trial fixture. The VM needed a narrow AppArmor
`userns` profile for bwrap, approved by the operator. `isolation_supported`
remains false: real host startup, declared auth files, host-level hook
execution, a profile re-freeze after host upgrades, and a Linux scenario oracle
are still required. No candidate slot was consumed.
