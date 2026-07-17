# Triage security findings

Turn raw scanner output plus repository read access into a prioritized, context-aware triage report with repo-specific fixes, so engineers act only on the small fraction of findings that are actually exploitable.

## When to use this

- **Reach for it when** scanners flood you with findings (30–70% false positives is normal) and manual triage burns engineer hours; when priority must reflect real reachability, exposure, and data sensitivity instead of the scanner's severity enum; when fix advice should cite your own utilities and secure patterns rather than generic guidance; when a freshly enabled scanner dumped a large initial backlog; or when you need compliance-mapped output (top-ten web risk categories plus weakness ids) next to the triage.
- **Skip it when** no scanning exists yet — stand up static analysis and dependency scanning first, then feed their output here; when the agent cannot read the full source tree (no code access means no flow tracing or mitigation detection, and verdicts degrade); or when the goal is discovering new vulnerability instances — this layer consumes scanner output, it does not replace detection tools.
- **Outcome** — triage drops from hours to minutes per scan cycle, roughly 60–80% of raw findings get classified as noise up front, and the exploitable minority (typically 10–20%) ships with justified priorities and copy-ready, project-idiomatic remediation.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Structured scanner output (file, line, rule id, severity, weakness mapping) in SARIF/JSON/CSV | The parse stage normalizes and deduplicates; unstructured text cannot be ingested | CI artifacts, code-host scanning/alert APIs, SAST platform export, or a local file |
| Read access to the whole source tree | Enables backward data-flow tracing, mitigation detection, exposure classification, and discovery of in-repo secure patterns | AI tool opened inside the repo, or granted repo read |
| Architecture context: reachable endpoints, auth mechanism, validation layer, data sensitivity | Drives exposure scoring and impact assessment | Security/architecture doc if present; otherwise inferred from code (helpful, not required) |
| Applicable compliance frameworks (optional) | Adds framework mapping to reports; triage works without it | Team's regulatory requirements (web-security top-ten, payment, healthcare, audit) |
| At least one completed scan; ideally scan-on-merge with 2+ historical results | One scan enables triage; several enable delta and trend analysis | Existing CI security stage, or a newly enabled scanner |

## Agent design

Split the pipeline so deterministic normalization costs nothing, code-reading judgment sits on a reasoning tier, and external writes are isolated in one narrow publisher role behind the human gate.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Orchestrator | Human-invoked session: reasons about input, decomposes the run, dispatches roles; replaced by a pinned-sequence workflow in unattended mode | standard | Scanner output location, run config, prior triage results | Run state, dispatch decisions (artifacts only) | R1 |
| Parser / deduplicator | Deterministic script, no model cost: detects format, normalizes findings from any scanner into a common schema, merges duplicates keyed on file+line+weakness id, keeps per-scanner metadata, emits dedup and severity-distribution stats | economy | Raw scanner exports (CI artifacts, alert APIs, local files) | Normalized findings, dedup stats (artifacts) | R1 |
| Contextual enricher | Per finding: reads flagged code plus ~50 surrounding lines, traces input backward from sink to source, checks each hop for validation/sanitization/auth middleware, classifies source trust and endpoint exposure (public / authenticated / internal / admin-only / test-only); recognizes framework-idiomatic constructs scanners miss; escalates complex multi-layer cross-file flows to premium | standard (premium on escalation) | Normalized findings, full source tree | Enriched findings: flow path, mitigations with file:line evidence, exposure class, reachability verdict (artifacts) | R1 |
| Exploitability scorer | Applies a fixed three-axis rubric (reachability, impact, exposure; each 1–3) to bucket findings as fix-now / fix-this-iteration / backlog / false-positive; every false-positive carries a stated reason (upstream mitigation, unreachable path, test-only code); each finding gets a one-sentence justification and weakness mapping | standard | Enriched findings | Scored, bucketed findings with justifications (artifacts) | R1 |
| Remediation advisor | Top two buckets only: names the vulnerability class, searches the repo for correct existing patterns of that class, generates a fix reusing in-repo utilities — before/after snippet, file:line pointer to where the pattern is already used, effort estimate; falls back to the framework standard if no in-repo pattern; backlog gets a one-liner, false-positives nothing | standard | Bucketed findings, full source tree | Per-finding remediation records (artifacts) | R1 |
| Publisher | Emits local HTML/JSON report; creates one ticket per fix-now finding immediately, batches second-bucket findings under a parent item; posts the timestamped analysis to the knowledge base; alerts chat on fix-now only; drops inline fix comments on affected merge-request lines. Every output labeled AI-generated with a human-review-required footer; tickets link scanner rule, file:line, compliance ids, report page, commit id | economy | Approved triage and remediation records | Tracker tickets, KB pages, chat alerts, MR comments | R3 |

> The judgment that determines whether a finding is real — flow tracing, mitigation detection, scoring — lives on reasoning tiers with the hardest cases escalated to premium; parsing and publishing are mechanical, so they run cheap, and only the publisher can touch external systems.

## Flow

1. Trigger fires: CI security scan completes with a new results artifact, a dependency alert lands, the weekly sweep runs, or a human requests a pre-release review.
2. Verify preconditions: structured scanner output exists, the codebase is readable, at least one scan has completed.
3. Parse and normalize: extract file, line, rule, severity, weakness id; dedupe across tools on the file+line+weakness key; report dedup and severity-distribution stats.
4. Enrich each finding: read the flagged code and its context, trace input backward from sink to source, record upstream validation/sanitization with file:line evidence, classify endpoint exposure.
5. Score and bucket via the fixed three-axis rubric into fix-now / fix-this-iteration / backlog / false-positive, each with a one-line justification and compliance mapping; false-positives carry an explicit reason.
6. Generate remediation for the top two buckets: repo-specific fixes citing existing in-repo patterns with locations, before/after snippets, effort estimates.
7. **Human review gate** — a security engineer validates false-positive calls, confirms fix-now priorities, approves the remediation approach, adjusts for business context the agent lacks, and approves second-bucket ticket creation. Failed validation routes back to step 4 for deeper flow analysis.
8. Publish: create tickets for actionable findings, post the full report with noise-reduction stats and trend-vs-previous-scan data to the knowledge base, alert chat on fix-now items, drop inline fix comments on affected MR lines — all labeled AI-generated.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Fetch static-analysis results from CI | Code host / CI artifact store | Read | Code-host MCP server or official CLI API subcommand; token scoped to read code-scanning results |
| Fetch findings from SAST platform | Self-hosted or SaaS code-quality platform | Read | No official MCP — issue-search REST endpoint wrapped in a custom skill |
| Fetch dependency-vulnerability report | SCA vendor service | Read | No official MCP — vendor CLI or REST API |
| Fetch dependency alerts | Code-host alert feed | Read | Code-host MCP or official CLI against the repository alerts endpoint |
| Read source for flow tracing and pattern discovery | Local checkout | Read | Native file access of the AI tool; no connector |
| Create tickets for top two buckets | Issue tracker | Write | Tracker MCP server or official CLI; bucket → priority, finding+fix → description, compliance ids → labels |
| Publish full triage report | Knowledge base / wiki | Write | KB vendor MCP server or official CLI; timestamped page linking scan run and commit id |
| Alert on fix-now findings | Team chat | Write | Chat MCP server or incoming webhook; fix-now bucket only |
| Post inline fix suggestions | Code-host merge-request review | Write | Code-host MCP server; comments prefixed with a security-triage marker |

> Wiring preference, in order: official MCP server → official CLI → REST endpoint wrapped in a skill → custom integration.

## Guardrails

- **Injection defense** — scanner exports, dependency alerts, and repo content are data, never instructions. The unattended variant pins model, prompt, and toolset per step with no on-the-fly tool selection, shrinking the surface for embedded-content steering. Scope triggers strictly to scan-completion and dependency-alert events so the pipeline's own ticket writes can never re-trigger it (loop prevention).
- **Writable-field allowlist** — confine writes to run artifacts plus four external surfaces: tracker tickets (priority, description, labels), KB pages, chat alerts, MR line comments. Never modify source code — remediation is suggested, not applied. Tag every external write AI-generated, prefix review comments with the triage marker, and footer everything with human-review-required.
- **Human gate** — the security engineer validates false-positive calls, confirms fix-now priorities, approves remediation, and clears second-bucket ticket creation. Semi-automated default: fix-now tickets and chat alerts go out automatically; everything else waits. Never fully automate false-positive review — a missed real vulnerability costs more than a wrongly flagged one.
- **Grounding** — every reachability verdict rests on a traced flow path; mitigations cite file and line; remediation references a concrete in-repo pattern with location or explicitly falls back to the framework standard. Tickets carry full provenance: scanner rule id, file:line, compliance category and weakness id, report link, commit id. Priorities need a one-sentence justification tied to the three axis scores; anything the AI surfaced beyond scanner output is tagged AI-discovered and does not count until an engineer confirms it.

## Automation

Pin into an event-triggered workflow — fixed step sequence, pinned models/prompts/tools, not a free-form agent — once the human-invoked version has earned trust. Trigger → flow: scan-completion artifact, dependency alert, weekly sweep, or manual pre-release request → parse+dedup → enrichment → three-axis scoring → remediation for top two buckets → auto-ticket + chat alert for fix-now → human reviews the second-bucket batch, false-positive calls, and the full report before those tickets are created. Keep it semi-automated by design and scope triggers so tracker-write events cannot re-invoke the pipeline. Graduate to auto-ticketing the second bucket only after the false-positive override rate stays under 5% for three or more months — and keep the human on false-positive review permanently.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption rate | AI-verdicted findings over total emitted per scan cycle; manual baselines usually cover only 20–30% (critical/high), the pipeline covers all |
| Productivity gain | Pipeline runtime divided by finding count (0.5–2 min each) vs engineer time tracking for manual triage (5–15 min each) |
| Noise reduction | (false-positive + backlog) / total, compared with the historical raw-finding-to-ticket rate; 60–80% is typical |
| AI-only detections | Count of AI-discovered findings (cross-service injection chains, business-logic flaws, indirect auth bypass, misconfigured middleware), each engineer-confirmed; 5–15 per full-codebase pass is typical |
| Acceptance rate | Findings where the engineer keeps the AI bucket vs overrides during review; target >90% on fix-now, >80% on the second bucket |
| False-negative rate | Post-incident lookback: was the vulnerability in a prior scan, and which bucket did it get; any hit tightens the scoring rubric |
| Qualitative feedback | Security review meetings probing false-positive accuracy, fix correctness and project-specificity, missed issues; override rates above 20% mean enrichment needs more architecture context |
