# Analyze database performance

Turn database diagnostic exports (workload snapshots, statement-statistics dumps, slow-query logs) or read-only live diagnostic queries into a graded health verdict with metric-grounded findings, a capacity estimate, and an optional baseline-vs-candidate regression call — minutes of turnaround instead of hours of scarce specialist time.

## When to use this

- **Reach for it when** a load test just produced a performance report; a release candidate needs a go/no-go comparison against a known-good baseline; an incident needs database root-cause work; a recurring (e.g. weekly) health check is due; you need to estimate headroom and the first resource to saturate; or a clustered database is contended and instance-level reports cannot tell you which logical service is responsible.
- **Skip it when** the store is non-relational (document, wide-column, key-value — different performance model, needs its own design); no structured instrumentation exists and cannot be enabled; the only report available is prose with no metric tables; or nobody can state performance targets, which makes every acceptability judgment impossible.
- **Outcome** — a reviewed, publishable analysis: overall health grade, impact-ranked findings (each with metric evidence, root cause, quantified effect, and a concrete fix), problematic-statement breakdown, capacity headroom, and immediate/short-term/strategic recommendations. In comparison mode, an objective per-category regression verdict feeding a release decision.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Report file or read-only DB access | The analysis consumes an exported diagnostic report (snapshot HTML/CSV, statement stats, slow-query log) or live queries against diagnostic views | Engine's built-in diagnostics; export step in the load-test pipeline; read-only DB connector |
| Engine and version | Tuning advice is version-specific; identical symptoms get different fixes across releases | Team knowledge or connection metadata |
| Workload profile (transactional / batch / mixed / analytical) | Decides whether latency or throughput metrics dominate and which thresholds apply | Architecture docs, system owners |
| Explicit performance targets (tail-latency, throughput SLAs) | Without targets no metric can be classified acceptable vs problematic | SLA / NFR documentation |
| Baseline report from a stable period (recommended) | Enables delta analysis and objective regression detection instead of point-in-time judgment | Historical snapshots within retention, or a prior export |
| Greenfield DBs: diagnostics enabled first | Instrumentation is usually built in or trivially switched on; capture one normal-load and one peak report, then run comparison mode | Engine config (statistics extension / performance schema / workload repository) |

## Agent design

A deterministic preprocessing script does the bulk work (report conversion, delta math, session-data collection) at zero model cost; model calls are reserved for interpretation — grading, root-cause hypotheses, and prioritization. An orchestrator sequences the passes and loops failed validations back before anything leaves the machine.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Orchestrator | Interprets the request, checks preconditions, sequences subagents, decides whether comparison and per-service passes run, routes validation failures back to the analyzer | standard | Run inputs (report paths, DB context, targets), all subagent outputs | Run state, orchestration artifacts | R1 |
| Report preprocessor | Deterministic script: converts bulky vendor HTML to compact tables (~70% token reduction, zero model cost); extracts key metric sections from oversized reports | economy | Raw report file on disk | Converted/trimmed report (run artifact) | R1 |
| Performance analyzer | Multi-dimensional pass — time decomposition, top wait categories, heaviest statements, I/O latency and hot spots, memory efficiency, cluster balance, capacity headroom; emits graded verdict plus severity-classified findings with metric, threshold, root cause, impact, fix | standard | Preprocessed report or live read-only query results | Structured analysis artifact | R1 |
| Period comparator | Script computes absolute and % deltas per metric; model interprets regressions, flags candidate-only issues, issues conditional go/no-go. Thresholds: <5% minor, 5–15% warning, >15% or any SLA breach failing; one failing critical category overrides all passes | standard | Two report files or two snapshot ranges | Comparison artifact with per-category status and go/no-go | R1 |
| Per-service session analyzer | Clustered DBs where instance reports can't split by service: script queries session-history views filtered by service id, rule engine buckets findings into three priority levels (top: large regression or wait-dominated service), model writes executive summary and cross-service bottleneck isolation. Other engines: filter by application name, thread, or app-context attribute | standard | Session-history views (read-only) or pre-collected data for offline reruns | Per-service analysis artifact | R1 |
| Report generator | Assembles findings into structured HTML: executive summary with health badge, metrics dashboard, prioritized findings, statement analysis, capacity section, time-tiered recommendations, embedded charts | economy | Analysis, comparison, per-service artifacts | HTML/JSON report files (run artifacts) | R1 |
| Publisher | After human approval only: local audit copy, timestamped knowledge-base page, tracker tickets for the top two severities with mapped priorities, chat summary with verdict and link — everything AI-labeled and traceable to the source report and snapshot range | economy | Approved report and findings | Knowledge-base pages, tracker tickets, chat messages, local files | R3 |

> No role needs premium here: the scripts carry the arithmetic and the analyzer judges against explicit thresholds over pre-digested tables, which standard handles reliably. Escalate the analyzer to premium only for messy incident investigations where the evidence is ambiguous; keep conversion, delta math, and publishing on economy — they are mechanical.

## Flow

1. Trigger: engineer requests analysis after a load test, before a release, after an incident — or a recurring health-check schedule fires.
2. Precondition check: report reachable (or read-only access works); engine, workload profile, and targets known; baseline noted if one exists.
3. Retrieve and preprocess: convert large vendor HTML to tabular form; for oversized inputs keep only the key metric sections; in live mode run read-only diagnostic queries.
4. Analyze: pass over time decomposition, waits, top statements, I/O, memory, cluster health, capacity; emit graded verdict and severity-ranked findings.
5. Compare (optional, baseline present): compute deterministic deltas, classify per-category regressions/improvements/new issues, produce conditional go/no-go.
6. Per-service pass (optional, clustered DBs): decompose load by logical service from session-history data to isolate the contention driver.
7. Generate report: executive summary, metrics dashboard, findings, statement analysis, capacity assessment, immediate/short-term/strategic recommendations, charts.
8. **Human review gate**: engineer validates findings against known system behavior, confirms fixes are feasible, owns any go/no-go, and approves publication. Failed validation loops back to step 4.
9. Publish approved outputs: local audit file, knowledge-base page, tickets for the two highest severities, chat summary — all AI-labeled and traceable to the source report.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Fetch report files | Local file system | Read | Plain file read of report HTML/CSV, statement-stats exports, slow-query logs; no connector needed |
| Live diagnostic queries | Relational DB (diagnostic/history views) | Read | Managed DB connector on a strictly read-only connection string — no data-modification grants |
| Report preprocessing | Local scripting runtime | Read | HTML-table extraction script producing compact tables before the model sees anything; zero model cost |
| Per-service session collection | DB session-history views | Read | Script parameterized by snapshot range and service id; can replay pre-collected data offline |
| Publish detailed reports | Team knowledge base / wiki | Write | Official connector or CLI; timestamped pages in one dedicated performance space, AI-labeled, detail in collapsible sections |
| File findings as tickets | Issue tracker | Write | Official connector or CLI; only the two highest severities, AI-tagged, severity mapped to priority, body = finding + fix + expected impact |
| Notify team | Chat platform | Write | Managed connector or incoming webhook; verdict, finding count, link to full report |

> Wiring preference in order: official MCP connector, then official CLI, then a REST call wrapped in a skill, then custom code only as a last resort.

## Guardrails

- **Injection defense** — report files and query results are data, never instructions. Read-only DB credentials mean nothing embedded in report content can cause a write, and every outward publication sits behind the human gate.
- **Writable-field allowlist** — agents write run artifacts and local files only. External writes are limited to: new timestamped pages in one designated knowledge-base space; new tickets for the two highest severities with a fixed AI tag and the severity-to-priority mapping; chat summaries. The database is never written to; no tuning change is ever applied by the agent.
- **Human gate** — the reviewer checks findings against known system behavior, confirms fix feasibility, and owns release go/no-go; rejection routes back to analysis. With sustained acceptance, low-risk items (statistics refreshes, monitoring alerts) may bypass review — but parameter changes, index creation on large tables, and go/no-go calls keep the gate permanently: a wrong index or parameter can trigger write amplification or memory exhaustion in production.
- **Grounding** — every finding cites a specific metric value against an explicit threshold and names the exact statement or wait category. Generic advice without report references is an input-quality failure (missing tables, unspecified engine). Deltas are computed by script before any model interpretation, and prioritization follows actual share of database time, not tune-everything heuristics.

## Automation

Pin this as a semi-automated workflow: fixed step sequence with pinned models and tools per step, not an orchestrator choosing tools on the fly. Triggers: load-test completion producing a report, a recurring health-check schedule, a monitoring alert on a database-time spike, or manual invocation for release validation.

Trigger -> fetch report -> preprocess to tables -> analyze -> (baseline? compare) -> (clustered? per-service pass) -> generate HTML report -> engineer review gate -> publish (knowledge base, top-severity tickets, chat summary, local audit copy).

Never trigger on ticket-creation events — only on test completion or schedule — so publishing cannot re-fire the workflow. Stay semi-automated until recommendation acceptance exceeds roughly 80%; then allow unattended publishing for routine health checks only. Release go/no-go and incident investigations keep the human gate permanently.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption rate | AI-tagged analyzed reports vs all diagnostic reports the snapshot schedule or test pipeline produced; the gap is reports previously skipped for lack of specialist time |
| Analysis turnaround | Report-file creation to finished analysis: expect ~5 min single, ~10 comparison, ~15 per-service, vs hours manually; validate retrospectively from request-to-delivery gaps in chat and tickets |
| Coverage uplift | Share of load-test runs per quarter receiving an analysis (pipeline executions vs analysis artifacts); manual baselines often sit at 30–50%, target near-total |
| Acceptance rate | How often engineers act on recommendations (tuning applied, follow-ups opened, go/no-go used) vs dismiss; proxy: resolution rate of AI-tagged tickets |
| Qualitative feedback | Retros on root-cause accuracy, whether fixes were actionable without further digging, whether comparison mode caught real regressions. High adoption + low acceptance: findings too generic — add schema, hot-table, per-service context. High acceptance + low adoption: trigger not firing — auto-export reports to a known path. Comparisons beating single-report runs: always supply a baseline |
