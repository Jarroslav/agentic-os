# Debug flaky tests

Turn archived CI run history and trimmed logs into a validated, published per-test flakiness report so intermittent failures arrive as a triage-ready queue each morning instead of a manual log dig.

## When to use this

- **Reach for it when** QA burns hours telling intermittent failures apart from real regressions; root-causing unstable tests is slow or guesswork; you want per-test flakiness scores and pattern classification over a rolling build window; recurring failure clusters hint at shared fixes nobody has surfaced; a nightly hands-off stability report into the tracker would slot into the team's triage routine.
- **Skip it when** fewer than ~20 archived runs exist or test IDs don't survive refactors (scores become noise); failures are constant, not intermittent — those are regressions and belong elsewhere; a reporting platform the team already uses covers flake detection natively (a custom pipeline only pays off for multi-system aggregation, a custom taxonomy, or automated tracker publishing); CI archives no structured results or logs, so there is no evidence to reason over.
- **Outcome** — a ranked stability report: per-test score with sample size, a five-way root-cause category, a concrete code-level fix, a rule-derived priority, suite-level systemic recommendations, plus two appendices (constant failers; possible regressions). Delivered to tracker tickets, a wiki page, a chat summary, and/or a repo markdown file — with triage resolutions looped back for accuracy tuning.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Read access to the CI platform: list runs, fetch per-test pass/fail records, download log artifacts for a window | Run history plus logs is the pipeline's only evidence; without programmatic retrieval nothing downstream works | CI/build platform (hosted or on-prem) |
| Structured result artifacts (standard XML test reports at minimum) archived for ~20+ builds per suite | Flakiness is statistical — it only shows across repeated runs; under ~10 runs you over- or under-flag | CI artifact storage or results store |
| A stable per-test identifier that survives refactors, ideally with suite/owner tags | History must correlate across runs to score, group, and route findings | Test framework naming conventions or reporting-platform IDs |
| Tracker write access: create/update tickets, apply a dedicated AI-origin label, attach evidence, comment | Publication, dedup, and the feedback loop all run through tickets and their resolutions | Issue tracker service account |
| A small project-owned log-trimming script producing per-test stack traces, deduplicated errors, and anomaly signals, capped near 50 KB per test | Raw logs run to hundreds of MB; the model should reason over evidence, not parse streams | Project repo (deterministic script, runs before the analyzer) |
| Greenfield suites: wire up archiving and stable IDs, then accumulate ~20 mixed pass/fail builds before the first run | You need a baseline before noise can be told from pattern | CI pipeline configuration |

## Agent design

Four roles: an orchestrator that sequences the run, an analyzer that does the statistical scoring and root-cause reasoning, a validator that gates every entry against traceability rules, and a publisher that fans the validated report out to destinations. Judgment lives in the analyzer; the validator and publisher are mechanical and run cheap.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Orchestrator | Collects inputs (suite, window, occurrence threshold); dispatches retrieval, generation, validation, publication; routes validator rejections back to the analyzer. Unattended: becomes a fixed sequence with pinned models/tools | standard | Run config, connector outputs, validator verdicts | Dispatch state only | R0 |
| Flakiness analyzer | Per candidate: pass/fail ratio over the window as score; classifies into five categories (timing, environment, isolation, data, test-order); root cause from the pass-vs-fail log diff; concrete fix with rule-derived priority. Also suite-level recommendations (quarantine >~30%, shared helpers for clusters, retry strategy, infra signals, process changes) and both appendices | standard | Trimmed per-test evidence, run history, project context (suite layout, known-unstable areas, critical-path tags) | Draft report (run artifact) | R1 |
| Report validator | Gates each entry: mixed signal (≥1 pass AND ≥1 fail in window) plus occurrence threshold (fails in ≥N of last M runs, default 3/20); completeness (category, non-generic fix, rule-consistent priority with justification, log snippet). Emits ready/partial/missing; blocks publication on failure | economy | Draft report, threshold params | Validation verdict (run artifact) | R1 |
| Report publisher | One ticket per flagged test (or bulk suite ticket) with field mapping (name→summary, score+sample→description, fix→acceptance criteria, priority→priority, snippet→attachment); dedup by test name + AI label; per-period wiki page; single chat/email summary with priority counts; optional root markdown file. Every output AI-labeled and linked to analyzed build IDs | economy | Validated report | Tracker tickets, wiki page, chat/email message, one repo markdown file | R3 |

> The split keeps the only reasoning-heavy step (log-diff root-causing) on one focused agent with pre-trimmed input, while gating and publishing stay deterministic enough for economy models — the validator enforces evidence rules by checklist, not judgment, so a cheap model gating an expensive one costs little and catches ungrounded entries before they hit the tracker.

## Flow

1. Trigger: QA engineer invokes on demand for a suite/window, or a nightly schedule fires after the daily CI suite completes.
2. Precondition check: ~20 archived runs with stable test IDs exist; inputs fix the window, minimum occurrences, and the mixed-signal requirement.
3. Retrieve run history, per-test pass/fail records, and log excerpts from the CI platform and results store.
4. Deterministic preprocessing condenses raw logs into per-test stack traces, deduplicated errors, and anomaly signals (timeouts, retries, latency spikes), capping model input near 50 KB per test.
5. Analyzer scores each candidate, classifies it against the five-way taxonomy, writes an evidence-grounded root cause and concrete fix with derived priority, and appends suite-level recommendations plus both appendices.
6. Validator applies the two-part gate and completeness checks; failed or partial entries loop back to the analyzer for gap-filling before anything publishes.
7. Publisher delivers to configured destinations with ticket dedup, AI-origin labels, and links to the analyzed build IDs.
8. **Human review gate** (deliberately post-publication — see Guardrails): QA triages the tickets in their normal workflow, closing each as fixed, not-a-flake (false positive, optionally with a dedicated label), or won't-fix. This replaces pre-publish approval so the nightly cycle never blocks.
9. Triage resolutions feed the acceptance-rate metric; thresholds, taxonomy, and the analyzer prompt are tuned from that signal over subsequent cycles.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Fetch run history, per-test outcomes, log excerpts | CI/build platforms (hosted or self-managed) | Read | Official MCP or CLI where available; REST otherwise; service account needs read on artifacts and log archives |
| Fetch structured result artifacts per build | XML test reports on disk, or test-reporting platforms | Read | Direct file read for XML; REST for reporting platforms (no official MCP assumed) |
| Trim and structure raw logs pre-model | Local project-owned script | Read | Fixed pipeline step ahead of the analyzer; no server or MCP |
| Create/update flaky-test tickets with evidence | Defect/issue tracker | Write | Vendor MCP or official CLI; create+update permission; dedup by test name + AI label |
| Publish the periodic stability page | Team wiki/docs space | Write | Vendor MCP or official CLI; page created or overwritten per period |
| Post summary alert with priority counts (optional) | Team chat or email | Write | Chat MCP, mail API, or SMTP; single message linking the full report |

> Wiring preference in order: official MCP → official CLI → REST wrapped in a skill → custom code. Drop down a level only when the one above doesn't exist for the system.

## Guardrails

- **Injection defense** — raw CI logs are untrusted, high-volume input. A deterministic project-owned script reduces them to stack traces, error lines, and anomaly signals before any model reasons over them; the model never parses raw streams. The unattended trigger must be purely time-based (cron) and must never subscribe to events from the tracker it writes to — ticket creation would re-fire the pipeline in a loop.
- **Writable-field allowlist** — tracker: summary, description, acceptance-criteria field, priority, log-snippet attachment, and a mandatory AI-origin label on every created ticket; existing tickets are updated (matched by test name + label), never duplicated. Wiki: one stability page per period, created or overwritten. Chat/email: one summary message. Repo: one named root markdown file, overwritten each run, prefixed with an AI-generated marker. Nothing else is written; test code is never modified.
- **Human gate** — intentionally after publication, not before: flakiness classification is probabilistic and false positives are expected, so reports publish directly and review happens during normal ticket triage. Each resolution (fixed / not-a-flake / won't-fix) is the control signal; growing confidence tightens thresholds and priority rules without restructuring the loop.
- **Grounding** — two-part traceability gate: a flagged test needs a mixed signal (≥1 pass and ≥1 fail in window — pure-pass is stable, pure-fail is a real failure routed to its appendix) and the occurrence threshold (≥N of last M runs, default 3/20); sub-threshold single failures land in the possible-regressions appendix rather than vanishing. Root causes must cite specific log lines and code symbols; fixes must be concrete code actions (a named wait API, a selector swap, a teardown step) — "investigate further" is rejected. Priority is derived, never free-form: high at score ≥40% or critical-path suite or state-corruption risk; medium at 20–39% off the critical path; low under 20% or where a documented retry exists. Failures outside the five categories extend the taxonomy; never force-fit.

## Automation

Pin into an unattended workflow — fixed step sequence, pinned model/prompt/tools per step, no on-the-fly tool choice — once the manual version has run a few cycles. Nightly cron (around 02:00 UTC, after the daily suite finishes) fits because flakiness is statistical: a daily pass over a rolling window catches emerging flakes without spending tokens on every CI build; per-run retriggering is out of scope.

Trigger → flow: schedule fires → fetch last N runs and result artifacts → preprocess logs → analyzer drafts the report → validator gates (rejects loop back) → publisher delivers to tracker/wiki/chat → QA triages next morning and resolutions feed the acceptance metric.

Keep manual invocation available for on-demand analysis of a specific suite or window. The post-publish triage gate stays regardless of automation maturity — it is the tuning signal, not a bottleneck; never wire the trigger to tracker webhooks (self-retrigger risk).

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption — share of flaky tests found via the agent vs manually per sprint | Query tracker for AI-labeled vs manually created flaky-test tickets; or count automated report runs vs ad-hoc investigations |
| Productivity — average hours per flaky-test investigation before vs after | Engineers log investigation time for two sprints pre- and post-adoption; compute (manual − AI) / manual |
| Acceptance rate — fixed / (fixed + not-a-flake) over a rolling window | Query tracker by AI-origin label and resolution field, including the false-positive label; a declining rate means the analyzer needs tuning (taxonomy mismatch, loose threshold, or noisy preprocessing) |
| Team feedback on root-cause accuracy, fix actionability, taxonomy fit | Structured questions in sprint retrospectives |
| Combined diagnostic — where to tune | High adoption + low acceptance: enrich the analyzer prompt with project-specific failure examples or adjust the taxonomy. High acceptance + low adoption: friction is in connectors or trigger setup — revisit CI integration and enable the nightly schedule |
