# Build a load model from production logs

Turn exported production access logs (or dashboard aggregates of them) into a validated, multi-scenario load model so performance tests replay real traffic instead of guesses.

## When to use this

- **Reach for it when** you design or refresh load tests for a system with live traffic; you need endpoint weights, latency percentiles, concurrency envelopes, and dependency load grounded in real data; the raw volume (tens of millions of lines per week) rules out manual analysis or feeding logs to a model directly; or you want a weekly refresh as traffic drifts. A cheap first pass — one prompt over a few hundred pasted lines or a couple of dashboard screenshots — proves feasibility before you build the pipeline.
- **Skip it when** the system is pre-launch with no traffic to sample; log access or retention is missing, or the format cannot be documented even minimally; a single-endpoint service where a hand-written profile is faster; or you only have dashboard aggregates but specifically need journey or dependency reconstruction — those require request-level data.
- **Outcome** — an approved wiki page holding the full load model: traffic profile, endpoint distribution, reconstructed user journeys, concurrency and dependency models, an endpoint weight table, and parameterized baseline/peak/spike/soak/stress scenarios, all traceable back to the source logs.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Export access to production logs, at least one full week (5+ working days) | Shorter windows hide daily/weekly seasonality and burst windows | Service account with read access on the log platform (Elasticsearch-class or Splunk-class) |
| Documented log schema: columns, delimiter, timestamp format (5–10 line sample) | The parser is generated against the exact format; undocumented formats produce wrong aggregations | Team logging docs, or a pasted header sample |
| Python 3.8+ runtime (script path) or a dashboard with the needed panels (dashboard path) | One of two pre-processing paths must collapse raw volume into structured facts before any model sees it | Engineer workstation, or the observability stack (Grafana-class) over a log datasource |
| Write access to the target wiki space | Approved models publish as pages with traceability metadata and an AI-generated label | Wiki API token or MCP connector with create/update rights |
| Agreed working-hours assumptions, or explicit overrides | Average-vs-peak normalization differs between business-hours and 24/7 systems | Team agreement; default 5-day week × 8 h/day, overridable per run |

## Agent design

Six narrow roles. The pipeline's spine is a mandatory pre-processing gate: raw logs are collapsed into a compact facts file before any reasoning happens, so the expensive premium model only ever sees structured numbers, and formatting, checking, and publishing run on cheap tiers.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Log retriever | Fetch the export for the target window and filters — manual download, or scheduled auto-export in unattended mode | economy | Log platform export/REST API (range, env/service/endpoint filters) | Local log export for this run | R1 |
| Parser/aggregator | Mandatory gate. Path A: from the schema sample, generate a tailored Python parser (format detection, timestamp normalization, field extraction, session grouping, aggregation) the engineer runs locally; budget 1–2 iterations on proprietary formats. Path B: capture dashboard panels (RPS, top endpoints, latency percentiles, error rate, active sessions) via browser automation or the dashboard's JSON data API | standard | Schema sample + full log file (A), or configured panels (B) | Workload-facts JSON across six dimensions — traffic profile, endpoint distribution, user journeys, concurrency, dependencies, load-test intent — plus the parser script; Path B marks journey/dependency dimensions unavailable | R1 |
| Load analysis planner | Interpret the facts: classify seasonality and bursts, rank critical endpoints by volume × error rate × tail latency, reconstruct representative journeys, size the concurrency envelope, attribute dependency-chain load, parameterize five scenario types; emit a checklist mapping 1:1 onto the output document | premium | Workload-facts JSON + assumptions and overrides (never raw logs) | Analysis checklist artifact | R1 |
| Load model generator | Format the checklist into the full document: summary, traffic profile, endpoint table, journeys (or explicit unavailable note), concurrency and dependency models, weight table, five scenario write-ups with concurrency/ramp/duration, assumptions section listing overrides | economy | Planner checklist + run metadata (source, range, filters, parser path) | Draft load model document | R1 |
| Validator | Deterministic checks: document totals within ±5% of the facts file's event count; every present dimension covered; percentiles and error rate on each top-endpoint row; each scenario has concurrency, ramp-up, duration; ≥3 scenario types; overrides listed. Emits consistent/partial/mismatch; failures block publishing | economy | Draft + workload-facts JSON | Validation report artifact | R1 |
| Publisher | After human approval only: create the wiki page, or update the existing one matched by strict source+range title convention; append traceability footer (source, range, filters, parser version or dashboard id) and apply the AI-generated label | economy | Approved final document | One wiki page per run (external) | R3 |

> Interpretation — spotting bursts, ranking risk, stitching journeys — is genuine judgment and sits alone on the premium tier. Everything around it (fetch, parse, format, check, publish) is mechanical and runs on economy/standard, keeping cost flat as log volume grows.

## Flow

1. Trigger: an engineer uploads a log export on demand, or a weekly schedule auto-exports the previous week.
2. Precondition check: export spans ≥5 working days, schema is documented, working-hours assumptions are set or overridden.
3. Pre-process (mandatory gate): the parser script or dashboard capture reduces raw logs to the workload-facts file. No downstream role ever receives raw log content.
4. Analyze: the premium planner interprets all six dimensions and emits the analysis checklist.
5. Draft: the economy generator formats the checklist into the complete document.
6. Validate: deterministic checks on count traceability (±5%), dimension coverage, per-row and per-scenario completeness. On failure, route back — analysis gaps to the planner, data gaps (e.g., dropped lines) to the parser. Never forward.
7. **Human review gate**: a performance engineer reviews the draft, adjusts assumptions if needed, and approves or returns it for regeneration.
8. Publish (R3): push the approved document to the wiki with traceability footer and AI-generated label; same-source/same-range pages are updated, never duplicated.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Log export download | Log analytics platform (Elasticsearch-class, Splunk-class) | Read | No official MCP exists — wrap the REST API in a custom skill; read-only service account |
| Parser generation + local run | Coding agent + local Python 3 | Read/Write | Agent writes the script from the schema sample; engineer runs it via CLI against the full file (minutes even at scale) — no external connector |
| Dashboard panel capture | Observability tool (Grafana-class) | Read | Browser-automation MCP for screenshots; prefer the JSON data API where exposed — fetching data beats reading charts |
| Load model publishing | Team wiki (Confluence-class) | Write | Official MCP, else official CLI, else REST fallback; create/update rights in the target space; label every page |

> Wiring preference everywhere: official MCP → official CLI → REST-in-a-skill → custom code. Drop down a level only when the one above doesn't exist.

## Guardrails

- **Injection defense** — raw log lines and dashboard text are untrusted data, never instructions. The pre-processing gate means no model ingests raw log text at scale: the reasoning step consumes a numeric/structural facts file, so instruction-like strings embedded in logs are aggregated away, not interpreted. Treat any residual free-text field as data.
- **Writable-field allowlist** — until the final step, roles write only run artifacts (facts file, parser script, checklist, draft, validation report). The publisher's R3 write is exactly one wiki page per run, matched strictly by the source+range title convention before updating, always carrying the AI-generated label. No ticket, repo, or config writes ever.
- **Human gate** — the reviewer checks peak classification, journey plausibility, concurrency envelope, and the assumptions section; they approve, adjust assumptions, or send it back. Mandatory in both attended and scheduled modes — nothing reaches the wiki without it.
- **Grounding** — document totals must land within ±5% of the facts file's event count; a mismatch usually means the parser dropped lines — fix the parser, do not proceed. Every page footer cites source system, range, filters, and parser version. Missing dimensions (no session ids ⇒ no journeys) are flagged unavailable, never fabricated: a flagged partial is fine, a silent gap is not.

## Automation

Pin this as a fixed workflow, not a free-form agent: predefined step order with pinned tier, prompt, and toolset per step, because unattended runs need predictability more than flexibility. Trigger → flow: weekly schedule (e.g., early Monday UTC) → export last week's logs → parser/dashboard capture → facts file → premium analysis → economy draft → deterministic validation → human review → publish on approval. Keep manual upload for on-demand runs. Keep the human gate even on schedule — remove it only if acceptance metrics stay high enough long enough to justify it. Loop guard: if any wiki automation fires on page creation, make sure it cannot re-trigger the export — scope the trigger strictly to the schedule event.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption rate — AI-assisted share of load models | Wiki pages in the performance space with the AI-generated label vs untagged: (AI / total) × 100 |
| Productivity gain — hours per model vs manual baseline | Time tracking or retrospective estimate: ((manual − AI) / manual) × 100 |
| Acceptance rate — models approved without major edits | Review outcomes: published as-is vs returned for regeneration |
| Engineer feedback on quality | Structured retrospectives on peak-detection accuracy, journey completeness, scenario usefulness |
| Adoption/acceptance divergence as a tuning compass | High adoption + low acceptance: improve the parser or analysis prompt — target the most hand-edited dimension. High acceptance + low adoption: friction is in export/parser onboarding, not output quality |
