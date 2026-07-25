# Generate BDD scenarios

Turn a user story with acceptance criteria into a categorized, syntax-valid Gherkin feature file — happy, negative, and edge paths — reviewed by a tester, then published to the repo and the test-management tool.

## When to use this

- **Reach for it when** stories carry written acceptance criteria but converting them to scenario files is slow or inconsistent; negative and boundary cases keep getting cut once the happy path eats the time budget; you want uniform declarative step phrasing across a growing suite; or scenario drafting has to keep pace with story throughput without losing requirement traceability.
- **Skip it when** acceptance criteria are vague or overlapping — fix the requirements first, because no pipeline turns fuzzy criteria into sharp scenarios; when nobody is available to review business intent — the gate is mandatory until metrics say otherwise; or before you have tried the one-prompt single-agent version — that cheap probe tells you whether style and categories fit before you invest in the multi-role pipeline.
- **Outcome** — a full draft feature file with balanced happy/negative/edge coverage in seconds rather than hours, every scenario traceable to a criterion, and testers reviewing drafts instead of hand-writing boilerplate.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Read credentials for the requirements source (title, description, acceptance criteria, persona, priority, epic link) | Scenarios must derive from real story fields, not a retelling | Issue tracker / dev-ops board (Jira, Azure DevOps) |
| Create/update rights in the test-management tool | Publishing cases with traceability links needs write access | TestRail, Xray, or Zephyr account or token |
| Branch push rights or PR-creation rights on the test repo | Approved feature files land in the project's test directory | Git hosting service account |
| Two or three genuine scenario files from the project | Few-shot anchors so generated steps match team phrasing, background usage, and granularity | Existing test repository |
| Team agreement that stories reach this pipeline with clear acceptance criteria | The single largest quality lever; weak criteria produce unusable output | Definition of ready / working agreement |

## Agent design

Five roles split fetch, reasoning, expansion, checking, and publishing. Coverage quality is decided at planning time — deriving negative paths, boundaries, and state transitions from criteria is judgment work — so that one step gets the premium tier. Everything downstream is mechanical expansion or rule-checking and runs on cheaper tiers.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Requirements retriever | Pull title, description, criteria, persona, priority, and parent link from the tracker; hand fields to the planner | economy | Tracker via read connector | Nothing persistent | R0 |
| Coverage planner (orchestrator) | Decompose behavior; apply equivalence partitioning, boundary-value analysis, state-transition analysis, negative-path derivation; output scenario titles with category labels, criterion links, background and outline candidates | premium | Fetched story fields | Coverage-plan run artifact | R1 |
| Scenario generator | Expand each plan line into a scenario or outline with Given/When/Then steps; group by category tags; consolidate shared preconditions into one Background; one scenario per observable behavior; declarative business-level steps only; reuse step wording verbatim for repeated behavior; comment each scenario with its source criterion | economy | Plan, story fields, few-shot examples, team tag conventions | Draft feature file run artifact | R1 |
| Coverage validator | Verify every criterion has a scenario, no orphans, each scenario has Given+When+Then, no duplicates, consistent wording, outlines where parameterization removes repetition, category balance (flag happy-only output); emit covered/partial/missing report; block and loop back on failure | standard | Draft file, plan, criteria | Validation-report run artifact | R1 |
| Publisher | Commit approved files to the test directory (dedupe by path + scenario name) and sync cases to the test tool (dedupe by title + feature link); keep two-way traceability; apply AI-origin markers: case label, in-file tag, commit-message prefix | economy | Approved file, story id | Repo feature files; test-tool cases and links | R3 |

> The premium tier buys reasoning depth exactly where it compounds — a thin plan caps everything after it, while expansion, rule checks, and publishing are deterministic enough for economy/standard tiers.

## Flow

1. **Trigger** — the story enters the ready-for-test-design status, or a tester picks it manually.
2. **Precondition check** — input must contain acceptance criteria, an as-a/I-want/so-that story, or a description rich enough to derive testable behavior. Otherwise stop and send it back for refinement.
3. **Retrieve** — fetch story fields through the read connector.
4. **Plan** — the premium planner applies the five analysis techniques and emits the categorized coverage plan with criterion links and Background/Outline candidates.
5. **Generate** — the economy generator expands the plan into a complete feature file, grouped by category tags, with declarative and consistently phrased steps.
6. **Validate** — rule checks on traceability, syntax, duplication, step consistency, and category balance. Failures loop to the generator until all missing items are cleared and partials resolved.
7. **Human review gate** — a tester confirms the scenarios express actual business intent (not just valid syntax), adjusts wording, adds domain context, then approves, refines, or sends back for regeneration. Nothing publishes without this step.
8. **Publish** — commit the approved file to the repo and sync cases to the test-management tool with bidirectional story links and AI-origin labels.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Fetch requirements | Jira, Azure DevOps boards | Read | Official MCP or CLI; REST wrapped in a skill only if neither exists or is blocked; service account needs read on project stories |
| Commit feature files | GitHub, GitLab, Bitbucket | Write | Official MCP/CLI per platform; custom REST wrapper as last resort; needs branch push or PR-creation rights |
| Publish test cases | TestRail, Xray, Zephyr | Write | Official integration where the tool ships one, REST-in-a-skill otherwise; needs create/update on cases; map feature header → suite, scenario title → case name, steps → case steps, example tables → parameters, category tag → section/label, criterion link → requirement-traceability field — adjust per tool, since some ingest feature files natively and others need structured steps |

> Wiring preference, in order: official MCP → official CLI → REST-in-a-skill → custom code. Drop down a level only when the one above is unavailable or blocked.

## Guardrails

- **Injection defense** — fetched ticket text is raw material for scenario derivation, never instructions to the agents. Also guard the trigger loop: if any step writes back to the tracker, scope the automation rule to the single status transition, never to all update events, or the write re-fires the pipeline.
- **Writable-field allowlist** — repo writes limited to feature files inside the test directory, deduplicated by file path + scenario name. Test-tool writes limited to test cases, deduplicated by scenario title + feature link. Every published item carries AI-origin markers (tool label, in-file tag, commit prefix) so it can be filtered later.
- **Human gate** — the reviewer checks business intent, not syntax: do scenarios describe what the feature must actually do, is domain wording right, is anything asserted that the story never promised. Validator failures never skip to publish; they always return to the generator. Start human-in-the-loop on every run.
- **Grounding** — each scenario cites its source criterion in a comment; the validator rejects orphan scenarios and uncovered criteria. Style is anchored to real project files supplied as few-shot input, and the team's existing tag set must be provided — otherwise the generator invents tags that break runner filters.

## Automation

Pin this into an unattended workflow once the human-invoked version is trusted: same steps as a fixed event-triggered sequence with models, prompts, and tools pinned per step and no runtime tool selection — predictability beats flexibility when nobody is watching. Keep it human-invoked while step style, tag conventions, or acceptance-criteria quality are still settling.

Trigger: tracker automation rule or webhook on the ready-for-test-design transition posts the story id to the agent endpoint → fetch → plan → generate → validate → human review → commit + publish.

Keep the review gate in the pinned variant. Remove it only when adoption and acceptance metrics over a sustained period justify it — and guard the trigger against self-retriggering if the pipeline writes back to the tracker.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption — AI-drafted share of all scenarios | Test-tool export filtered by the AI-origin label plus git history filtered by the commit prefix, versus manually authored files |
| Productivity — time per feature file with vs without assistance | Sprint velocity before/after; cycle time from ready-for-test-design to scenarios committed |
| Acceptance — drafts published unchanged vs reworked | Revision rate at the review gate; share of generated steps kept verbatim vs rewritten |
| Team feedback on quality and time saved | Retrospective questions on scenario quality, phrasing consistency, coverage completeness, and real time savings |
| Category balance drift | Watch for persistent under-generation of negative/edge scenarios; reweight the planner's negative-path technique if it drifts. Read signals jointly: high adoption + low acceptance points at planner logic or phrasing; high acceptance + low adoption points at tooling or trigger friction |
