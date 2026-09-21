# Shared runtime contracts

Status: experimental, incomplete implementation. Existing SDLC/QA skills are
not yet integrated with this store. No host authentication or live workflow
certification is established. Run completion and mailbox delivery require
trusted host contracts before they can be enabled safely. The reopening ledger
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
They check supplied coordinator revisions and lease epochs, reserve
dispatches transactionally, and put uncertain external outcomes into
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
`task.dispatch`, `decision.record`, `message.deliver`, `external.intent`,
`external.reconcile`, `legacy.import`, and `run.export`. `legacy.import` records
the source hash and receipt without replacing the original file. Mutating requests for an owned run carry
the coordinator identity, current `lease_epoch`, and expected revision; stale ownership or revisions fail atomically.
Assignments are owned by one worker and carry paths, context references,
acceptance criteria, limits, and dependencies. `assignment.create` rejects
unknown dependencies and cycles; `assignment.transition` requires the current
assignment revision. `message.send` accepts only registered typed messages and
rejects stale assignments, duplicate content changes, inconsistent sender labels, and
payloads over the registry limit.
`evidence.record` currently stores caller-supplied command claims bound to a run
counter. It does not execute or authenticate commands or bind them to repository
content. Required failures are rejected at ingestion rather than retained as
receipts. Trusted evidence capture and gate decisions remain implementation work.
Setup uses `host.preflight` to report observed Python, SQLite, Git, and host
launch capabilities; unsupported OS sandboxing is reported explicitly. Peer
work also exposes `assignment.create`, `assignment.transition`, `message.send`,
`message.receive`, and `runtime.recover`.
