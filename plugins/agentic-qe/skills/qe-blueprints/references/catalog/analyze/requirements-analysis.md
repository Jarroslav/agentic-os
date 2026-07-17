# Analyze requirements for testability

Screen requirements and epics before sprint planning: emit a severity-coded findings report plus concrete rewrite proposals back to the tracker, so gaps surface pre-development instead of mid-sprint.

## When to use this

- **Reach for it when** requirements repeatedly arrive incomplete, self-contradictory, or vague — and defects trace back to them; when manual review is slow, subjective, or unevenly applied; when you want a structured pre-sprint gate covering completeness, consistency, ambiguity, testability, and cross-item conflicts (contradictory non-functional constraints, circular dependencies, orphaned items).
- **Skip it when** no written definition of requirement quality exists in your org — write that first, or the validation stage has nothing to enforce and output collapses to generic noise; when a single-agent pilot on one real pasted requirement produced only generic feedback instead of findings quoting specific wording — fix the criteria before scaling to multiple agents; when the agent cannot get comment/field write access to the tracker — the loop depends on publishing back.
- **Outcome** — every analyzed item carries a structured comment with critical/warning/info findings grouped by issue category and requirement type, plus proposed rewrites and stakeholder questions; items breaching hard thresholds get flagged not-ready-for-development.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Read access to requirements | Pipeline fetches full item detail and every linked artifact (parent epics, dependent stories, related NFRs) — the link graph powers conflict detection | API token or MCP connector for the tracker/wiki; service account with read scope across all linked projects, not just the target board |
| Write access to requirements | Findings land as comments, field updates, labels, and follow-up items on the ticket itself | Same-system account with comment, field-update, and linking permissions |
| Org quality-criteria document | The rule-enforcement stage checks against it; without it, output is generic noise at real cost | Internal wiki page defining completeness rules, naming conventions, AC templates, NFR categories |
| Requirement-type taxonomy | Analysis rules, validation, and report grouping are keyed to type (functional, non-functional, business, stakeholder) | Team classification plus its label/tag scheme in the tracker |
| Cheap single-agent pilot | One prompt against one pasted real requirement proves the model surfaces project-specific issues; naming the five analysis dimensions explicitly in the prompt is the critical design constraint | Any capable chat model; no connectors needed |

## Agent design

Five roles in a fetch → judge → check → package → write-back pipeline. The judgment-heavy stage (multi-dimensional analysis over an item plus its full dependency graph) sits on a premium model; rule application and proposal drafting run on standard; assembly and tracker writes are mechanical and run on economy.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Analyzer | Entry point. Reviews each item on five dimensions: completeness (missing fields, vague AC, absent edge cases), internal consistency, ambiguity (subjective adjectives, unclear pronouns, weak verbs), testability (measurable or not), cross-item conflicts (incompatible constraints, circular dependencies, orphans) | premium | Full item detail plus all linked parents, dependents, related NFRs | Per-item structured report: id, type, issue category, severity, finding, downstream impact, implicated links | R1 |
| Validator | Checks Analyzer output against the org criteria document and industry references (INVEST for stories, IEEE 29148 for specs, ISO/IEC 25010 for NFR categories); applies per-type rules — functional items need a clear actor and measurable criteria, NFRs need numeric thresholds and a category, business items a measurable outcome, stakeholder items a named persona. Verdicts: passed / warning / failed; failed blocks development | standard | Analyzer report, org criteria doc, per-type rule sets | Per-item verdict artifact with threshold-failure flags | R1 |
| Reporter | Assembles the consolidated document: summary stats (items analyzed, pass rate, critical count), sections per requirement type, grouping by severity and category, dependency/traceability map, proposal list | economy | Analyzer + Validator output, proposals | Consolidated report (document or comment-ready fragments) | R1 |
| Enhancer | Drafts a concrete fix per flagged issue: rewritten AC, missing NFR categories, clarifying questions, conflict-resolution options (split the item, add conditions, escalate to the product owner). Proposals only — never applies changes | standard | Findings, original item, linked dependencies, validation criteria | Proposal artifact: issue ref, suggested change, rationale, questions, fix priority | R1 |
| Publisher | Writes approved output to the tracker: structured comments, quality-score/status fields, filter labels, follow-up tasks, traceability links. Logs every suggestion and its human disposition; snapshots the original item before any direct edit | economy | Reviewed report and proposals | Comments, fields, labels, follow-ups, links in the external tracker | R3 |

> The Analyzer is deliberately the expensive stage: deep reasoning over an item and its whole link graph is what pre-empts rework, and rework costs more than premium tokens. Everything downstream of it is expansion and transcription — pushing those onto standard/economy tiers keeps per-item cost flat as batch size grows.

## Flow

1. **Trigger** — a responsible engineer selects a requirement, epic, or batch. Precondition: items are typed/classified in the tracker.
2. **Retrieve** — fetch full item detail plus the complete link graph: parents, dependent stories, related non-functional items.
3. **Analyze** — premium agent scores each item on the five dimensions and emits the structured per-item report.
4. **Validate** — rule agent issues pass/warning/fail against the org criteria and industry references. Hard-threshold failures (no acceptance criteria at all, contradictory constraints) short-circuit straight to a human, marked not-ready-for-development.
5. **Report** — consolidate into a severity-coded document grouped by type and category, with stats and a traceability map.
6. **Enhance** — draft rewrites, missing categories, stakeholder questions, and conflict resolutions for every flagged issue. Proposals only.
7. **Human review gate** — the responsible engineer edits the draft inline: sharpens wording, deletes false positives, tags follow-ups. In steady state this is review-and-polish, not hard approval; full pre-publication approval applies only during initial rollout, and hard-threshold failures always stop for a human.
8. **Publish** — write the approved output back as comments, field updates, labels, follow-up tasks, and links, with an audit log of accepted/modified/rejected suggestions and pre-edit backups for rollback.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Fetch item details | Issue tracker / boards / wiki (e.g., Jira, Azure DevOps) | Read | Official MCP connector; pulls title, description, AC, type, priority, links |
| Walk traceability graph | Same tracker | Read | Same connector via the platform query language, traversing business → stakeholder → functional → non-functional; needs read scope over every linked project — this is what enables conflict detection |
| Publish results | Same tracker | Write | Same connector with comment + field-update permission; posts comments, sets score fields, applies labels, creates links and follow-ups |
| Fetch quality criteria | Internal knowledge base / wiki | Read | Wiki MCP or CLI where available; otherwise wrap the REST API in a custom skill |

> Wiring preference in order: official MCP server → official CLI → REST API wrapped in a skill → fully custom integration.

## Guardrails

- **Injection defense** — fetched ticket and wiki text is analysis input, never instructions. Structural mitigations: in unattended mode the workflow is pinned (fixed step order, pinned models/prompts/tools, no dynamic tool selection), and the write surface is narrow, labeled, and human-reviewed. Still treat all retrieved content as untrusted data.
- **Writable-field allowlist** (Publisher, R3) — default surface: structured comments plus an analyzed-by-AI label, quality-score/analysis-status custom fields, warning/critical filter labels, follow-up tasks, traceability links. Direct edits to descriptions or acceptance criteria are opt-in per project, require a pre-edit backup, and may need an extra approval workflow in regulated domains. Every suggestion and its disposition (accepted/modified/rejected) is logged.
- **Human gate** — the reviewer removes false positives, tightens wording, and tags follow-ups on the draft comment before or shortly after it lands. Heavy pre-publication approval only during rollout — permanently gating every run negates event-driven automation. Critical-threshold failures always block for a human.
- **Grounding** — findings must quote the specific words or clauses they criticize; never fabricate acceptance criteria, stakeholders, or behaviors absent from the source item; if an item is too thin to score on a dimension, say so rather than guess. A one-line ticket correctly yields mostly critical completeness findings — do not pad the input to make it look analyzable.

## Automation

Run human-invoked while tuning criteria; pin into a semi-automated event-driven workflow once the false-positive rate is acceptable. Triggers: status transition to ready-for-review, an edit to description or AC, or a weekly sweep of in-progress epics.

Trigger → flow: tracker automation rule fires an HTTP POST with the item key → pinned workflow runs fetch → analyze → validate → report → enhance → publishes a draft comment carrying the analyzed-by-AI label → the responsible engineer polishes inline. Models, prompts, and tools are pinned per step with no dynamic selection — predictability over flexibility when nobody is watching. Keep the inline human gate; drop to spot-checking only when acceptance-without-edit metrics justify it.

## Signals it's working

| Signal | How to measure |
|---|---|
| Coverage | Items with the analyzed-by-AI label vs all items in the sprint/epic; compare against structured manual reviews |
| Review-time reduction | Average minutes from ready-for-review to first reviewer response, AI-screened vs manual, from tracker history |
| Early catch rate | Reviewer-accepted AI findings as a share of all pre-development findings; count accepted warning/critical comments |
| Acceptance-without-edit rate | Draft-comment dispositions: accepted as-is vs heavily edited vs deleted as false positive |
| Fewer clarification cycles | Needs-clarification / back-to-owner transitions per sprint vs pre-adoption baseline |
| Perceived signal vs noise | Retrospective feedback on whether flagged issues were real |
| Tuning heuristic | High adoption + low acceptance = noisy analyzer → tighten rules or improve the criteria doc. High acceptance + low adoption = trigger/wiring friction, not output quality |
