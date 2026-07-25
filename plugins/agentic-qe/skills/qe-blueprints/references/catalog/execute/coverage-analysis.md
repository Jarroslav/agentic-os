# Analyze test coverage

Turn a scope identifier (story, sprint, epic, or release) into a per-acceptance-criterion requirements-to-tests coverage report with prioritized gap recommendations, so holes surface at test design time instead of just before release.

## When to use this

- **Reach for it when** traceability links between tests and requirements are patchy because nobody maintains them; manual coverage mapping is slow, error-prone, and gaps keep appearing late; you need criterion-level resolution (a story with five criteria and one tested must read as partial, not covered); or you want a weekly / per-sprint snapshot pushed to the tracker, wiki, or chat automatically.
- **Skip it when** acceptance criteria are paragraph blobs — per-criterion mapping is the entire value, so fix the requirement-writing standard first; there is no readable tracker or test-management source to map between; what you actually need is line/branch instrumentation, not requirements traceability; or a small manual pilot shows the model crediting tangential tests — scaling that would bury real gaps under an official-looking report.
- **Outcome** a recurring structured report — criterion-status table, story-level rollup, inventory of tests linked to nothing, and categorized missing-scenario recommendations — that QA acts on before the next design cycle.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Read access to the requirements tracker, scoped fetch of stories + acceptance criteria | Mapping starts from requirements; no scoped retrieval, no report | API token or connector for Jira / Azure DevOps |
| Read access to the test management system, including existing traceability links | Each criterion is judged against the tests already linked to its story | API token or connector for Xray, Zephyr Scale, or Azure Test Plans |
| Criteria written as discrete numbered/bulleted items | Criterion-level assessment is the point; blobs collapse everything to story level | Team requirement-writing standard |
| One publishing destination with write rights | The report must land where the team already looks | Tracker comment/task rights, wiki page-create, chat webhook, or a local markdown path |
| Machine-readable label for AI-produced output | Adoption metrics need to separate agent reports from manual ones | Agreed tag/label convention on pages, tickets, comments |
| A manual single-story pilot before wiring connectors | Paste one story plus 3–10 linked tests and check the classification against careful human judgment before scaling | Any chat-based assistant session; zero connector setup |

## Agent design

Three narrow roles keep cost and blast radius separated: a cheap fetcher, a mid-tier judge, and a cheap append-only publisher. The only reasoning-heavy work — deciding whether a test genuinely exercises a criterion — sits in the middle.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Retriever | Pull in-scope stories + criteria from the tracker and test cases + link records from the TMS | economy | Tracker work items; TMS tests and links, filtered by scope | Run-local dataset for the generator | R0 |
| Coverage generator | Classify each criterion covered / partial / uncovered under strict credit; roll up to story verdicts; compute summary stats; list unlinked tests; draft prioritized missing-scenario recommendations by category (happy path, negative, boundary, edge) | standard | Retrieved dataset | Structured report artifact | R1 |
| Publisher | Deliver the report to each configured destination as a new item only, stamped with the AI footer and label | economy | Report artifact + destination config | New tracker comment/task, new timestamped wiki page, chat post, new local file | R3 |

> The split matters because the R3 step must be trivially auditable: the publisher makes no judgments, only appends. All judgment lives at R1 on a standard tier where a wrong call costs a correction, not a corrupted source system.

## Flow

1. Trigger — QA engineer invokes with a scope parameter (story, sprint, epic, project, or release id), or the weekly schedule fires.
2. Retrieve stories and their acceptance criteria from the tracker within scope.
3. Retrieve test cases and existing traceability links from the TMS.
4. Classify coverage per criterion (covered / partial / uncovered) with strict credit; roll criterion statuses up to a story verdict.
5. Assemble the report: summary counts and percentages per status, linked/unlinked test totals, per-requirement table with gap notes, unlinked-test section, categorized prioritized recommendations.
6. On retrieval failure (dead TMS connection, empty scope), loop the error back for retry — nothing publishes until inputs are sound.
7. Publish: tracker comment for single-story scope, new task item for wider scopes, new timestamped wiki page, chat summary, and/or local markdown file — every output labeled AI-generated.
8. **Human review gate** (post-delivery) — a QA engineer or lead checks the findings against their own judgment, logs where the assessment missed, and works the gap recommendations before the next test design cycle. Note the R3 publish precedes this gate deliberately: outputs are append-only and labeled, so the gate reviews rather than approves. Keep it until acceptance data says otherwise.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Fetch stories + criteria | Issue tracker (e.g. Jira) | Read | Official MCP connector or CLI; service account read-only on scoped items |
| Fetch work items + criteria (alternative tracker) | Azure DevOps boards | Read | Official connector package or platform CLI; read on scope |
| Fetch tests + traceability links | TMS (Xray, Zephyr Scale, Azure Test Plans) | Read | Official connector or CLI for the TMS family; read on tests and links |
| Publish report into the tracker | Issue tracker | Write | Official connector/CLI with create rights; comment for single story, new task for sprint/epic/release |
| Publish documentation page | Team wiki | Write | Official connector/CLI with page-create; new timestamped page per run |
| Notify the team | Chat (Slack, Teams) | Write | Incoming webhook for text; connector if you want card layouts |
| Write local report file | Filesystem / repo | Write | Plain file write; new timestamped file per run |

> Wiring preference, in order: official MCP connector, then official CLI, then REST/SDK wrapped in a skill, then fully custom code only as a last resort.

## Guardrails

- **Injection defense** — every fetched ticket, criterion, and test step is data to analyze, never an instruction to follow. The unattended variant runs as a pinned workflow: fixed step order, pinned model and toolset per step, no dynamic tool selection, so hostile ticket text cannot summon new tool calls. Never bind the trigger to tracker-update events — the workflow's own posted comment or ticket would re-fire it in a loop. Manual invocation or schedule only.
- **Writable-field allowlist** — append-only across the board: new comments, new tasks, new timestamped wiki pages, new chat posts, new local files. The agent never edits requirements, test cases, or traceability links. Every output carries the AI footer and machine-readable label.
- **Human gate** — review happens after delivery, not before. The reviewer validates gap findings against their own read of the scope, records corrections (these feed prompt tuning), and pushes vague-criteria problems upstream to the requirement-writing standard instead of patching the prompt around them.
- **Grounding** — strict credit: a test counts toward a criterion only when its steps directly exercise that criterion's behavior; adjacent or tangential tests earn nothing. Criteria too vague to assess are marked partial, not guessed. Every report records its input scope and links back to the source work items so any line can be verified.

## Automation

Run attended while calibrating: an orchestrating session dispatches retrieval, generation, and publishing with a human free to redirect mid-run. Pin to unattended once the pilot and a few attended runs show acceptable accuracy — same steps in fixed order with pinned tiers, prompts, and tools per step, because predictability beats flexibility when nobody is watching.

Trigger (manual scope invocation or weekly schedule) -> fetch requirements + criteria -> fetch tests + links -> classify and assemble report -> publish to configured destinations. Retrieval failures retry before anything publishes. Keep the post-delivery human gate in both modes; drop it only when acceptance-rate data over several sprints justifies it. Never event-trigger from tracker updates — self-retriggering loop.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption — share of coverage reports produced by the agent | Filter tracker/wiki exports by the AI label vs manually authored reports in the same window |
| Productivity — hours saved per report vs manual baseline | Retrospective estimate of historical manual mapping effort per sprint vs agent-run effort |
| Acceptance — gap findings matching reviewer judgment | Log agreements and corrections during post-report reviews |
| Team feedback on accuracy, granularity, actionability | Collect at retrospectives; read jointly with adoption — high adoption + low acceptance means tune the matching logic; high acceptance + low adoption means fix the delivery channel |

Out of scope: this blueprint finds and ranks gaps — it does not write the missing tests, repair vague requirements, edit or create traceability links, execute tests, measure code-level coverage, or act as a blocking release gate. It informs human sign-off; it does not replace it.
