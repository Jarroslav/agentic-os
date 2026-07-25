# Analyze and report performance results

Turn raw load-test output and web-vitals exports into a severity-ranked SLA compliance report with baseline trend — a release-decision signal minutes after each run, not hours of manual spreadsheet work.

## When to use this

- **Reach for it when** CI emits structured performance results (CSV/JSON/aggregate tables) after every run and someone must check them against numeric SLA/NFR limits; when release managers and non-technical leads need a readable summary instead of raw percentile dumps; when promotion decisions want an evidence-cited go/conditional/no-go input; when trend-vs-last-release reporting is expected and prior artifacts are retained.
- **Skip it when** thresholds are missing, ambiguous, or qualitative — without numeric limits there is nothing to classify against; when results are not stored as a retrievable structured artifact; when the analysis is a one-off — paste results plus limits into a single interactive session instead; when you want performance problems *fixed* — this blueprint reports, it does not remediate, script tests, or generate load.
- **Outcome** — every completed run publishes a severity-grouped compliance report (optionally topped with an advisory release verdict), fully traceable to its run id, with zero fabricated numbers.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Numeric per-metric thresholds (latency percentiles, error rate, throughput, satisfaction index) | Violation classification needs unambiguous limits; fuzzy thresholds are the main cause of bad first runs | Team NFR/SLA reference doc or table |
| Aggregated results in structured form (CSV/JSON/table) | The primary input compared against limits | CI/CD artifact store, from standard load or web-vitals tooling |
| Retained prior-run baseline artifact | Deltas vs the previous release are impossible without it | CI/CD artifact store |
| Environment metadata (name, version, CPU/memory/instance sizing) | Context and reproducibility in the report footer | Deployment docs or the trigger payload |
| Stakeholder-approved report template (sections, severity labels, tone) | The validator checks structure against it; agreeing up front prevents rework at scale | Sign-off from report consumers before scaling |
| Writable delivery destination (wiki page-create rights or a mail list) | Publishing fails without create/update permission | Wiki admin or mail relay config |

## Agent design

Six narrow roles instead of one generalist: a fetcher, a planner that decides *what* to say and *how severe*, a writer that decides only *how to phrase it*, a rule-based validator, an optional release advisor, and a publisher. Judgment (severity classification, trend interpretation, verdicts) sits on premium; mechanical fetching, templated expansion, checking, and delivery sit on economy.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Artifact retriever | Pull current results and baseline from the CI artifact store | economy | CI artifact store (current + baseline) | Nothing — passes data on | R0 |
| Analysis planner | Compare each metric to its limit; p50/p95/p99 analysis; severity: critical when a limit is breached by >20%, warning when within 20% of it, else pass; baseline deltas; group by section and by transaction/endpoint for root-cause hypotheses; emit a JSON plan. Decides content and severity, never wording | premium | Results, baseline, thresholds doc, env metadata | JSON analysis plan (run artifact) | R1 |
| Report generator | Expand the plan section by section: 3–5-sentence plain-language summary (no raw percentiles), compliance table (metric/value/threshold/status), one paragraph plus recommended action per critical, warnings as table rows, trend table + narrative, top-3 recommendations, environment footer; severity-first order | economy | Plan JSON, fetched artifacts, two few-shot report excerpts (one with violations, one clean) | Draft report (run artifact) | R1 |
| Completeness validator | Rule checks: every threshold metric has an explicit verdict; no value differs from source data; severities match the plan; structure matches the template; every critical has an action; trend section present when a baseline exists; summary is percentile-free. Emits pass/partial/missing per check; failures block publishing and return the error list for targeted regeneration | economy | Draft, plan JSON, thresholds doc, source data | Per-check verdict list (run artifact) | R1 |
| Release-gate advisor (release builds only) | Advisory verdict: go (all limits met, no negative trend), conditional go (warnings only, stable/improving trend, risk documented), no-go (any critical, or negative trend across 2+ consecutive runs); one-paragraph rationale citing metrics and trend direction; prepended to the report and dispatched as a separate high-visibility notification | premium | Plan JSON (statuses, deltas, severity counts) + recent-release trend history | Verdict section; standalone stakeholder notification | R3 |
| Publisher | Create-or-update one wiki page per run id, one email per run to the configured list, and always a standalone HTML export as the canonical artifact; titles/subjects carry run id, date, overall status; everything labeled AI-generated | economy | Validated report, publish config | Wiki page, email, HTML export | R3 |

> The planner/generator split keeps the expensive model on the only step that needs judgment. Severity calls and trend reading are reasoning; expanding a JSON plan into templated prose is not — an economy model with two few-shot samples does it reliably, and the validator catches drift.

## Flow

1. **Trigger** — CI finishes a performance run; a post-build webhook hits the agent endpoint with run id, artifact URL, baseline URL, and a release-build flag.
2. **Preconditions** — results reachable, thresholds doc accessible, env metadata present, template configured, destination writable. Abort loudly if any fail.
3. **Retrieve** — fetch current and baseline artifacts, read-only.
4. **Analyze** — premium planner classifies every metric (critical >20% over limit / warning within 20% / pass), runs percentile and delta analysis, emits the JSON plan.
5. **Generate** — economy writer expands the plan into the templated, severity-first report with a non-technical summary.
6. **Validate** — rule checks run; any partial/missing verdict blocks publishing and loops the failing sections back to the generator until all checks pass. No human is paged for this.
7. **Release gate** (release builds only) — premium advisor issues go / conditional-go / no-go with metric-cited rationale, appended to the report and sent as its own notification.
8. **Publish** — wiki page keyed to run id, stakeholder email, canonical HTML export; all carry the AI-generated label and run traceability. Writes are confined to the allowlist below.
9. **Human review gate** — the consequential action, release promotion, belongs to people. Release engineers read the advisory verdict and its cited evidence, then decide. A no-go never blocks publishing or deployment on its own; humans can override, informed. The pipeline's own R3 writes (steps 7–8) are tightly bounded and reversible; promotion is not, so the gate sits in front of it.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Fetch result and baseline artifacts | CI/CD platform (Jenkins, GitHub Actions, GitLab CI) | Read | Official platform MCP or CLI (`gh`/`glab` or a CI-server MCP); service account with artifact-read access only |
| Publish report page | Team wiki (Confluence-class) | Write | Vendor MCP or official CLI, else REST; create/update rights in the target space; one page per run id, labeled ai-generated |
| Send report and verdict notifications | Email via SMTP relay; optionally a chat channel for the verdict | Write | No official connector exists — wrap SMTP in a custom skill or REST webhook; emit inline-safe HTML that mail clients won't strip |

> Wiring preference, always: official MCP → official CLI → REST-in-a-skill → custom-built last.

## Guardrails

- **Injection defense** — every fetched byte (result artifacts, thresholds docs, baseline files) is data, never instructions; nothing embedded in test output may steer the pipeline. Scope the webhook to the build-complete event only — not generic artifact-upload — so the agent's own writes back to CI can never re-trigger it into a loop.
- **Writable-field allowlist** — until validation passes, writes are limited to run artifacts (plan JSON, draft, verdict list). The publisher may only: create/update the wiki page keyed to *its own* run id, mail the pre-configured recipient list, and emit the HTML export. No other repo, CI, or ticket writes. Every published artifact carries an AI-generated footer, label, and run id.
- **Human gate** — the pipeline runs unattended; validation failures loop back automatically. The deliberate human decision is promotion: the verdict is advisory — the agent advises, people decide — and its rationale must name specific metrics, values, and trend direction so an override is an informed one.
- **Grounding** — hard rule: never invent a metric value absent from source data. The validator cross-checks every reported number against the source, requires an explicit verdict for every threshold metric, and requires severities to match the plan. No verdict ships without traceable evidence from the structured analysis output.

## Automation

Pin this into an unattended workflow once the interactive dry run holds up: paste raw results plus thresholds into a single prompt and confirm no violation gets buried, findings are severity-grouped, the summary reads for non-engineers, and no number was fabricated. Then pin — fixed step sequence, pinned model/prompt/toolset per step, no runtime tool selection or decomposition. With no human in the loop, predictability beats flexibility; a free orchestrator has no one to catch its improvisation.

Trigger → flow: CI completion webhook (run id, artifact/baseline URLs, release flag) → fetch → premium threshold/percentile/trend analysis → economy report expansion → validation with loop-back → optional release verdict → publish to wiki/email/HTML.

Keep the promotion-side human gate. The verdict stays advisory until adoption and acceptance metrics (below) make a case for anything stronger — and even then, wiring it to block deployments is out of scope for this blueprint.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption — share of reports produced by the pipeline per sprint | Filter CI logs for completed publish steps, cross-reference wiki pages carrying the ai-generated label; automated/total × 100 |
| Productivity gain — webhook-to-publish minutes vs manual analysis hours | Pipeline timing metadata for automated runs; retrospective sampling with the perf team for the manual baseline; ((manual − automated)/manual) × 100 |
| Acceptance — reports forwarded unchanged vs edited first | Engineers tag each report used-as-is or revised for the first 4–6 weeks after rollout |
| Qualitative feedback on severity accuracy, summary readability, recommendation actionability | Structured questions in sprint retrospectives |
| Tuning heuristic across the two rates | High adoption + low acceptance → the writing step needs work (real few-shot samples, tighter severity limits); high acceptance + low adoption → friction is in trigger setup or delivery, not report quality |
