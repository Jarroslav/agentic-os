# Profile: generic OTLP logs

How to point `telemetry-export` at any backend that accepts an
OpenTelemetry Protocol (OTLP) logs endpoint — Datadog, Honeycomb, Grafana
Cloud, an in-cluster OTel Collector, and Axiom itself (which also exposes an
OTLP logs endpoint alongside the ingest API documented in
`references/profiles/axiom.md`). Use this profile when the host already has
an OTel pipeline and does not want a second, vendor-specific ingestion path.

See `references/observability-adapters.md` for the contract this profile
fills in.

## Declaring this profile

```
**Status**: configured
**Profile**: otlp-logs
**Exporter invocation**: python3 "${CLAUDE_PLUGIN_ROOT}/references/profiles/scripts/ndjson-to-otlp-logs.py" \
  --endpoint "${OTEL_LOGS_ENDPOINT}" \
  --header "Authorization=Bearer ${OTEL_TOKEN}"
**Extra fields**:
```

This profile does not ship the wrapper script above — an OTLP logs payload is
a structured protobuf-or-JSON body keyed by resource/scope/log-record, not a
line-for-line NDJSON passthrough, so turning the projector's output into a
valid OTLP request needs a small translation step. Writing that translator is
a host-side task; keep it thin (parse NDJSON line, set `body` to the record,
`timestamp` from `_time`, `attributes` from every other field, `severity` from
`stream`) and point it at your collector's OTLP/HTTP logs endpoint, typically
`<collector>/v1/logs`.

## What a record maps to

Each NDJSON line from `export-run-telemetry.py` becomes one OTLP log record:

| Telemetry record field | OTLP log record field |
| --- | --- |
| `_time` | `timeUnixNano` |
| everything else | `attributes` (flat key/value) |
| `stream` | also a good candidate for `severityText`, or a resource attribute distinguishing the two ledgers |

## Things worth deciding explicitly

- **Where does this run in the pipeline?** A local OTel Collector as the
  exporter target keeps the credential entirely inside infrastructure the host
  already runs, with no token in `telemetry-flow.md` at all — the collector's
  own exporters (to Datadog, Honeycomb, whatever) carry the real secret.
- **Resource attributes.** OTel backends generally expect a `service.name` and
  similar resource-level attributes on every batch. Set these once in the
  collector's receiver config rather than per-line, so the projector's output
  stays a plain flat NDJSON record.
- **Batching.** `telemetry-export` calls the exporter once per invocation with
  whatever's new since the last receipt — usually small. If the collector
  expects its own batching, let it do that; do not add batching logic to the
  projector itself, which stays a stateless-per-run script by design.

## Not shipped here

- A concrete `ndjson-to-otlp-logs.py` translator. The mapping table above is
  enough to write one against whatever collector is in play; shipping one
  generic implementation here would either be too thin to be useful or would
  start accumulating vendor-specific quirks, which is exactly what the profile
  split is meant to avoid.
- Any endpoint, token, or collector configuration. All of it is host-declared,
  same as every other profile.
