# Select tests by risk

Turn a cycle's change set, defect history, incident records, and a metadata-rich test catalog into a ranked, time-budgeted regression subset with a written justification per test — so scoping is fast, defensible, and auditable instead of gut-feel.

## When to use this

- **Reach for it when** full regression is too slow or costly per release; scoping is done by intuition and can't be justified after the fact; you need a subset that fits a stated execution-time budget with a rationale on every row; change/defect/incident signals live in queryable systems and the catalog carries component, priority, and duration metadata.
- **Skip it when** the suite is small enough to run in full every cycle; tests lack component tags, duration estimates, or requirement links (the scorer has nothing to score); the team has no written risk rubric — a vague rubric produces generic, indefensible rankings; there is no accessible change, defect, or incident history for the product area.
- **Outcome** — a ranked include/optional/exclude selection that fits the budget, cites the concrete change or risk behind every included test, flags changed areas left uncovered, and publishes with full traceability to the originating cycle.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Test catalog with component tag, priority, duration estimate, automation status, recent results/flakiness | These fields are the scorer's raw inputs; without them per-test scoring is impossible | Test-management system or reporting platform |
| Requirement-to-test links (every test tied to at least one requirement/feature) | Maps requirement changes onto the tests they touch | TMS / tracker link fields |
| Read access to defect history and production-incident records | Defect density and incident severity are two of the four scoring factors | Issue tracker + incident-platform APIs |
| Written, team-agreed risk rubric: factors, weights, thresholds | The planner applies it verbatim; an unstated rubric forces the model to invent one and kills defensibility | Team wiki, agreed before first run |
| Read access to the cycle's changed requirements and impacted components | Change recency is the leading factor and anchors every rationale to a real change | Issue tracker / requirements wiki API |

## Agent design

Split retrieval, judgment, expansion, and publishing into four roles. The scoring judgment — weighting four factors, applying an 80/20 lens, fitting a time budget — sits alone on the premium tier because its quality propagates into every downstream row; everything around it is mechanical and runs on economy.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Data retriever | Pull all scoring inputs for the cycle: changed requirements, catalog + execution history, defects, incidents, optional component-criticality map | economy | Tracker, requirements wiki, TMS/reporting, incident platform, optional config/architecture store | In-run working set only | R0 |
| Risk planner (orchestrator) | Score components on four weighted factors (change recency, defect density, incident severity, business criticality); apply 80/20 prioritization and the time-budget constraint; emit ranked risk profile with include/exclude recommendations | premium | All retrieved signals + the written rubric | Ranked risk-profile artifact | R1 |
| Test-set generator | Expand the profile into one row per test — score with factor breakdown, decision, change-citing rationale, requirement links, duration, automation status — enforcing built-in checks: every high-risk changed area has an included test, every score shows its factors, total fits the budget | economy | Planner profile, catalog + history, change/defect/incident metadata | Per-test selection table artifact | R1 |
| Publisher | Push the approved set outward: create/update the cycle's regression run/plan keyed by cycle id (no duplicates), post a wiki summary, export a spreadsheet; stamp everything with an AI-selection label and two-way links | economy | Approved selection table | TMS run/plan, wiki page, export file | R3 |

> No separate validator role: the generator's coverage, factor-breakdown, and budget checks are built in, and the human reviewer validates the result. Adding one buys nothing.

## Flow

1. A test lead or engineer triggers a cycle with a release, sprint, or build identifier.
2. Verify preconditions: tagged catalog, requirement-test links, reachable defect/incident sources, written rubric. Stop if any is missing.
3. Retrieve inputs: requirement changes for the cycle; catalog with execution history; defects (severity, frequency, reopen rate); incidents (severity, recency, affected module); optionally component criticality from an architecture or configuration store.
4. Plan: the premium planner applies the weighted four-factor rubric with 80/20 prioritization and constraint optimization, producing a ranked per-component risk profile with include/exclude recommendations under the budget.
5. Generate: the economy generator expands the profile into the per-test table and runs its coverage, breakdown, and budget checks.
6. **Human review gate**: the test lead checks scores against domain knowledge, confirms no critical area is uncovered, overrides where context beats the model (e.g., low technical risk but organizationally sensitive), and approves or returns the set for re-scoring. Nothing publishes without this.
7. Publish: write the approved set to the TMS as the cycle's regression run/plan (re-runs within a cycle update, never duplicate), post the wiki summary, export the spreadsheet — all labeled AI-selected with two-way traceability.
8. Measure and tune: track adoption, acceptance, and override patterns; a factor reviewers keep overruling means its rubric weight needs adjusting.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| fetch-requirements | Issue tracker / requirements wiki (Jira, Azure DevOps, Confluence) | Read | Official MCP or CLI; changed requirement ids, change types, linked components |
| fetch-test-catalog | TMS (TestRail, Xray, Zephyr, Azure Test Plans) or reporting platform | Read | Tracker-hosted TMS via the tracker's MCP/CLI; otherwise REST wrapped in a skill |
| fetch-defects | Defect tracker (Jira, Azure DevOps) | Read | Official MCP or CLI; severity, frequency, reopen rate, component per defect |
| fetch-incidents | Incident platform (PagerDuty, ServiceNow) | Read | Rarely has an official MCP — REST in a custom skill; severity, recency, module |
| fetch-architecture (optional) | CMDB, architecture docs, wiki | Read | Wiki MCP/CLI where available, REST otherwise; criticality and dependency maps |
| publish-to-tms | Test-management system | Write | Tracker MCP/CLI if TMS lives in the tracker, REST otherwise; decision → scope flag, score/factors → custom fields, rationale → notes; needs run/plan create-update rights |
| publish-to-wiki | Team wiki / docs space | Write | Official MCP/CLI; summary page with risk profile, rationale, coverage overview |
| export-file | Local or shared drive | Write | Plain file write; spreadsheet with every generator column for offline analysis |

> Wiring preference, in order: official MCP server → official CLI → REST wrapped in a skill → custom integration. Drop down only when the level above doesn't exist.

## Guardrails

- **Injection defense** — text pulled from tickets, incidents, and wiki pages is scoring data, never instructions. When change context is thin, the scorer returns an explicit neutral no-signal value for the history factor instead of fabricating evidence.
- **Writable-field allowlist** — the R3 write touches only: the cycle's regression run/plan (scope flags, custom score/factor fields, notes, traceability links), one wiki summary page, one export file. Requirements, defects, and incidents stay read-only. Every published artifact carries the AI-selection label, mirrored as a tag on linked tracker items, so adoption stays measurable.
- **Human gate** — a test lead approves before anything publishes: sanity-check scores against team knowledge, confirm no critical area is uncovered, override where domain context wins, return for re-scoring when needed. Mandatory at introduction; lighten only when adoption and acceptance metrics justify it.
- **Grounding** — only tests present in the supplied catalog may appear; every score exposes its four-factor breakdown; every include cites the concrete change or risk it covers; total included duration is checked against the stated budget; any changed area with zero included tests surfaces as a coverage gap; publishing keys on the cycle id so re-runs update rather than duplicate.

## Automation

Start human-invoked: the lead supplies a cycle identifier, the fixed sequence runs (retrieve → premium planner scores → economy generator builds the set → publish to TMS, wiki, export), and the lead reviews, re-running with adjustments as needed. Validate before wiring anything: paste a change list and catalog table into a single prompt carrying the explicit rubric and time budget, and compare the ranking against a senior tester's pick — connect the systems only if it matches. To go unattended later: `ticket status change or nightly schedule -> retrieve -> plan -> generate -> gate -> publish`, with model, prompt, and toolset pinned per step and no on-the-fly tool selection — once nobody is watching, predictability outranks flexibility. Keep the human gate until adoption and acceptance numbers earn its removal.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption rate | AI-labeled selection cycles vs manually curated ones (label filter in the TMS plus a manual-selection tracker or shared dashboard); AI cycles / total, reviewed monthly |
| Productivity gain | Analyst hours per selection cycle, AI-assisted vs manual, from start/end timestamps validated by retrospective sampling; secondary: trigger-to-approved-set elapsed time |
| Acceptance rate | Share of selections published unchanged vs returned or overridden in review; high adoption + low acceptance → tune rubric weights; high acceptance + low adoption → fix process/tooling friction |
| Team feedback | Structured retro questions on score accuracy, clarity of per-test justification, and real decision time saved |
| Override patterns | Which factors reviewers consistently overrule — locates systematic gaps in the rubric |
