# Shared runtime contracts

Status: experimental, incomplete implementation. SDLC/QA skills have a
managed-runtime boundary and guarded integration points, but full workflow
migration and live certification are not established. Host adapters can issue
short-lived signed dispatch records for
identity-bound mailbox reads and trusted completion gates; without a configured
host key those operations remain fail-closed. The reopening ledger
at `tests/reliability/REOPENING.md` tracks the current acceptance gaps.

`agentic_runtime/registry.json` is the canonical contract source. Run
`python3 runtime/generate_bundles.py` after a source change; CI uses `--check`
to reject drift. Each plugin receives its own runtime and generated contract
reference, so it can be installed without its sibling.

Python 3.10 or newer is required. The runtime uses only the standard library.
Requests and responses are versioned JSON on standard input/output. Invalid
requests fail with exit status 2 and a structured error. Registry inspection:

```sh
printf '%s\n' '{"api_version":"1.0.0","operation":"registry.get"}' | python3 runtime/run.py
```

The runtime lifecycle operations use SQLite as their state and require a
branch/worktree ownership precondition before export artifacts are written.
They check supplied coordinator revisions and lease epochs, reserve dispatches
transactionally, persist in-flight dispatch leases with concurrency and timeout
limits, and put uncertain external outcomes into
reconciliation. JSON exports are revision-labelled views; editing one never
changes the database. Host enforcement and installation operations remain
separate capabilities. An absent operation is an error; it must never fall
back to editing JSON state. Registry validation alone does not enforce worker
permissions or provide an operating-system sandbox.

Scored evaluation definitions remain frozen independently under
`tests/reliability/`. Passing contract tests earns no live evaluation points.

Supported operations use the same `api_version` envelope:

| Operation | Required fields beyond operation/version | Optional fields |
|---|---|---|
| `registry.get` | none | none |
| `contract.lookup` | `section`, `identifier` | none |
| `policy.resolve` | `entrypoint` | `overrides` |
| `input.normalize` | `payload` | `legacy` (boolean, default false) |
| `transition.validate` | `source`, `target` | none |
| `retry.allowed` | `loop_id`, `attempts_used` | none |

`attempts_used` includes the initial attempt. A false retry result prohibits another
attempt; it does not change the outcome of the previous attempt. Policy overrides
can reduce default budgets. Increasing a running budget requires a future recorded
user-decision operation; changing configuration must not silently reset counters.

Lifecycle requests include `run.start`, `run.status`, `run.resume`, `run.cancel`,
`run.complete`, `task.dispatch`, `task.result`, `dispatch.start`, `dispatch.finish`,
`dispatch.recover`, `decision.record`, `message.deliver`, `external.intent`,
`external.reconcile`, `legacy.import`, `legacy.export`, `evidence.ingest`, and
`event.record`, `run.export`.
`legacy.import` records
the source hash and receipt without replacing the original file. Mutating requests for an owned run carry
the coordinator identity, current `lease_epoch`, and expected revision; stale ownership or revisions fail atomically.
Assignments are owned by one worker and carry paths, context references,
acceptance criteria, limits, and dependencies. `assignment.create` rejects
unknown dependencies and cycles; `assignment.transition` requires the current
assignment revision. `message.send` accepts only registered typed messages and
rejects stale assignments, duplicate content changes, inconsistent sender labels, and
payloads over the registry limit. Worker-originated messages also require a
host-signed dispatch record bound to the assignment revision; only the fenced
coordinator may publish without a worker dispatch record.
Question correlations support the registry's bounded request/reply rounds; an
unanswered or cyclic exchange is escalated by `runtime.recover`.
`evidence.record` stores receipts bound to a run revision. A host-signed
`run.complete` record must name successful required evidence and an approved gate
before completion. Host adapters use the signing helpers in `agentic_runtime.host`
and keep the signing key outside repository state. Signed command receipts bind
the command, working directory, check type, and required flag as well as the
result. Failed required commands remain in the ledger; completion requires the
latest signed result for each required command stream to pass and be named by
the gate. Host adapters may explicitly mark exploratory command events
`required: false` before signing; the default is required. Unsigned required
failures remain rejected.
Completion rechecks the retained signed host claim against each evidence row.
Legacy receipts that did not sign the command identity cannot satisfy a new
completion gate; rerun the affected checks to create current receipts.
Before filtering required checks, completion also rejects modern persisted rows
whose stored fields disagree with their signed claims. This detects a damaged
row projection; it does not protect a database that a worker can rewrite or
delete directly. Worker access to coordinator state requires a separate host
isolation boundary.
Named optional results may remain in a gate for context, but at least one
successful signed required receipt is still required to prove completion.
`agentic_runtime.trace.command_receipt` accepts only explicit
`agentic.command.completed` adapter events, so model prose cannot become command
evidence by inference.
Host adapters can pass the same event to `agentic_runtime.trace.ingest_command_event`
or the versioned `evidence.ingest` operation; parsing happens before the
transaction and the store verifies the signed host claims.
Adapters may use `agentic_runtime.host.issue_evidence_record` to sign only the
validated explicit command fields before ingestion.
`agentic_runtime.adapter.adapt_json_lines` provides the stream boundary: unrelated
host output is ignored, explicit receipts are signed, and malformed JSON fails
closed.
The versioned `trace.adapt` operation exposes the same boundary to host launchers
and requires `AGENTIC_HOST_KEY`.
`install.plan` computes journal-aware file actions without writes. `install.apply`
recomputes that plan immediately before atomically applying create/managed-replace
actions and updates `.agentic/agentic-os/install.json`; user-modified files are
preserved. `install.remove` deletes only unchanged managed/generated files and
marks modified files as user-owned. `install.merge-settings` performs the same
deterministic recursive object/unique-array merge used by setup, writes the
result atomically, and journals the resulting hash while preserving existing
user scalar values. Skills remain responsible for interviews and stack-specific
rendering.
`legacy.export` regenerates `meta.json`, `events.jsonl`, and `decisions.jsonl`
as compatibility views from SQLite; edits to those files are overwritten on
the next export and never affect authoritative state.
Setup uses `host.preflight` to report observed Python, SQLite, Git, and host
launch capabilities. Passing `required_capabilities` makes the check fail closed
when a workflow depends on an unavailable control; unsupported OS sandboxing is
reported explicitly, and `control_matrix` names each control's enforcement
boundary and evidence source. Peer
work also exposes `assignment.create`, `assignment.transition`, `message.send`,
`message.receive`, and `runtime.recover`.
