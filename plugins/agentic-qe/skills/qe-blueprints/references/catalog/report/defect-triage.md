# Triage and prioritize defects

Turn a queue of untriaged defect tickets into consistently scored, duplicate-flagged, team-routed records — severity, priority, owner, target release, and a grounded rationale on every ticket — using the project's own severity/priority rulebook instead of a multi-person triage meeting.

## When to use this

- **Reach for it when** defect inflow makes manual triage a daily bottleneck; severity/priority calls drift between engineers and need normalizing against one rulebook; getting several people to agree per defect delays fixes; a documented scoring matrix exists (or the team will write one) and the tracker exposes read/write APIs.
- **Skip it when** no written severity/priority rules exist — the output will be generic guesswork until rules are codified; defect volume is too small to pay for connector setup; the tracker account cannot edit fields, comment, or apply labels; the rules are vague one-liners — tighten them with concrete examples before automating anything.
- **Outcome** — the morning untriaged queue arrives as a reviewed backlog: every defect scored against the rulebook, duplicate candidates surfaced, routed to an owning team, with an auditable rationale comment on the ticket.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Tracker read access to full defect fields (title, description, repro steps, expected/actual, environment, component, linked story) | The scorer needs complete evidence per ticket; incomplete tickets are skipped, not guessed at | API token or MCP connector on the issue tracker |
| Tracker write access (field edits, comments, labels) | Publishing sets severity/priority/assignee/release and leaves a rationale comment plus audit labels | Service account with edit permission on defect work items |
| Project-owned severity/priority matrix, written down | Every score must map to an explicit rule; rule quality is the ceiling on output quality | Short wiki/knowledge page fetched at run time, so rule edits take effect without prompt changes |
| 2–3 previously triaged defects with their written rationale | Few-shot anchors that lock the model to the team's scoring conventions and rationale style | Real examples exported from the project backlog |
| A connector-free dry run on a handful of pasted defects | Cheap sanity check on rule application and duplicate spotting before granting write access or scheduling | Any chat session with the matrix, one example, and 3–5 raw defects pasted in |

## Agent design

Five roles form a pipeline: an orchestrator sequences work and enforces preconditions, a retriever assembles evidence, a generator applies the matrix, a validator checks structure and grounding, and a publisher — the only role that touches the external tracker — writes the results back.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Orchestrator | Select untriaged tickets, skip and flag incomplete ones, sequence retrieve → generate → validate → review → publish, loop failures back to generation | standard | Tracker query results, run state, validation reports | Run logs, dispatch decisions | R1 |
| Retriever | Fetch defect fields plus the linked user story (description, acceptance criteria, scope) as intent context; load rulebook, few-shot examples, and optionally the open backlog, team routing list, and upcoming release scope | economy | Issue tracker, project docs | Nothing | R0 |
| Triage generator | Apply the matrix per defect, nominate duplicate candidates by similarity against the open backlog, pick owning team and target release, draft a 2–3 sentence rationale citing the rule used and the defect evidence | standard | Defect bundle, rulebook, examples, backlog, routing and release context | Draft triage records (run artifacts) | R1 |
| Validator | Enforce allowed-value membership for every score, confirm the assignee exists, verify the rationale references actual defect content; emit covered/partial/missing; block and return failures; mark all duplicate flags pending human decision | economy | Draft records, allowed-value lists, user directory | Validation report (run artifact) | R1 |
| Publisher | Map record fields to the tracker schema (severity, priority, assignee, fix-version/iteration), post the rationale comment, apply a human-facing triaged label and a machine-applied AI-audit label, skip already-labeled tickets, preserve the defect-to-story link | economy | Approved records, tracker field configuration | Existing defect tickets in the tracker | R3 |

> Scoring against a written matrix is mapping work, not deep reasoning — a standard-tier generator suffices. Retrieval, validation, and publishing are mechanical, so they run on economy. Isolating all external writes in one economy-tier publisher keeps the R3 surface a single, auditable role.

## Flow

1. Trigger — a schedule (nightly is typical) or a manual run queries the tracker for defects lacking the triaged label.
2. Precondition filter — skip tickets missing required fields and flag them back to their reporter; never score on partial evidence.
3. Retrieve — per defect, pull all fields and follow the linked story for intended behavior; load the rulebook, few-shot examples, and optionally the open backlog, routing list, and nearest-release scope.
4. Generate — emit one structured record per defect: severity, priority, duplicate flag with candidate id, owning team/assignee, target release, and a short rationale quoting both the applied rule and the defect evidence.
5. Validate — check allowed values, assignee existence, and rationale grounding; failures return to step 4 instead of proceeding. Duplicate flags are always escalated, never resolved here.
6. **Human review gate** — a QA engineer or lead approves, adjusts, or sends records back for regeneration, and personally decides every flagged duplicate. Nothing reaches the tracker before this step.
7. Publish — update tracker fields, post the rationale comment, apply both labels; skip any ticket already carrying the triaged label to prevent double-processing.
8. Post-run audit (unattended variant only) — reviewers inspect updated tickets in the tracker, filtering by the machine-applied label.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Defect retrieval — untriaged list with full fields, attachments/logs if present, plus traversal of the parent-story link for description, acceptance criteria, scope | Issue tracker (e.g., Jira, Azure DevOps) | Read | Official tracker MCP connector; official CLI as fallback; service account needs project read access |
| Triage context — scoring rulebook, prior triaged examples, open backlog for duplicate matching, component/team routing list, nearest-release scope | Issue tracker plus project docs/wiki | Read | Same MCP/CLI order; the rulebook stays in a project-owned doc fetched at run time |
| Triage publishing — set severity, priority, assignee, fix-version/iteration; post rationale comment; apply both audit labels | Issue tracker (e.g., Jira, Azure DevOps) | Write | Official MCP, then official CLI, then a REST/SDK wrapper as a custom skill only if neither exists or is allowed; account needs field-edit, comment, and label rights; verify custom field ids against the instance schema before first run |

> Wiring preference in order: official MCP connector → official CLI → REST-in-a-skill → custom integration. Drop down a level only when the one above does not exist or is not permitted.

## Guardrails

- **Injection defense** — defect descriptions and comments are reporter-supplied text; treat them strictly as data to score, never as instructions. Scope the unattended trigger to a label-absence query only — never fire on comment or update events, or the agent's own rationale comment re-triggers the run in a loop.
- **Writable-field allowlist** — the publisher may touch only severity, priority, assignee, and target-release/iteration fields, one rationale comment, and the two audit labels. It never closes tickets, never auto-links or auto-closes duplicates, never edits titles/descriptions/repro steps, and skips anything already labeled triaged.
- **Human gate** — in interactive mode the reviewer checks every record before publish and owns all duplicate decisions; relax the gate only after adoption and acceptance metrics justify it. In the unattended variant, review shifts to post-publish auditing filtered by the machine-applied label.
- **Grounding** — every score must cite a specific rule from the documented matrix; rationales must reference actual defect content, enforced by the validator rather than left as convention. Few-shot examples anchor style. Duplicate detection only nominates candidates. The top failure mode is a vague rulebook — fix the rules, not the prompt.

## Automation

Pin the interactive pipeline into a fixed-sequence workflow — predefined steps, pinned model, prompt, and toolset per step, no on-the-fly tool choice — once the dry run and a stretch of interactive use hold up. Trigger it from a scheduler (nightly is typical) or a manual kick.

Trigger → flow: untriaged-label-absent query → retrieve context → generate records → publish field updates, comment, and labels → humans audit the labeled tickets afterward in the tracker.

Keep the in-flow human gate until adoption and acceptance metrics justify removing it; only the unattended variant trades it for post-publish audit, and the AI-audit label keeps every machine-processed ticket filterable. Scope the trigger strictly to the label-absence query so the workflow cannot re-trigger off its own comments.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption rate — share of triaged defects processed by the agent | Tracker counts of tickets with the AI-audit label vs. all tickets with the triaged label; compute the ratio |
| Productivity gain — less time defects sit untriaged | Compare average time-in-status for new/open with and without the agent via tracker reports; fall back to retrospective sampling |
| Acceptance rate at the review gate | Records published as-is vs. returned for adjustment during human review |
| Team-perceived quality | Structured retrospective feedback on scoring accuracy, rationale clarity, duplicate precision |
| Duplicate false-positive rate | Track separately — over-flagging erodes reviewer trust fastest. Read adoption and acceptance together: high adoption + low acceptance points at prompt/rulebook problems; high acceptance + low adoption points at process friction |
