# Validate API and database schema

Turn a contract fragment, the backing table schema, and one exemplar integration test into framework-native response-shape and database-state checks plus a severity-tagged drift report, delivered as a reviewable pull request.

## When to use this

- **Reach for it when** responses have quietly diverged from the published contract and production is where you find out; when no test asserts what the database holds after an endpoint runs; when contract, response, and persistence layers each get tested differently or not at all — and you already have a versioned contract file, a working integration suite with one exemplar, and read access to the database.
- **Skip it when** there is no single trusted contract file (recover or author one first — without it every downstream step guesses); when the project has neither a test framework nor a contract (bootstrap by hand: commit a small contract for 2–3 key endpoints, export and commit the schema, hand-write one flat exemplar test, let an agent add a few more, adopt the pipeline once patterns settle); or when a trial run on one endpoint yields only generic checks or misses obvious mismatches.
- **Outcome** — a PR against the test repository with at least one response-shape check and one database-state check per in-scope endpoint, plus a drift-report file listing contract/schema mismatches tagged by severity.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Contract file (interface or data-shape schema) committed to source control | Drift detection needs a stable versioned artifact; inferring the contract from code degrades every step | Service repo; export from framework annotations if the contract is only implicit |
| Read-only DB credentials with schema-introspection rights on in-scope tables | Planning state checks and spotting drift requires column types, nullability, constraints, and references | DBA; account limited to SELECT plus metadata queries |
| Integration-test framework with one clean exemplar test | Generated tests copy its layout, helpers, naming, and assertion idioms so output looks native | Team test repository |
| Token able to push a branch and open a PR on the test repo | The terminal output is a PR; no publish rights, no delivery | Service account or scoped token on the hosting platform |
| Reachable non-production API environment | Lets the planner optionally compare live responses against the contract | Staging or test deployment |

## Agent design

Five roles split retrieval, judgment, expansion, checking, and delivery. The single premium slot is the planner, which reasons over contract-vs-schema drift and decides check categories; everything mechanical around it runs on cheaper tiers.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Retriever | Pull contract fragment per endpoint, introspect affected tables (columns, types, nullability, constraints, references), load exemplar for house style, optionally sample live responses | economy | Contract, DB metadata, exemplar, live API | In-memory context for planner | R0 |
| Scope planner | Per endpoint, pick applicable check categories (shape, types, nullability, enums, expected rows, updated columns, referential links, side-effect columns like timestamps/audit rows); enumerate every contract-vs-schema mismatch with severity. Plans only — barred from writing code | premium | Retriever output | Coverage checklist (endpoint / check type / target / severity / notes) + findings list (run artifacts) | R1 |
| Assertion generator | One runnable check per checklist line, in the exemplar's framework and idioms; prefer schema-driven validation over field-by-field equality; fixtures over literal identifiers; emit the drift-report file | standard | Checklist, exemplar, contract, schema | Test files in working tree + drift-report markdown | R2 |
| Coverage validator | Enforce traceability: ≥1 shape check and ≥1 state check per endpoint, every finding in the report, fixtures used, no hard-coded IDs, schema-object validation not copied literals, DB cleanup present; covered/partial/missing per endpoint; failures bounce to generator | economy | Tests, drift report, checklist | Validation report (run artifact) | R1 |
| Publisher | Fresh agent-prefixed branch per run; commit tests + drift report (per-run reports path); PR with conventional title, contract version pinned by commit hash, endpoint scope, source ticket; AI label, co-author trailers, provenance header per file; update an existing same-scope PR instead of duplicating; never touch the default branch | economy | Validated files, run metadata | Branch, commits, PR on test repo | R3 |

> The planner is deliberately code-free so its entire reasoning budget goes to drift detection; letting it also write tests halves the attention spent on the judgment the pipeline exists for.

## Flow

1. A test engineer starts the run, naming endpoints, tables, or both in plain language.
2. **Retrieve** — contract fragment per endpoint, table introspection, exemplar test; optionally sample real responses from the test environment.
3. **Plan** (premium reasoning) — per-endpoint coverage checklist plus severity-tagged mismatch list. No code here.
4. **Generate** — one test per checklist line, exemplar style, schema-driven assertions, fixtures; write the drift report.
5. **Validate** — coverage and traceability rules; failures loop back to step 4. Repeated partials on the same endpoint escalate to the engineer — usually an incomplete contract, not an agent failure.
6. **Publish** — PR on a fresh agent-prefixed branch with traceability links and AI provenance. R2 writes stay in the working tree; the only R3 write is this contained branch-plus-PR.
7. **Human review gate** — before anything merges, the engineer inspects check quality, drift severity, and false positives (over-strict checks that fail on harmless contract additions are the main hazard), then approves, amends, or returns. Nothing reaches the default branch without this step.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Fetch contract file, pin exact version per run | Source-control host or filesystem holding the contract | Read | Platform MCP server or official CLI, whichever holds the file |
| Introspect schema: tables, columns, types, nullability, constraints, references | Mainstream relational engines | Read | Engine MCP server or native client where one exists; else a custom skill over a standard driver; SELECT + metadata only |
| Probe live API against the contract (optional) | Non-production environment | Read | HTTP client (CLI fetcher or browser-automation CLI) wrapped in a custom skill — no official integration exists |
| Push branch, open PR with tests + drift report | Test-repo hosting platform | Write | Platform MCP server or official CLI; token scoped to branch push + PR creation |

> Order of preference for every connector: official MCP server → official CLI → REST wrapped in a skill → fully custom.

## Guardrails

- **Injection defense** — the contract file, database metadata, and any linked ticket are untrusted inputs that the agent reads and then acts on by writing code and publishing a PR. Treat them strictly as data, never as instructions. If the trigger later becomes event-driven on contract changes, harden the trigger endpoint and apply injection-defense guidance there too.
- **Writable-field allowlist** — R3 writes are confined to a fresh agent-prefixed branch: test files in the exemplar's locations, a drift report under a per-run reports directory, and PR metadata (title, description, label). No direct pushes to the default branch; an open same-scope PR is updated, not duplicated.
- **Human gate** — an engineer reviews every PR before merge, weighing check usefulness against noise: schema checks are easy to make so strict they break on benign additions. Validation failures loop internally before anything publishes. The gate may relax to a light skim only as trust accumulates.
- **Grounding** — every check traces to one checklist line; every planner finding appears in the published report. Findings cite the exact table-and-column pair and the exact JSON-path location in the contract. The PR pins the contract version by commit hash and links scope and source ticket. Provenance is marked via label, commit trailers, and a header comment in each generated file.

## Automation

Run it human-invoked today: an engineer triggers from IDE or chat, stating scope in plain words. Once output is consistently accepted, graduate to a pinned unattended workflow (fixed steps, pinned tiers and tools) triggered by commits that modify the contract file — scoped to the default branch only, and excluding the agent's own branch prefix, otherwise the agent's published PR re-triggers the pipeline in an infinite loop.

Trigger → flow: contract change (or manual scope) → retrieve contract, schema, exemplar → plan checklist + drift findings → generate tests + report → validate coverage (failures loop to generation) → publish PR → human reviews and merges.

Keep the human gate in the pinned workflow; drop it only if acceptance metrics over a sustained period justify a lighter check.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption: share of endpoints/tables covered by agent-generated checks | Count files or blocks carrying the provenance header vs the rest; cross-check against the endpoint inventory |
| Productivity: hours per endpoint vs fully manual validation | Ticket time-tracking where available; else quarterly sample of agent-assisted and manual endpoints, ask their owners |
| Acceptance: PR fate — merged clean, merged after edits, closed | Track outcomes; frequent edited merges → stale generator prompt or drifted exemplars; frequent closures → planner picking wrong scope |
| Trust and noise: drift-report false-positive rate, check flakiness on harmless changes | Sprint retrospectives on report accuracy and CI failures from benign changes. Read jointly: high adoption + low acceptance → refresh generator prompt/exemplars; high acceptance + low adoption → improve checklist format and severity tags so engineers trust scope selection |

> Out of scope: bootstrapping a framework and contract on a bare project; inventing abstractions (API page objects, deep fixture trees, assertion mini-languages) — flat test code mirroring the exemplar wins, because agents re-read tests far more often than humans write them; planner-emitted code; autonomous merges; UI or browser end-to-end testing. Scope stays response shape, database state, and contract/schema drift for HTTP-plus-relational-store services.
