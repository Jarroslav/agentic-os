# Generate negative and boundary coverage

Turn a story's acceptance criteria and explicit input constraints into validated, traceable negative and boundary test cases published to your test management system — so edge-condition gaps stop leaking defects.

## When to use this

- **Reach for it when** a story is input-heavy — explicit numeric or date ranges, required fields, typed inputs — and you want extra confidence at the edges; when you're testing an unfamiliar system where negative and boundary scenarios are the ones most likely to be missed; when your team keeps generated cases in a test tool and needs requirement traceability plus an AI-origin label on each case; or for a no-connector dry run — paste one story (optionally one field with its valid range) into any assistant and inspect the checklist before wiring anything up.
- **Skip it when** the criteria are vague behavioral prose with no concrete ranges or constraints — planning cannot derive boundaries from nothing; send the story back to its author first. Skip it for happy-path or general functional coverage, and do not apply it blanket across the backlog: this is a targeted, low-frequency technique for stories that warrant extra edge confidence.
- **Outcome** — every acceptance criterion is covered by at least one boundary case and one negative case; drafts pass automated coverage validation and a human review before being upserted into the test tool with a bidirectional link to the source story.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Criteria with explicit fields, ranges, types, constraints | Boundaries are derived mechanically from stated ranges; without them output degrades to generic negatives | Story/requirement record in the tracker, or pasted text |
| Read access to the requirements source | Step 1 pulls story id, title, criteria, field definitions, priority | Tracker/work-item/wiki API token or MCP connector with project read; manual paste is a valid fallback |
| Write access to the test management system | Final step creates/updates cases in the target suite with labels and links | Test tool API token or MCP connector with create/update on the suite |
| Assistant with a premium reasoning tier available | Boundary identification quality at planning propagates into every downstream case | Any authenticated agentic coding/chat assistant |

## Agent design

Split the pipeline into one reasoning role and four mechanical ones. Boundary identification — spotting every field, partitioning valid/invalid classes, deriving edge values — is the step where model quality decides the run; everything after it is deterministic expansion, rule-checking, and API plumbing.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Retriever | Fetch story id, title, criteria, field definitions, priority (or accept pasted text) | economy | Tracker/wiki record | Normalized story payload | R0 |
| Planner (orchestrator) | Identify fields/parameters/conditions; equivalence partitioning; boundary value analysis (lower, upper, just-below, just-above); classify negatives (null, empty, out-of-range, wrong type, missing required); emit checklist rows (scenario id, type, field, condition/value, linked criterion) — design intent only; dispatch subagents | premium | Normalized payload | Scenario coverage checklist | R1 |
| Generator | Expand each row one-to-one into a full case (title, preconditions, steps, expected result, type, linked criterion); one action per step, one scenario per case; expected results cite the concrete value, never a placeholder; flag vague criteria in the title instead of inventing values; regenerate on pushback | economy | Checklist + per-project domain context | Draft test cases | R1 |
| Validator | Enforce per-criterion rule (≥1 boundary + ≥1 negative); check quality rules (concrete value, unambiguous steps, measurable expectation, type label matches checklist); grade covered/partial/missing; block and route gaps back to the generator | economy | Drafts + checklist | Validation report | R1 |
| Publisher | After approval, upsert cases keyed by story id + scenario id; remap fields to the target tool's schema; set bidirectional story link; apply AI-origin label and mirror a tag/comment on the story | economy | Approved cases | Test tool records; story tag/comment | R3 |

> The split puts the only judgment-heavy step — deciding what the boundaries *are* — on the premium tier, and keeps expansion, rule enforcement, and publishing on economy where a cheap model performs identically. Paying premium rates for mechanical steps buys nothing; skimping on planning corrupts every downstream case.

## Flow

1. Tester selects a story and invokes the pipeline (manual trigger; precondition: criteria contain explicit fields/ranges/constraints).
2. Retriever pulls full story details from the source system, or accepts pasted input.
3. Planner runs equivalence partitioning and boundary value analysis on the premium tier and emits the scenario coverage checklist.
4. Generator expands every checklist row into one fully specified test case on the economy tier.
5. Validator grades coverage per criterion (covered / partial / missing) plus quality rules; any gap loops back to step 4. Partial coverage never publishes.
6. **Human review gate** — the tester reviews validated drafts and approves, refines, or returns them. Required: business rules and known system quirks reveal gaps no agent can infer from criteria alone. Relax only after sustained confidence, never at the start.
7. Publisher upserts approved cases into the test tool with schema mapping, story+scenario dedupe key, bidirectional story link, and AI-origin label.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Fetch requirements (id, title, criteria, field definitions, priority) | Issue trackers, work-item systems, wikis | Read | Official MCP connector; service account needs project read. Manual paste covers a dry run |
| Publish cases with traceability links and AI-origin label | Test management platforms (some have MCP/CLI coverage, others REST only) | Write | Official MCP where it exists; service account needs create/update on the suite. Field names differ per tool (title/summary, step-result pairs, script arrays) — remap the draft schema before deployment; scenario type maps to a label or custom field |

> Wiring preference, in order: official MCP connector → official CLI → REST/SDK wrapped in a skill → fully custom. Build custom only when nothing official exists or is permitted.

## Guardrails

- **Injection defense**: fetched story text is design input, not instructions. The writable surface is confined to the test tool plus one mirror tag on the story. If you ever move to event triggers, scope the trigger strictly to the initiating event type — the pipeline's own write-back (the story comment/tag) must never re-trigger it. This is a real infinite-loop hazard, not a hypothetical.
- **Writable-field allowlist** (the R3 publish): test-case name, steps, expected result, scenario-type label/custom field, requirement link, AI-origin label, and one tag/comment on the linked story. Upserts key on story id + scenario id to prevent duplicates. Nothing else in the tracker or repo is written.
- **Human gate**: the tester checks that scenarios match their domain knowledge — business rules, known quirks, edge cases the criteria omit — and approves, refines, or returns drafts. Start in semi-automated mode (approval before every publish); consider relaxing only after quality has been consistently high.
- **Grounding**: every scenario links to a specific acceptance criterion — nothing from thin air. When a criterion is vague ("a valid amount"), the generator flags the ambiguity rather than fabricating a boundary; invented boundaries create false confidence. A `missing` validator grade means the criteria are too vague to plan from — escalate to the story author instead of regenerating.

## Automation

Run human-invoked and semi-automated until output quality is consistently high; only then pin into a fixed workflow. The pinned variant runs the same steps as a predefined sequence — model, prompt, and toolset fixed per step, no runtime decomposition, no on-the-fly tool selection — because predictability beats flexibility when nobody is watching.

Trigger: tester selects a story and invokes the run → fetch story + criteria → planner builds coverage checklist (premium) → generator expands drafts (economy) → validator grades and loops gaps back until confirmed → tester approves → publish with traceability and AI-origin label.

Keep the human gate even in the pinned variant until adoption metrics justify removing it, and guard the trigger against re-firing on the pipeline's own write-back events.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption rate — AI-produced boundary/negative cases vs total in the suite | Export from the test tool filtered on the AI-origin label vs manually created cases; AI count over total, as a percentage |
| Productivity gain — time per case, AI-assisted vs manual baseline | Retrospective sampling: estimated hours per test-design session collected at sprint retros; (manual − AI) / manual |
| Acceptance rate — drafts published as-is vs returned for rework | Track the return rate at the review gate; a high return rate on boundary cases specifically points at vague criteria upstream |
| Classification fit and missed edge cases | Structured retro questions: did the planner's scenario classification match the tester's mental model, and were known edge cases absent |
| Combined diagnostic for evolving the pipeline | High adoption + low acceptance → planner lacks domain context (add field definitions, business rules). High acceptance + low adoption → invocation friction (add a shortcut trigger or a story template that pre-formats criteria) |
