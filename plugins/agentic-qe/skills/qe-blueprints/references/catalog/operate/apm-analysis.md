# Analyze APM performance data

Turn raw observability telemetry into an evidenced investigation report — traffic-light verdict, root-cause hypothesis, ranked recommendations — in minutes instead of an hour of manual dashboard correlation.

## When to use this

- **Reach for it when** an alert fires and the real cause likely sits several hops away in the service topology; when a fleet is too large for humans to health-check every service on schedule; when validating a deployment for latency/error/resource regressions; when comparing the same service across environments to separate code regressions from environment-parity gaps; or when hunting slow degradation — memory growth, capacity creep, quietly worsening dependencies.
- **Skip it when** services have no observability-agent instrumentation or under ~7 days of history (no baseline, no analysis); when the cause is already obvious and confined to one service; when the platform connector or credentials are not yet working — prove them with a single-prompt smoke test first; or when you want automated remediation — this workflow analyzes, humans act.
- **Outcome** — single-digit-minute investigations replacing 30–60 minutes of expert correlation, an evidenced write-up for every fired alert instead of only the top-severity fraction, and trend flags weeks before threshold alerts would trip.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Read-only observability API token (metric, entity/topology, problem/event, log scopes) | All analysis is query-driven; granting no write access caps blast radius | Platform admin console |
| Connector between agent tool and platform | The agent must run platform-native queries; each vendor has its own query language, the method is identical | Vendor integration catalog, or a thin custom skill |
| Service topology: names, dependencies, zone/namespace scoping | Determines what to query and how failures cascade | Platform auto-discovered dependency map, team-verified |
| Per-service thresholds: tail latency, error %, throughput, resource limits | Anomaly classification is meaningless without a reference point | Team SLOs / performance targets |
| ≥7 days of hourly telemetry | Rolling baselines and trend regression need history; deploy the (usually zero-config) platform agent and wait a week for new services | Existing platform data store |
| Expected traffic patterns (business hours, batch windows, periodic peaks) | Anomalies are relative to expected load, not absolute values | Team operational knowledge |
| Credentials for both environments (comparison runs only) | Paired same-metric queries must hit both sides over the same window | Platform admin per environment |

## Agent design

Split the pipeline by cognitive load: metric fetching and threshold math are mechanical and deterministic; cross-service causal reasoning is not. One orchestrator dispatches four analyzers and a publisher, each with a narrow read surface and its own output contract.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Orchestrator | Interpret trigger and inputs, decompose the investigation, dispatch specialists, route rejected hypotheses back for deeper analysis; in unattended mode becomes a pinned sequence with fixed model/prompt/tools per step | standard | Trigger context, service names, environment, time window | Dispatch decisions, assembled intermediate state | R1 |
| Metrics collector / anomaly detector | Fetch golden signals (rate, errors, duration, saturation), infrastructure metrics (CPU, memory, GC, pod counts), dependency health; classify each metric against static thresholds and a rolling multi-day baseline into three severity bands; regression for trend direction; flag co-occurring anomalies | standard | Platform query APIs | Per-metric status table, anomaly list with deviation size and duration, worst-metric-wins service rollup | R1 |
| Cross-service correlator / root-cause analyzer | Reason about the incident as a whole: align events in time, walk the dependency graph symptom-to-source, tie infrastructure events (evictions, restarts, OOM kills) to application impact, compute metric-pair correlations, apply causal domain knowledge; escalate to premium for complex multi-service incidents | standard → premium | Anomaly output, topology API, events API (deployments, orchestrator events, alerts) | Root-cause hypothesis with confidence and evidence chain, correlation matrix, cascade map, incident timeline | R1 |
| Environment comparator | Pair identical metrics across two environments or before/after a deploy; compute deltas, bucket them (match <~10%, minor to ~30%, significant above); for significant gaps inspect resources, config, and traffic to separate code regression from parity gap; emit go/no-go | standard | Both environments' query APIs, same window | Delta table, difference findings, promotion recommendation | R1 |
| Degradation trend analyzer | 1–4 weeks of hourly data: per-metric linear regression, slope-significance test, match trend combinations to known patterns (memory leak, capacity exhaustion, dependency decay, config drift, seasonal load), project time-to-breach and exhaustion dates | standard | Extended historical metrics (7–30 days) | Pattern classification, trend rates, capacity forecast, tiered recommendations (immediate / short-term / strategic) | R1 |
| Report publisher | Assemble the report (verdict badge, summary, status tables, timelines, evidenced root cause, recommendations) as local HTML with charts; fan out sized variants: 3-line chat summary, incident ticket on critical only, pager incident on sustained critical only; label everything AI-generated | economy | All analyzer outputs | Local report file; external wiki page, ticket, chat message, pager incident | R3 |

> The causal judgment — separating cause from effect across a dependency graph — is the only step that earns premium spend, and only when incidents span multiple services. Everything numeric is deterministic math a standard model narrates; publishing is pure templating on economy.

## Flow

1. Trigger fires: platform alert (latency breach, error spike, container restart), scheduled health check, detected deployment, or manual request.
2. Verify preconditions: API reachable, target service reporting, ≥1 week of baseline, thresholds configured.
3. Collect inputs: service name(s), environment, time window, investigation context (alert payload, deployment details, reported symptoms).
4. Fetch golden-signal, infrastructure, and dependency metrics via the platform's native query language.
5. Classify every metric against static thresholds plus rolling baselines into three severity bands; flag significant deviations and trend direction.
6. All healthy on an automated run → publish the routine health report and stop.
7. Otherwise correlate anomalies across services and layers, walk the dependency graph, and build the evidence chain from symptom to root-cause hypothesis.
8. Deployment-triggered runs: execute the paired environment comparison to separate regression from parity effects.
9. Run the multi-week trend lookback for slow degradation and capacity forecasts.
10. Generate the structured report: verdict, summary, per-metric table, anomaly timeline, evidenced root cause, dependency impact, ranked recommendations.
11. **Human review gate** — an engineer validates the hypothesis against system knowledge, confirms recommendations are safe to act on, and sets priority. Rejected hypothesis routes back to step 7 for deeper analysis.
12. Publish by severity: report file always; chat notice on degraded; incident ticket plus pager escalation reserved for critical.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Query metrics, topology, problems, logs | Any major APM/observability platform or open-source metrics stack | Read | Official MCP server; else official CLI; else REST/GraphQL wrapped in a thin skill. Token scoped to read-only. |
| Publish detailed reports | Team wiki / docs platform | Write | Vendor MCP or CLI; pages carry an AI-generated label |
| Create incident tickets | Issue tracker (Jira, Azure DevOps) | Write | Vendor MCP or CLI; critical verdicts only, dedicated AI-analysis label, body carries root cause + evidence + recommendations |
| Send health summaries | Team chat | Write | Chat MCP or incoming webhook; verdict + top anomaly + report link, bot-prefixed |
| Page on-call | Incident paging service | Write | REST API; fires only when critical persists beyond a several-minute window |

> Wiring preference, in order: official MCP → official CLI → REST-in-a-skill → custom code. The query languages differ per vendor; the analytic method does not.

## Guardrails

- **Injection defense** — telemetry, log lines, and event payloads are data to analyze, never instructions to follow. Unattended runs execute as a pinned workflow: fixed step order, fixed model/prompt/toolset per step, no on-the-fly tool selection, so observed content cannot redirect the agent. Triggers are limited to platform alerts and schedules — the workflow must never re-trigger off tickets or pager incidents it just created.
- **Writable-field allowlist** — platform access is read-only by token scope; the agent cannot mutate monitoring config or the systems it observes. Permitted writes: local report file, wiki page, chat message, and (critical-only) ticket and pager event. Every output carries an explicit AI-generated marker. No remediation — no scaling, restarts, or config changes, ever.
- **Human gate** — the reviewer checks that the root-cause hypothesis matches their system knowledge, that recommendations are safe and correctly prioritized, and that evidence actually supports the verdict. Failed validation loops back to deeper investigation; it never proceeds.
- **Grounding** — every claim cites queried numbers: current value, baseline, deviation magnitude, duration. No vague qualitative statements. Each report records service, environment, window, platform, query identifiers, timestamp, and a dashboard link to the identical window so a human can verify independently. Before wiring any automation, run a first-time smoke test confirming the agent's verdict matches the dashboard.

## Automation

Pin into an unattended workflow once the pipeline is stable: triggers are a schedule (hourly/daily health check), a platform alert, or a deployment event; each step runs a fixed model, prompt, and toolset. Keep the flexible human-invoked agent for ad-hoc investigations where the engineer steers.

Trigger → flow: alert/schedule/deploy → fetch golden signals → classify against baselines → all-healthy auto-publishes a routine report and stops → anomalous runs continue through correlation, week-long trend lookback, and report generation → degraded auto-publishes report + chat notice → critical additionally opens a ticket and pages on-call, then an engineer reviews before anyone remediates. Never let ticket or pager creation act as a trigger — that is a feedback loop.

Keep the human gate on everything at first. Above ~80% measured acceptance, graduate low-risk steps: auto-publish non-critical reports, then auto-open critical tickets with pre-remediation review. High-risk actions (scaling, restarts) keep mandatory review indefinitely; auto-remediation for well-known patterns is a question for after 6+ months of validated recommendations, not before.

## Signals it's working

| Signal | How to measure |
|---|---|
| Fleet coverage | Services with AI-tagged reports vs total services the platform knows; manual review covers a handful, automation should cover the fleet |
| Alert-to-root-cause time | Alert timestamp to report timestamp; compare against historical MTTR and the 30–60 min manual baseline |
| Alert investigation coverage | Share of fired alerts receiving an automated investigation vs the historical manually-investigated share (often ~a third, top-severity only) |
| Root-cause acceptance rate | In post-mortems, record whether the AI hypothesis matched the confirmed cause; low acceptance at high adoption means the correlator needs more topology and incident-history context |
| Team feedback quality | Retrospectives on hypothesis accuracy, recommendation actionability, false-positive investigations, time saved |
| Proactive catch rate | Degradations flagged by the trend analyzer weeks before any threshold alert — the strongest measure of value over plain alerting |
