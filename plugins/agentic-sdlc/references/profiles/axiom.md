# Profile: Axiom

How to point `telemetry-export` at [Axiom](https://axiom.co) — a schemaless
event-data platform with its own query language (APL), dashboards, and
monitors. This document is read by a human wiring up
`.agentic/guides/integration/telemetry-flow.md`; nothing in it is executed by
the pipeline. See `references/observability-adapters.md` for the contract this
profile fills in, and `references/profiles/otlp-logs.md` for a vendor-neutral
alternative.

## Declaring this profile

```
**Status**: configured
**Profile**: axiom
**Exporter invocation**: curl -sf -X POST \
  "https://${AXIOM_DOMAIN}/v1/ingest/${AXIOM_DATASET}" \
  -H "Authorization: Bearer ${AXIOM_TOKEN}" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @-
**Extra fields**:
```

`AXIOM_DOMAIN`, `AXIOM_DATASET`, and `AXIOM_TOKEN` are read from the host's own
environment at export time — none of them are written into this file or into
any file the plugin ships.

## Things that will silently go wrong if skipped

- **`AXIOM_DOMAIN` is a placeholder, not `api.axiom.co`.** Ingest and query
  traffic goes to a region edge: `us-east-1.aws.edge.axiom.co` or
  `eu-central-1.aws.edge.axiom.co`. Only account/dashboard management traffic
  uses `api.axiom.co`. Using the wrong host for ingest is a common copy-paste
  mistake from older examples.
- **The token must be an API token, not a personal token.** Axiom issues two
  shapes; only the API-token form is accepted for ingest. A personal token
  authenticates a human session and is rejected here.
- **The endpoint returns HTTP 200 even when some events failed.** The response
  body carries `{"ingested": N, "failed": M, "failures": [...]}` — `curl -f`
  only catches a non-2xx status, so a healthy-looking exit code does not mean
  every line landed. If you need per-event confirmation, replace the `curl`
  one-liner above with a small wrapper that parses the JSON response and exits
  nonzero when `failed > 0`.
- **Batch cap is 10,000 events.** `telemetry-export` runs are one turn-end's
  worth of new lines, which is nowhere near that in practice, but a very long
  gap between exports could approach it. Export more often if runs are long.
- **Axiom may throttle or suspend ingestion under sustained high request
  rates.** Wiring `telemetry-export` into every `Stop` hook on a busy fleet is
  the scenario to watch for; export on a coarser cadence if that's the setup.

## Dataset

One dataset is enough for this contract's event volume — both streams
(`events` and `decisions`) carry a `stream` field, so a single dataset can
distinguish them in a query rather than needing two. Axiom's free tier allows
three datasets total, so a single governance dataset (suggested name:
`agentic_sdlc_runs`) leaves room for whatever else the project already sends.

## Token scoping

Axiom's own guidance for agent-facing tokens applies directly here: a
dedicated token, scoped to the one dataset above, with a short expiry
(hours-to-days, not months), rotated rather than reused. Do not reuse a
broader personal or org-wide token for this exporter.

## Starter queries (APL)

Validate these against Axiom's current APL reference before relying on them —
query syntax has changed between doc revisions.

Escalation rate by mode, over time:

```apl
['agentic_sdlc_runs']
| where stream == 'decisions'
| summarize total=count(), escalations=countif(escalated == true) by mode, bin_auto(_time)
| extend escalation_rate = escalations * 1.0 / total
```

Phase duration, p50/p95, worst offenders first:

```apl
['agentic_sdlc_runs']
| where event == 'phase.completed'
| summarize p50=percentile(duration_ms, 50), p95=percentile(duration_ms, 95) by phase
| order by p95 desc
```

Autonomous approvals on thin evidence — the query worth turning into a
monitor:

```apl
['agentic_sdlc_runs']
| where stream == 'decisions' and mode == 'autonomous' and decision == 'approve'
| where confidence == 'low' or array_length(risk_flags) > 0
| summarize count() by gate_id, bin_auto(_time)
```

## Free-tier constraints worth knowing up front

500 GB/month ingest (not a binding constraint at this event volume), but also
**3 datasets, 3 monitors, 1 user, 30-day retention** — the last of those means
long-horizon trend queries need either an upgraded plan or your own periodic
rollup exported elsewhere.

## Reading telemetry back into an agent

Out of scope for this profile, but worth knowing: Axiom ships its own hosted
MCP server and its own agent skill set for querying Axiom data from an
assistant. Wiring either of those up is unrelated to `telemetry-export` — this
profile only covers the outbound direction.
