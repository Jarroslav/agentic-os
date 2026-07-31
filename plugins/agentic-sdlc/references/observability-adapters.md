# Observability adapters: projecting the run ledgers without hardcoding a backend

Every pipeline run already writes a complete governance record —
`events.jsonl` (phase transitions and side effects) and `decisions.jsonl`
(every gate verdict, its source, confidence, and risk flags). Nothing in the
pipeline ever reads that record back in aggregate; it lands in the run
directory and dies with the workspace. This reference is the contract that
lets a host project ship that record to an external observability backend
without the pipeline ever naming one.

Load it with:

```
${CLAUDE_PLUGIN_ROOT}/references/observability-adapters.md
```

Read it if you author or maintain the `telemetry-export` skill, or if you are
writing an adapter profile for a specific backend.

> The whole point is the same indirection `work-item-adapters.md` and
> `mr-adapters.md` already use. A skill that hardcodes an ingest endpoint is a
> skill that ships a secret-handling surface and breaks on the next backend. A
> skill that emits a normalized record and lets a declared **profile** carry it
> the rest of the way keeps working everywhere, because the vendor shape lives
> in a profile document, not in the skill.

## What this is not

This is not a telemetry collector the pipeline runs by default. Nothing here
adds a hook, a network call, or a credential to shipped code. Export only
happens when a host project declares a profile and invokes the
`telemetry-export` skill (directly, or via a Stop hook it wires itself). Absent
that declaration, the pipeline behaves exactly as it does today — see
"Not in scope" at the end of this file.

This is also not the token/cost collector. `references/tokenomics.md` reserves
a separate `usage.sampled` event and a `report-builder` roadmap slot for token
economics; this contract carries governance events only (`events.jsonl` and
`decisions.jsonl`), and the two are not to be conflated.

## What flows across the boundary

One versioned data contract moves from the projector to a profile: the
**telemetry record**, schema `references/schemas/telemetry-record.schema.json`.
It is a flattened, redacted NDJSON projection — one line per source ledger
line, `stream` set to `"events"` or `"decisions"`.

### Deny-by-default field allowlist

The projector never forwards a source field unless it is named below. This is
a security posture, not an oversight: `summary`, `verdict.rationale`, and
`prior_context` are free-form text that can carry ticket content, file paths,
or model reasoning, and none of it is needed to answer a governance question.

| Stream | Forwarded fields |
| --- | --- |
| `events` | `_time` (from `ts`), `stream`, `schema`, `event`, `run_id`, `phase`, `actor`, `artifact_count` (derived: `len(artifacts[])`), `duration_ms` (derived on `phase.completed`, matched against the run's `phase.started`) |
| `decisions` | `_time` (from `ts`), `stream`, `run_id` (**injected** — see below), `gate_id`, `mode`, `escalated`, `decision` (`verdict.decision`), `source` (`verdict.source`), `confidence` (`verdict.confidence`), `risk_flags` (`verdict.risk_flags`), `follow_up_count` (derived: `len(verdict.follow_ups)`) |

`data{}` on an `events` line gets a second, narrower allowlist —
`status`, `state`, `kind`, `count`, `loop`, `attempt` — and only when the value
is a scalar matching `^[A-Za-z0-9_.:/-]{1,64}$`. Anything else in `data{}` is
dropped silently, not truncated or scrubbed.

**Always dropped:** `summary`, `verdict.rationale`, `prior_context`,
`artifacts[]` path strings, every `data` key not on the narrow list above. A
host that has a specific, understood need for one of these can opt it in via
`**Extra fields**` in its declared flow file (see below) — the projector still
enforces the scalar/pattern check on anything added this way.

### `run_id` injection

`decisions.jsonl`'s own schema (`decision-line.schema.json`) has no `run_id`
field — a decision record is meaningful only inside the run directory it lives
in. The projector injects `run_id` from the run directory name before emitting
a `decisions` line. Without this injection the two streams cannot be joined in
a query, which defeats the point of exporting either.

### Machine-checked allowlist

`tests/lib/check-telemetry-allowlist.py` parses the three blocks below and
asserts they match `export-run-telemetry.py`'s allowlist constants exactly, so
this document and the code it describes cannot silently drift apart.

<!-- allowlist:events -->
_time, stream, schema, event, run_id, phase, actor, artifact_count, duration_ms
<!-- /allowlist:events -->

<!-- allowlist:decisions -->
_time, stream, run_id, gate_id, mode, escalated, decision, source, confidence, risk_flags, follow_up_count
<!-- /allowlist:decisions -->

<!-- allowlist:data -->
status, state, kind, count, loop, attempt
<!-- /allowlist:data -->

## Declaring an adapter

A project declares its telemetry profile in
`.agentic/guides/integration/telemetry-flow.md`, using the same
`**Label**:` single-line-value convention `ticket-flow.md` already uses:

| Field | Meaning |
| --- | --- |
| `**Status**` | `configured` or `not configured` |
| `**Profile**` | `axiom` \| `otlp-logs` \| `custom` — see `references/profiles/` |
| `**Exporter invocation**` | a command that reads NDJSON on **stdin** and exits 0 on success. `{count}` is substitutable with the line count of the batch. |
| `**Extra fields**` | optional, comma-separated additions to the `data{}` allowlist above |

The declaration is what `telemetry-export` reads; it never sniffs a backend
from an endpoint shape, and it never hardcodes which backend a project uses.

## Failure handling

The default posture is `warn-and-continue`, matching every other adapter in
this pipeline.

| Situation | Ledger entry |
| --- | --- |
| No flow file declared | nothing — silent no-op, no event appended |
| Exporter command fails or times out | append `telemetry.export_warning` |
| Exporter command succeeds | append `telemetry.export_receipt` with the line count exported |

Export never blocks a run. It is invoked after turn-end work is otherwise
done, and any failure is swallowed exactly the way `ticket-sync` swallows
adapter failures.

## Dedup and the receipt cursor

`telemetry-export` treats its own last `telemetry.export_receipt` in the
ledger as the export cursor: everything at or before its recorded line offset
was already sent. `telemetry.*` events are themselves **excluded from every
export** — without that exclusion, each successful export appends a line that
becomes new input for the next export, and the ledger grows forever on every
turn-end. If nothing new (excluding `telemetry.*` lines) exists since the last
receipt, the skill exits without writing anything.

## Constraints

- Do not infer a profile from an endpoint URL shape.
- Do not hardcode a vendor name, endpoint, or credential anywhere in this
  plugin. `references/profiles/*.md` document vendor specifics; they are read,
  never executed.
- Do not widen the default allowlist. Adding a field to the default set is a
  decision that affects every host project that has not opted in — it belongs
  in this document's review, not in a projector code change.
- Do not export before an exporter command is declared. Absent configuration
  is a no-op, not an error.
- Do not treat a `telemetry.export_warning` as fatal. It is diagnostic only.

## Not in scope

- This is not an Axiom, Datadog, or Honeycomb client. No provider request
  shapes are defined here — that is `references/profiles/`.
- No credential ever passes through the plugin. The exporter invocation is a
  host-declared command; the plugin pipes NDJSON to its stdin and reads its
  exit code. Whatever token that command uses is the host's own environment,
  never a plugin-managed secret.
- Token/cost telemetry (`usage.sampled`) — see `references/tokenomics.md`.
- Reading telemetry back into an agent's context (e.g. querying a backend
  during a run) is out of scope for this contract; a backend's own MCP server
  or skill set (several ship one) is the way to do that, and is unrelated to
  this export path.

## Related

- `work-item-adapters.md` — the same indirection for ticket backends; the
  precedent this document follows.
- `mr-adapters.md` — the same indirection for MR/PR platforms.
- `lifecycle-artifacts.md` — owns `events.jsonl` and `decisions.jsonl`
  themselves; this document only describes their projection.
- `tokenomics.md` — the token/cost collector this contract is deliberately not.
- `schemas/telemetry-record.schema.json` — the versioned output shape.
- `profiles/axiom.md`, `profiles/otlp-logs.md` — shipped profiles.
- Consumers: `telemetry-export` (emits the projection and invokes the
  exporter).
