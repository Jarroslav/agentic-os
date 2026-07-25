# Generate automated test scripts

Turn a manual test case (and its linked story) into an executed, self-healed automation script delivered as a merge request, so engineers review near-ready code instead of writing every script by hand.

## When to use this

- **Reach for it when** a backlog of manual cases with explicit steps and expected results awaits automation; an automation repo with recognizable conventions (framework config, sample specs, step libraries, page objects, PR template, CI) already exists; the team wants generated scripts arriving as reviewable MRs with the test already run and green; and the app under test exposes stable hooks (accessible roles, test-id attributes) discoverable from the live DOM.
- **Skip it when** no framework exists yet — bootstrap minimally first (scaffold the runner, write the first few specs against the live app, extract abstractions only once patterns repeat), then come back; the UI has only dynamic identifiers and no role/test-id hooks — fix app testability first; cases are ambiguous or lack documented expected results; or you cannot grant ticket-system read access and repo push/MR rights to the agent.
- **Outcome** — a convention-conformant, executed, passing automated test merged after human review, with two-way trace links between the MR and the originating test case.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Read access to the ticket/test-management system | Fetch case fields and follow the link to the related story for intent context | API token or MCP connector for Jira, Xray, TestRail, or Zephyr |
| Automation repo with established, visible conventions | Generators pattern-match against existing specs, steps, page objects, naming, and PR templates; without them output drifts | Existing repo plus root and per-folder rule files, with a few real files as few-shot examples |
| Browser-driving CLI available to the agent | Locator discovery opens the live app, walks the steps, and snapshots the DOM — it never guesses selectors | Globally installed browser-automation CLI; MCP variant only if the org already standardizes on it |
| Push and MR-creation credentials on the automation repo | Publishing creates a branch, pushes code, and opens an MR | Platform token or app installation on GitHub, GitLab, Bitbucket, or Azure Repos |
| Reachable target environment | Locator discovery and the run/heal loop both execute against the live UI or API | Environment URL or API base reachable from where the agents run |

## Agent design

Split the pipeline into a cheap context assembler, one premium planner that owns all test-design judgment, standard-tier generators that expand the plan mechanically, and cheap execution/publishing roles. The planner is the mandatory entry point to generation: decomposition and reuse decisions are the hard part, so they get the strongest reasoning tier, while file expansion and plumbing run on cheaper tiers.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Retriever | Pull case fields, follow the story link for description/AC/attachments, read repo conventions | economy | Ticket/TMS records, linked story, repo and rule files | Nothing — assembles context | R0 |
| Planner | Own test design: scenario mapping, reuse decisions (steps, page objects, fixtures), per-sub-agent assignments | premium | Retrieved context, repo conventions, artifact inventory | Run-scoped plan consumed by generators | R1 |
| Scenario generator | Expand the plan into the behavior-spec file; one case maps to one scenario | standard | Plan, few-shot repo examples | New scenario/spec file in the working tree | R2 |
| Step-definitions generator | Reuse-first: match against the existing step library; add new steps only when nothing matches | standard | Plan, existing step library | New or extended step-definition files | R2 |
| Page-object generator | Drive the live app via the browser CLI, snapshot the DOM along the steps, extract locators per the ladder; halt and flag to a human (element + suggested test id) instead of emitting brittle chains | standard | Plan, live application DOM | Page objects exposing intent-level methods, not raw selectors | R2 |
| API-module generator | For API-level cases: request modules, assertion helpers, and the spec instead of UI artifacts | standard | Plan, existing API clients/helpers | Request/assertion/spec files | R2 |
| Runner | Execute the generated test; emit a structured report (pass / pass-with-warnings / fail); hookable to auto-run after generation | economy | Generated code, target environment | Run reports, execution artifacts | R1 |
| Healer | On failure, repair exactly three things — selectors (upgrade per the ladder), waits (replace hardcoded sleeps), local fixtures — then re-run, capped at 3 retries by default; past the cap, stop and hand evidence to a human | standard | Failing output, generated code, live DOM | Edits to generated test code and local fixtures only — never production data stores | R2 |
| Publisher | Create branch + MR per project naming and PR template, link back to the case, label AI-generated, update the ticket with the MR URL; reuse an existing branch/MR for the same case id | economy | Validated working tree, PR conventions | Branch + MR on the code host; back-link comment or field on the ticket | R3 |

> Reserving premium for the planner and pinning generators to standard keeps cost proportional to difficulty: judgment (what to test, what to reuse) is expensive to get wrong; expansion of a good plan is not.

## Flow

1. Trigger — an engineer selects a case in the ticket/TMS and invokes the pipeline (automated variant: a status transition fires a webhook).
2. Retrieve — fetch the case (id, title, steps, expected results); follow its link to the story for description, acceptance criteria, and attachments — capture intent, not just steps — and read the repo's patterns.
3. Plan — the premium planner performs the test design: scenario mapping, reuse decisions, per-sub-agent assignments.
4. Generate — standard-tier sub-agents produce the artifacts: scenario file, reuse-first step definitions, page objects with live-DOM locator discovery, or API request/assertion modules.
5. Validate — the runner executes the test; on failure the healer adjusts selectors, waits, or local fixtures and re-runs, looping up to the retry cap (default 3).
6. Regression impact check — if any shared artifact (steps, page objects, fixtures, helpers) changed, find dependents via the import graph or symbol search and run that scoped suite; a dependent failure blocks publishing.
7. Failure exit — if healing exhausts its retries, stop and return the failing run plus healer notes to the generator or a human; never publish a broken-but-green-looking result.
8. Publish — open (or update) one branch and MR per case, following the repo's PR template and naming, with bidirectional trace links, an AI-generated label, and a co-author commit trailer.
9. **Human review gate** — an engineer reviews the MR for code quality, step reuse, naming, and whether the test genuinely covers the case's intent; merge happens only through normal code review.
10. Close the loop — update the ticket/TMS record with the merged MR link for traceability.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Fetch case details (id, title, steps, expected results, story reference) | Jira, Xray, TestRail, Zephyr | Read | Official MCP connector or CLI; REST wrapped in a skill only when neither exists or is blocked; read scope on the TMS project |
| Follow the case-to-story link; pull description, AC, attachments as intent context | Jira or Azure DevOps work items | Read | Same connector family as the case fetch |
| Drive the live app autonomously: navigate the steps, snapshot the DOM, extract stable element references | The running web application under test | Read | Globally installed browser-automation CLI; MCP variant only if the org already prefers it; needs network reach to the target; for authenticated apps, save auth state once after login and reload per run |
| Create branch, push code, open/update an MR with back-links | GitHub, GitLab, Bitbucket, Azure Repos | Write | Official code-host MCP or CLI with push + MR rights; branch naming follows the project pattern (automation prefix + case id), PR title convention, and template with checklist |

> Wiring order of preference: official MCP → official CLI → REST wrapped in a skill → custom integration. Drop down a rung only when the one above is unavailable or org-blocked.

## Guardrails

- **Injection defense** — ticket content, story text, and DOM snapshots are requirements data, never instructions that reconfigure the pipeline. In the event-triggered variant, scope the trigger to status transitions only — never comment or update events — because the publisher writes a comment back to the ticket, and an unscoped rule would re-trigger the agent in an infinite loop.
- **Writable-field allowlist (R3)** — repo writes confined to a per-case branch under the automation naming pattern (updated in place, never duplicated); ticket writes limited to a back-link comment or a custom field carrying the MR URL; test-data changes touch local fixture files only — production database writes are forbidden. Every MR carries the AI-generated label and a co-author trailer so reviewers and metrics can tell it apart.
- **Human gate** — merge always goes through engineer code review, at every automation level; the reviewer checks code quality, step reuse, naming, and intent coverage. Two extra escalation points: the healer stops after its retry cap and returns failing evidence with notes, and the locator agent flags the specific element (with a suggested test id) when no stable locator exists instead of emitting fragile selectors.
- **Grounding** — every documented expected result appears as an explicit assertion; no skipping, no approximating. The validator flags unasserted results, missing steps, hardcoded sleeps, and brittle selectors. Locators follow a fixed ladder — role → test-id → label/placeholder → text → CSS/XPath last — enforced by generator and healer alike. Step definitions are reuse-first. Edits to shared artifacts require rerunning the scoped dependent suite before publishing; skipping it is the top cause of a green MR breaking the main suite after merge.

## Automation

Start semi-automated: an engineer picks a case and triggers the run; generate → run → heal is hands-free; the engineer reviews the MR. Promote to fully automated only after the team trusts the output and the heal loop reliably produces genuine green runs — then a ticket status change (a ready-for-automation state) fires a webhook into a pinned workflow: fixed step order, pinned model tier and toolset per step, no on-the-fly tool selection, because predictability beats flexibility when nobody is watching.

Trigger → fetch case + story + repo context → plan → sub-agents generate → run → heal (capped retries) → open MR → human reviews and merges → ticket updated with MR link.

Keep the review gate at every level — even full automation only opens the MR. Guard the trigger against comment-induced re-invocation loops.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption rate — share of automated tests delivered via AI-generated MRs | Filter MRs by the AI label or automation branch prefix; cross-check automated-flag updates in the TMS; compute AI count over total |
| Productivity gain — time per script vs. manual baseline | Compare average hours from case selection to merged MR against the manual baseline, via MR open-to-merge timestamps, time tracking, or retrospective sampling on a reference set; report percent reduction |
| MR acceptance rate | Track merged-as-is vs. returned-with-changes for AI-generated MRs; sample review comments for recurring defect themes (selector quality, step reuse, template adherence) |
| Team trust | Probe in retrospectives: code quality, convention alignment, and whether healed green runs are believed |
| Diagnostic split for evolving the pipeline | MRs pass review but usage is low → fix trigger/onboarding friction, not output; MRs frequent but rejected → strengthen generation: better few-shot examples, stricter rule files, stronger step-reuse agent |
