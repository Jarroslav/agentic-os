# Case sync: writing approved cases to the adapter-configured backend

> Final stage (7) of `qa-case-generator`. Optional, consent-gated, and non-fatal. It runs only after the stage-6 review gate has approved `test_cases.md`, and the pipeline's success never depends on it — the local run is authoritative whether or not the push lands.

Load this file immediately before executing the sync stage. Read it once; do not carry assumptions from earlier stages about the backend — everything you need about the remote push is here.

## Blast radius

Contacting an external test-management system is an **R3** side-effect (external, irreversible from this run's point of view) and is the highest-privilege operation in the whole pipeline. It is always fenced behind an explicit consent gate. Everything before the push is local:

| Step | Writes | Tag |
|---|---|---|
| Build `sync_payload.json` | run artifact | R1 |
| Push to the remote via the adapter | external system | R3 |
| Enrich `meta.json` with the outcome | repo file | R2 |

> Nothing leaves the machine until the user says yes. Treat consent as the gate that unlocks R3.

## Inputs

| Input | Source | Notes |
|---|---|---|
| `test_mgmt_adapter` | stage 1 (environment validation) | `null` means no backend is configured |
| `test_cases.md` | stage 5, approved at stage 6 | the source parsed into the payload |
| `meta.json` | earlier in the run | mutated in place at the end of this stage |

All artifacts for the run live under one directory:

```
docs/superpowers/qa-tasks/<date>-<slug>/manual/
```

## Entry decision

Branch on `test_mgmt_adapter` first, then on user consent. The three paths and the `sync_status` each sets:

| Condition | Action | `sync_status` |
|---|---|---|
| `test_mgmt_adapter` is `null` | skip straight to the completion summary | `not_configured` |
| adapter present, user declines | skip to the completion summary | `skipped` |
| adapter present, user accepts | build payload → invoke adapter → process receipt | resolved from the receipt |

Ask for consent with the `AskUserQuestion` tool. The question **must** name the target system and the exact number of cases about to be pushed, so the user is agreeing to a concrete action rather than an abstract one.

> Consent is per-run and specific to this system + count. Never reuse an approval from a prior run or a prior push. A fresh yes is the only thing that unlocks the R3 call.

## Build the payload — R1

On the accept path, parse the approved `test_cases.md` into structured JSON and write it to `sync_payload.json` *before* touching the network. Persisting the payload first gives you a replayable record and makes the remote call a pure function of a file on disk.

```json
{
  "ticket_id": "PROJ-123",
  "test_cases": [
    { "id": "PROJ-123_TC_001", "priority": "P1", "type": "ui" }
  ]
}
```

- `id` — `PROJ-123_TC_001` format: the ticket key, then `_TC_`, then a zero-padded ordinal.
- `priority` — one of `P1|P2|P3`.
- `type` — includes `ui` and `api`; carry through whatever value stage 5 assigned.
- Any extra per-case fields stage 5 produced pass through untouched (the `...` in the schema).

## Invoke the adapter — R3

No backend is hardcoded. The adapter resolved in stage 1 is the only path to the remote system (for example TestRail, Xray, Zephyr, or Azure DevOps test plans). Hand it `sync_payload.json` and read back a structured receipt:

```json
{ "status": "success | partial | failed", "test_run_id": "TR-456", "test_run_url": "https://..." }
```

## Process the receipt

| `status` | Handling | Resulting `sync_status` |
|---|---|---|
| `success` | write the receipt into `meta.json` under `sync_details` | `synced` |
| `partial` | offer a retry of **only** the failed cases via `AskUserQuestion`; resolve once the retry outcome is known | `synced` if all land, else `failed` |
| `failed` | log it, notify the user, leave the local outputs authoritative | `failed` |

`sync_details` captures the receipt fields — `test_run_id` and `test_run_url` — alongside the synced status.

> Sync failure is non-fatal by design. An unreachable adapter and an authentication failure both mark the run `failed` and stop the stage — neither halts the pipeline nor invalidates any local artifact. A partial receipt is not a dead end; it flows into retry handling.

## Duplicate cases on the remote

If the adapter reports that matching cases already exist on the backend, resolve it with a three-way `AskUserQuestion`:

| Choice | Effect |
|---|---|
| Overwrite | replace the existing remote cases with this run's payload |
| New Run | push as a fresh test run, leaving the existing cases in place |
| Cancel | abandon the push; local artifacts stay authoritative |

## Record the outcome — R2

- **`meta.json`** — set `"sync_status"` to exactly one of `not_configured | skipped | synced | failed`. On a successful push, additionally write the `sync_details` key.
- **`events.jsonl`** — append the run's audit trail for this stage: the consent decision, the adapter invocation, and the receipt outcome.

## Completion summary

Print this once at the end, on every entry path (including `not_configured` and `skipped`). It reports:

- Ticket id and its URL.
- Case counts split by priority tier — `P1`, `P2`, `P3`.
- The artifact directory (the `manual/` path above).
- A per-file checklist, one line per artifact: `test_cases.md`, `meta.json`, `ticket-analysis.md`, `sync_payload.json`, `events.jsonl`.
- The sync status, plus the `test_run_url` when the receipt supplied one.

## Recovery

A stage-7 failure is fixable without redoing anything upstream. Correct the adapter configuration, then retry the sync alone — a re-run resumes from the failed stage, never from scratch. The approved `test_cases.md` and every other artifact are unchanged and reused as-is.

## Out of scope

- **Case authoring** — owned by the stage-5 reference and `test-templates.md`.
- **Adapter internals and backend API calls** — hidden behind the adapter abstraction; this stage only knows the payload and receipt schemas.
- **Coverage and priority math** — see `SKILL.md`.
- **Making sync mandatory** — it never is. A configured-but-skipped or a failed push leaves a fully successful run behind it.
