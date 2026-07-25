# Run tests and report results

Turn a release scope identifier plus tracker, test-execution, and wiki data into a validated, human-approved Go/No-Go readiness report with every metric traceable to a source record.

## When to use this

- **Reach for it when** a release, iteration, or build needs a formal readiness verdict aggregated from executions, open defects, and story status scattered across systems; when verdicts drift between cycles because each lead applies a private rubric; when the same code-freeze metrics table and blocker list gets rebuilt by hand every cycle; or as a zero-connector trial — paste exported result/story/defect tables into one agent with the default rubric before wiring anything.
- **Skip it when** no concrete scope filter exists (version field, iteration path, test plan id, launch name); when the execution export lacks linked-defect references — failures can't be tied to blockers, so fix the export first; when tracker or execution-source read access is missing; or when the team wants the agent to own the ship decision — the human gate here is non-negotiable.
- **Outcome** — a stakeholder-ready report (verdict, rationale, per-criterion metrics table, top blockers with root-cause hypotheses, risks, next actions) published to the wiki, summarized on the release ticket, plus a machine-readable metrics sidecar for trend dashboards.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Tracker read credentials | List in-scope stories and open defects via the scope query | API token / PAT with read scope on the release project |
| Test-execution source read credentials | Pass/fail/blocked results with linked defects are the core quality signal | API token for the configured results system |
| Release scope identifier | Wrong scope silently corrupts every metric | Team convention: version field, iteration path, test plan id, or launch name |
| Agreed readiness rubric (or accepted default) | The verdict is rubric-driven; without agreement the output can't be trusted | Written rubric in repo/wiki, or sign-off on default: 0 open blocker/critical defects, pass rate ≥ 95%, all top-priority stories done, no untriaged defects older than 2 days |
| Write access to publishing targets | Final step creates/updates a wiki page and comments on the release ticket | Account with create/update on the wiki space and comment permission on the ticket |

## Agent design

Split retrieval, judgment, expansion, checking, and publishing into separate roles so the expensive reasoning happens exactly once — deciding what the rubric means against the data at hand — while everything mechanical (fetching, prose expansion, publishing) runs on cheap tiers, and an independent validator stands between generation and any external write.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Data Retriever | Parallel fetch: stories + open defects (tracker), execution results (results system), prior cycle's report (wiki, optional, for trends) | economy | Tracker scope query, results filter, wiki | Nothing external; raw records to downstream stages | R0 |
| Readiness Planner | Map each rubric criterion to configured sources, flag unevaluable criteria, set precedence on conflicting signals (one open blocker beats a high pass rate; mass skips beat a good pass rate on the rest). Decides weighting — never writes prose | premium | Rubric, retrieved records, source config | Run artifact: per-criterion checklist (criterion, data needed, source, decision logic, gap risk) | R1 |
| Report Generator | Expand the checklist into the report: verdict + rationale, one metrics-table row per criterion (pass/partial/fail), ≤5 top blockers each with a root-cause hypothesis, risks, actions, footer naming systems read and when. Verdict on one screen, detail below. No verdict logic of its own | economy | Planner checklist + raw records | Run artifact: draft report, every figure citing a retrieved record | R1 |
| Consistency Validator | Every number/ticket key traces to a record; every criterion addressed; verdict logically matches the metrics (open blocker + positive verdict fails); rates in 0–100%, counts ≥ 0. On failure: block and return findings to the Generator | standard | Draft, checklist, records | Run artifact: per-check pass/partial/fail report with offending lines | R1 |
| Report Publisher | Wiki page per release (rerun updates in place, keyed by release id, so reviewers see the diff); one append-only summary comment per run on the ticket; JSON metrics sidecar attached; bi-directional page↔ticket links; AI-provenance labels (draft prefix until approved) | economy | Approved report + metrics | Wiki page, ticket comment, attachment, labels | R3 |

> Only the planner carries judgment, so only the planner needs premium reasoning; the generator and publisher are deterministic expansion and I/O. Keeping verdict logic out of the generator also means fetched free text can never steer the decision.

## Flow

1. **Trigger** — QA lead or release manager invokes with a release identifier; alternatives: scheduled run in the code-freeze window, or the release ticket entering a sign-off status.
2. **Precondition check** — scope filter defined, tracker and results source reachable, rubric present (custom or default).
3. **Retrieve** — parallel pulls: stories and open defects, execution results, optionally the prior report for trend deltas.
4. **Plan** — premium reasoning maps criteria to available data, marks unevaluable criteria, resolves signal conflicts by precedence, emits the criterion checklist.
5. **Generate** — economy expansion turns the checklist into the full report; each criterion becomes a metrics row; every figure cites its record.
6. **Validate** — traceability, coverage, verdict-consistency, and plausibility checks; any failure blocks publication and loops back to step 5.
7. **Human review gate** (mandatory; never removed regardless of measured accuracy) — the QA lead or release manager inspects verdict, metrics, and blockers; may edit rationale, escalate caveats, or send the run back with an adjusted rubric. A wrong Go ships a regression; a wrong No-Go stalls the release.
8. **Publish** — wiki page created or updated in place, one append-only ticket comment, JSON sidecar attached, cross-links and provenance labels applied.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| In-scope stories + open defects | Work tracker (issue platform or DevOps boards) | Read | Official MCP or CLI; scoped by version field, iteration path, or saved query |
| Execution results with linked defects | Test-management tool, test-plans module, or launch-reporting platform | Read | MCP/CLI when the results system rides the tracker's platform; otherwise REST wrapped in a skill (some options have no official MCP). Wire only what the team actually uses |
| Prior release report (optional, trends) | Team wiki | Read | Wiki MCP or CLI |
| Publish report page + JSON sidecar | Team wiki | Write | Wiki MCP/CLI with create-and-update permission; the wiki's storage markup differs from rendered text — tables and issue-link macros need native storage format, verify rendering once at setup |
| Verdict summary on release ticket | Work tracker | Write | Tracker MCP/CLI with comment permission; one new comment per run, history preserved |

> Order of preference everywhere: official MCP server → official CLI → REST wrapped in a skill → fully custom integration.

## Guardrails

- **Injection defense** — fetched ticket text and test names are evidence, not instructions. Verdict logic lives only in the planner's rubric-derived checklist; the generator may not re-derive decisions; the validator rejects claims not anchored to a retrieved record. Free text inside tickets therefore has no path into the verdict.
- **Writable-field allowlist** — exactly three write surfaces: the wiki report page (create, or update-in-place keyed by release id), one append-only ticket comment per run, and the JSON sidecar plus provenance labels. No ticket fields edited, no status transitions, no defects created or closed.
- **Human gate** — the reviewer checks that the verdict follows from the metrics, blockers cite real tickets, and data-gap flags are honest; they can approve, edit rationale, escalate caveats, or force regeneration with an adjusted rubric. Permanent by design: verdict errors carry asymmetric cost in both directions.
- **Grounding** — every metric, rate, and ticket key must trace to a fetched record; inventing ids, counts, or percentages is prohibited. Missing data becomes an explicit "not provided" risk, never an estimate. Sanity bounds apply (rates 0–100%, counts ≥ 0). A partial validation mark usually signals a retrieval gap hiding behind vague wording; a verdict-consistency failure forces regeneration, not manual patching. Publication stays blocked until validation passes.

## Automation

Start human-invoked. Pin into an unattended workflow when acceptance is high but adoption is low — the friction is invocation, not quality. Trigger (code-freeze schedule, or release ticket → sign-off status) → fixed step sequence with pinned tiers and pinned connectors, no dynamic tool selection: without a human steering mid-run, predictability beats flexibility. The human review gate stays in the flow even under automatic triggering. Inverse case — high adoption, low acceptance — means do not automate further; tune the planner's criterion weighting and feed the generator real example reports instead.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption rate — AI-drafted report published vs manually built | Shared QA-lead log, one row per release with AI/manual column, cross-checked against provenance-labeled wiki pages |
| Productivity gain — reviewer hours editing the draft vs hours to build manually | Retrospective self-logging at sign-off in the same shared log; gain = relative reduction |
| Acceptance rate — verdicts published unchanged vs overridden in review | Log each override with a free-text reason; recurring reasons drive prompt and rubric tuning |
| Qualitative trust — confidence in the verdict, visibility of data-gap flags, clarity of blocker section | Structured feedback at release retrospectives |
| Provenance integrity — drafts re-tagged as approved after review | Label transitions on page and comment; keeps adoption/acceptance measurable |
