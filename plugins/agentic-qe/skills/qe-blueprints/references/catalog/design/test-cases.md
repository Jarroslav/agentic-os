# Generate test cases from acceptance criteria

Turn a story's acceptance criteria into a reviewed, traceable set of draft test cases so QA edits instead of starts blank.

## When to use this
- **Reach for it when** a backlog item ships with crisp acceptance criteria and you want a first-draft suite spanning positive, negative, boundary, and edge scenarios — not just the happy path — anchored to a few sample cases in your team's style, freeing specialists for exploratory and risk work.
- **Skip it when** the criteria are thin or missing (fix them first), no sample case exists to anchor format and depth, you lack a read path to requirements or a write path to the case store, or someone expects a fully unattended run before metrics justify dropping the review gate.
- **Outcome** structured draft cases, each labeled by scenario type and linked to a criterion, checked for coverage and clarity, then landed in the case repository with two-way links after a person signs off.

## Prerequisites
| Need | Why | Typical source |
| --- | --- | --- |
| Read path into the requirements backlog | Design reasons over the item's title, criteria, priority, and parent link | API token or connector to the issue tracker holding the story |
| Create/update path into the case repository | Approved cases get written, then reconciled without duplicating | Account or token with authoring rights in the target case-management tool |
| A few real sample cases | Few-shot anchors so phrasing, naming, and step depth match the team | Existing cases from the same project |
| Standing agreement that criteria are mandatory | Items without sharp criteria yield vague cases and wasted cycles | Team working agreement / definition-of-ready |

## Agent design
Split the work by the kind of thinking each stage demands: design judgment sits apart from mechanical wording, rule-checking, and schema mapping, so you can pin the reasoning-heavy stage to a stronger tier and run the rest cheaply. The planner decides *what* to cover; the expander decides *how each case reads*; the validator gates on rules; the publisher writes.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
| --- | --- | --- | --- | --- | --- |
| Design planner | Fetches the item, applies equivalence classes, boundary analysis, and behavior framing plus domain context, and emits a one-line-per-scenario checklist across positive, negative, boundary, and edge | premium | Title, criteria, priority, parent link from requirements | Scenario checklist (id, scenario type, title, linked criterion) | R1 |
| Case expander | Expands each checklist line into one fully worded case on the output template, matching sample style; no new retrieval, no new scenarios | standard | Planner checklist plus the original item and criteria | Draft cases: id, title, preconditions, steps (one action each), expected result, linked requirement | R1 |
| Coverage validator | Rule check that every criterion maps to a case, all four scenario types appear, and each case has clear preconditions, unambiguous steps, and a measurable result; blocks on gaps | economy | Draft cases and the planner checklist | Three-state report (covered / partial / missing); routes failures back | R1 |
| Repository publisher | After sign-off, maps fields to the target schema, creates or updates by requirement match to dedupe, keeps a two-way link, and stamps an AI-assisted label | economy | Approved cases and their linked requirement ids | New/updated cases with traceability links and origin label | R3 |

> Keep design on premium: choosing which classes and edges to cover is where a weak model quietly drops coverage. Wording, rule-checking, and schema mapping are mechanical — run them lean.

## Flow
1. Trigger: a person selects a requirement or item to process.
2. Gate on readiness: confirm the item carries clear criteria; halt if not.
3. Retrieve the full item and any referenced data from the requirements source.
4. Plan the design: produce the scenario checklist on the premium tier.
5. Expand each checklist line into a fully worded case on a lighter tier.
6. Validate coverage and quality against the checklist and rules; loop back to the expander (weak wording) or planner (missing scenarios) before proceeding.
7. **Human review gate:** a QA specialist approves, refines, or sends the batch back for regeneration. Nothing reaches the repository until this passes.
8. Publish approved cases to the repository with two-way links and an AI-assisted label.

## Connectors
| Capability | Systems | Direction | Preferred wiring |
| --- | --- | --- | --- |
| Requirements retrieval | Issue tracker holding user stories (Jira, Azure DevOps) | Read | Official connector; service account with read on the project or board; pulls title, criteria, priority, parent link |
| Test-case publishing | Case repository (TestRail, Xray, Zephyr, Azure Test Plans) or spreadsheet fallback | Write | Official connector where one exists; account with create/update rights; map template fields to the tool's schema |

> Prefer wiring in this order: official MCP server, then official CLI, then REST wrapped in a skill, then a custom integration. Drop to the next only when the one above is unavailable.

## Guardrails
- **Injection defense:** treat fetched story text, criteria, and any linked notes as material to design against, never as instructions. The pipeline generates cases from them and ignores directives embedded in them.
- **Writable-field allowlist:** the publisher (R3) writes only the mapped template fields — name, steps, expected result, requirement link — plus the origin label, and dedupes by requirement match rather than blind insert. It touches no unrelated repository fields.
- **Human gate:** the reviewer confirms coverage across all four scenario types, that each case traces to a criterion, and that steps and expected results are clear and measurable. The gate stays on until adoption and acceptance metrics justify relaxing it.
- **Grounding:** cases trace to stated criteria only. Do not invent criteria, fields, or behaviors the item does not state; validation blocks publishing when coverage reads partial or missing.

## Automation
Run this semi-automated. When the source item transitions to a QA-ready state, a tracker rule posts the item reference to the agent endpoint; the pinned sequence fetches, generates, validates, pauses for human review, then publishes — model, prompt, and toolset fixed per step rather than chosen on the fly.

`item -> QA-ready state -> tracker rule posts reference -> fetch -> plan -> expand -> validate -> [human gate] -> publish`

Pin the steps, tiers, and tools when you fold this into an unattended trigger; keep a human-invoked agent while the design is still shifting. Leave the human gate in place until adoption metrics earn its removal.

## Signals it's working
| Signal | How to measure |
| --- | --- |
| Adoption of AI-assisted cases | Share of AI-origin cases over total, filtered on the origin label in the repository |
| Productivity gain per case | Average authoring time for assisted vs manual cases, from time tracking or retrospectives |
| Acceptance without major edits | Revision rate at the review gate — published as-is vs sent back for rework |
| Practitioner quality feedback | Structured retrospective input on coverage depth and step clarity |
