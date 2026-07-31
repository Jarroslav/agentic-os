# telemetry-export

Sends a pipeline run's governance record — phase transitions and gate
verdicts — to an observability backend of your choosing, stripped down to
structural fields only. Nothing about the ticket content, the rationale text
behind a gate decision, or any file path ever leaves the workspace by default.

## Use It For

- Answering fleet-level governance questions an operator otherwise can't:
  which gates escalate most, where runs stall, whether autonomous approvals
  are backed by high confidence.
- Turning the append-only `events.jsonl` / `decisions.jsonl` ledgers — which
  already exist for every run — into a queryable stream in Axiom, an OTLP
  collector, or anything else that accepts NDJSON.
- Setting up alerting (e.g. "low-confidence autonomous approvals exceeded N in
  the last hour") on top of a backend's own monitor/alert feature.

Not for: token or cost telemetry (unimplemented — see `tokenomics.md`), reading
a backend back into an agent's context (use the backend's own MCP server or
skill set), or automatic export — this skill runs only when invoked, or when a
host wires it into its own hook.

## How To Ask

```
telemetry-export
```

or, for a specific run:

```
telemetry-export docs/superpowers/runs/20260713-1200-demo
```

Requires a declared profile first — see "What It Needs" below. Without one,
the skill is a documented no-op: it prints nothing and appends nothing.

## What It Needs

| Requirement | Where | If missing |
| --- | --- | --- |
| A declared telemetry profile | `.agentic/guides/integration/telemetry-flow.md`, `**Status**: configured` | export is a silent no-op |
| An exporter command | same file, `**Exporter invocation**` — reads NDJSON on stdin | pick a shipped profile (`references/profiles/axiom.md`, `references/profiles/otlp-logs.md`) or write a `custom` one |
| A run directory | `docs/superpowers/runs/<run-id>/` with `events.jsonl` | run the pipeline first — there's nothing to export yet |
| `python3` on PATH | — | the projector is stdlib-only Python, no installs needed |

Credentials (an API token, an org id) live entirely in the host's own
environment and the exporter command it declares — this skill never reads,
stores, or forwards one. If you're pointing at Axiom, its own docs describe
scoping a dedicated, short-expiry, dataset-scoped token; see
`references/profiles/axiom.md`.

Outputs: nothing lands on disk from this skill directly. Successful and failed
export attempts are recorded as `telemetry.export_receipt` /
`telemetry.export_warning` lines appended to the run's own `events.jsonl`.
