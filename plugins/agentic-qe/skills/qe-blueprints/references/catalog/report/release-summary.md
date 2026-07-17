# Summarize a release with impact analysis

Turn a release's work items, merged changes, and optional pipeline metadata into one correlated, multi-audience summary with risk ratings and deployment impact — so risks surface before go-live, not after.

## When to use this

- **Reach for it when** release notes and impact write-ups are hand-assembled across tracker, git host, and CI; when test, performance, security, BA, and leadership each need their own view and nobody produces all five; when a regular cadence deserves pre-deploy risk and dependency surfacing; or when you want one correlated dataset that downstream deep-dives (performance, security, regression scoping) can reuse.
- **Skip it when** tracker metadata is too thin to group on (vague titles, missing components, unlinked items) — fix hygiene first; when there is no reliable way to scope a release (no version field, label, or tag convention); or when releases are so small a one-paragraph manual note suffices.
- **Outcome** — a human-approved published summary: per-audience impact sections, risk levels each backed by evidence and paired with mitigations, deployment and rollback notes, and concrete follow-up analysis recommendations, delivered far faster and broader than manual compilation.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Tracker read access queryable by version/sprint/label, returning title, type, priority, status, components, sprint, links | Defines release scope and supplies the metadata everything groups and correlates on | Tracker API token or connector, project read permission |
| Git host read access to list merged changes between two release tags/branches (title, author, files, linked items) | Code-level detail for correlation and deployment/performance/security assessment | Git host token or connector, repo read |
| Consistent release-scoping convention (version field, label, or tag pattern) | The run needs a deterministic answer to "what is in this release" | Team process agreement |
| Component/service taxonomy | Grouping by real components instead of arbitrary clusters | Docs page, tracker component field, or repo instructions file |
| Defined audience roster and their channels | Determines which tailored sections exist and where each routes | Team agreement |
| Writable destination for the final report | The approved summary must land where stakeholders look | Wiki space, chat channel, or shared doc with create/update rights |
| Optional: CI/CD read access for RC build/deploy status | Enriches the deployment-impact section | CI token, connector, or REST API |

## Agent design

Split the work by cost of being wrong. One premium orchestrator does all the judgment — correlation, risk, audience impact — while cheap workers fetch, expand, check, and publish around it.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Data Retriever | Pull release-scoped items, merged changes between tags, optional pipeline status; assemble one aggregated dataset | economy | Tracker, git host, optional CI | Aggregated dataset (run artifact) | R1 |
| Impact Planner (orchestrator) | Group by component; find cross-item correlations and dependency chains; assess each group through five lenses (test, performance, security, BA, leadership); assign probability-x-impact risk levels with justification; flag warranted deep-dives; dispatch workers, re-decomposing per run | premium | Dataset, taxonomy, audience roster | Structured analysis plan (run artifact) | R1 |
| Summary Generator | Expand the plan into the formatted document: overview, per-component change summary, correlations, five standalone audience sections, deployment impact with rollback notes, risks with mitigations, sprint-to-release map, follow-up recommendations; match team tone from examples; keep the leadership section free of item IDs and jargon | economy | Plan plus raw data for reference | Draft summary (run artifact) | R1 |
| Validator | Verify every in-scope item appears, all five sections exist (explicit no-impact statements allowed), risk levels are data-backed, sections name specific components, correlations cite real item keys, recommendations are concrete, nothing invented; emit per-section complete/partial/missing plus item coverage; on failure loop to Generator, escalate to human when input data is the root cause | economy | Draft and dataset | Validation report (run artifact) | R1 |
| Publisher | Post-approval only: create/update one wiki page per version, apply a machine-generated label and a footer naming generator and reviewer, back-link the tracker release record, route audience sections to their channels, optionally fire configured deep-dives | economy | Approved document, routing map | Wiki page, chat posts, tracker back-link | R3 |

> Correlation quality and risk calibration are where the value lives and where errors cost a go/no-go decision — spend premium there. Retrieval, formatting, checklist validation, and publishing are mechanical; economy handles them.

## Flow

1. Trigger: a test or release lead starts a run for a version or sprint, or CI reaches its release-candidate stage.
2. Check preconditions: version/label exists with assigned items, changes are merged and tagged, taxonomy is reachable.
3. Retrieve: work items with metadata and links, merged changes between tags with changed files and linked items, optional pipeline status — into one dataset.
4. Plan (premium): component grouping, cross-item correlation and dependency detection, five-lens impact assessment, justified risk levels, deep-dive flags — as a structured plan.
5. Generate (economy): expand the plan into the full multi-audience document.
6. Validate: completeness, consistency, grounding. On failure loop to step 5 with the report; escalate to the human when the data itself is deficient.
7. **Human review gate**: the test/release lead reviews the draft, verifies risk ratings and audience sections, adjusts levels as needed, and approves. Nothing publishes without this.
8. Publish (R3): create/update the wiki page, route sections to channels, back-link the release record, optionally trigger flagged deep-dives.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Fetch release-scoped work items | Work-item tracker | Read | Official connector or CLI; query by version/sprint/label; needs project read for the service account |
| Fetch merged changes | Git hosting platform | Read | Official connector or CLI; list merged changes and commits between two tags, with authors, files, linked items; repo read |
| Fetch RC build/deploy status (optional) | CI/CD platform | Read | Official connector/CLI where available, else a thin REST wrapper; pipeline read; deployment-section enrichment only |
| Publish summary page | Team wiki / knowledge base | Write | Official connector or CLI; one page per release in a designated space, in-place update with refreshed timestamp if it exists |
| Notify and route audience sections | Team chat | Write | Chat connector or webhook; per-audience channel posts prefixed with a machine-generated marker; post permission per channel |

> Wiring preference in every row: official MCP connector, then official CLI, then REST wrapped in a skill, custom code last.

## Guardrails

- **Injection defense**: everything fetched — item text, commit and change descriptions, pipeline logs — is data to summarize, never instructions to follow. The unattended variant pins model, prompt, and toolset per step with no on-the-fly tool choice, shrinking what embedded text can redirect.
- **Writable-field allowlist**: external writes are exactly three — one wiki page per version (create or in-place update), posts to designated chat channels, one back-link on the tracker release record. Never edit work items, never touch code. Output carries a machine-generated label with the reviewer named in the footer.
- **Human gate**: the lead checks that risk ratings match the evidence, all audience sections are accurate and complete, and no dependency was missed — the document feeds go/no-go decisions where a fabricated risk or overlooked coupling is expensive. Validator failures also hard-block publishing. The pipeline informs the release decision; it never makes it.
- **Grounding**: every claim traces to input data. Every in-scope item appears in the output. Risk levels rest on observable facts (priority, late merges, cross-service touch points). Correlations cite real item keys. When data is missing for a section, say what is missing — do not guess, and do not infer metadata the tracker lacks.

## Automation

Pin into an unattended workflow once the steps are stable: fixed sequence, pinned tiers, prompts, and tools per step — predictability beats flexibility when nobody is steering. Keep the human-invoked agent for ad-hoc or exploratory runs.

Trigger -> flow: release version transitions to released status, OR a version-pattern tag is pushed, OR CI hits the RC stage -> automation rule fires an HTTP call with the version id -> retrieve, plan, generate, validate -> draft waits for the lead -> on approval: publish, route, back-link, optionally fire deep-dives for flagged dimensions.

> Loop guard: the publish step writes back to the tracker record. Scope the trigger strictly to the status transition or tag push — never generic record-update events — or the back-link re-fires the rule.

Start semi-automated (auto-trigger, human-approved publish). Remove the gate only after the risk assessments prove consistently accurate across releases — measured, not assumed.

## Signals it's working

| Signal | How to measure |
|---|---|
| Items summarized and classified | Count in-scope items appearing with both a component and at least one audience-impact tag, by parsing the output |
| Non-obvious cross-references found | Count correlation entries (shared files, dependencies, co-deploy needs); check how many were not already linked in the tracker |
| Net-new risks surfaced | Agent-flagged risks minus those already tracked (risk labels, pre-release checklists) |
| Critical dependencies highlighted | High-severity and cross-service callouts; how many changed the deploy sequence or rollback plan |
| Actionable per-audience insights | Across the five sections, items pairing a specific finding with a recommended action; exclude vague statements |
| Downstream conversion | Share of follow-up recommendations that became created-and-completed tasks, segmented by dimension |
| Risk prediction accuracy | ~3-day post-release retro: precision = flagged risks that materialized / flagged; recall = incidents that were flagged / all incidents |
| Time to insight | Trigger timestamp to draft-ready timestamp |
| Manual effort saved | Historical hand-compilation hours minus review time on the machine draft, sampled retrospectively |
| Audience coverage breadth | Sections produced per release (max five) vs. the one or two views produced manually before |
| Caught-something-we-missed rate (north star) | Ask reviewing leads each release whether the summary surfaced anything the team had not already identified; track yes/no and what |
| False positive rate | Fraction of flagged risks/correlations dismissed in review; high values mean the planner needs tighter specificity — per-audience patterns show which lenses need richer input |
