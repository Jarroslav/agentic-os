# Assess product risk

Turn a product description plus your documented test scope into a scored, deduplicated risk register with coverage gaps and ranked test focus areas, so effort lands where failure hurts most.

## When to use this

- **Reach for it when** sprint or release planning needs the test strategy re-aligned to real product risk; you suspect test effort is misallocated or critical areas have zero coverage; you are about to design new suites and want uncovered critical risks to drive them; a readable test-scope artifact (strategy doc, suite list, coverage map) exists to compare against.
- **Skip it when** there is no substantive product description or module map (output collapses into generic risks); the current test scope lives only in heads, not artifacts; the team rejects both a shared probability/impact scale and the default three-level matrix; you just need a one-off brainstorm — paste product context into a single chat prompt instead and skip the connector setup entirely.
- **Outcome** — a published register (wiki page or ticket comment) of 8–15 scored risks, each with coverage status and a specific gap note, plus an ordered list of test focus areas, linked back to the source requirements in both directions.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Read access to epics, feature descriptions, acceptance criteria, module list | Risks must attach to real modules and flows; thin requirements yield vague risks | Issue tracker via authenticated connector (token issued, MCP/CLI installed) |
| Documented test scope: plan, suite list, coverage map, or strategy doc | Gap analysis compares each risk to actual tests; tribal knowledge is unreadable to the pipeline | Team wiki or test management system |
| Agreed risk taxonomy: shared probability/impact levels, or acceptance of default High/Medium/Low | Everyone consuming the register must interpret scores the same way | Team agreement |
| Agentic coding assistant with read and write connectors authenticated and reachable | The pipeline pulls inputs and pushes output through these | Local agent setup |
| For the chat-only variant: a 2–5 paragraph product description (modules, personas, critical flows, integrations) plus testing types in use | Description richness directly bounds how product-specific the risks get | Pasted into the prompt |

## Agent design

Four roles in a strict pipeline: a reasoning planner decides *which* areas carry risk and why, a mid-tier generator does the mechanical expansion into register rows, a cheap rule-based validator gates completeness, and a cheap publisher performs the only external write.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Risk analysis planner | Reason over modules and features with a probability×impact matrix, lightweight failure-mode analysis, and six categories (functional, security, performance, integration, UX, data); emit one checklist line per risk: area, category, scenario type, linked module. Decides what matters — never wording or format | premium | Fetched requirements, AC, module/persona/flow context | Risk checklist run artifact | R1 |
| Risk register generator | Expand each checklist line into a full row: description, probability (H/M/L), impact (H/M/L), score (critical = both high; high = high/medium mix; medium = medium/medium; low otherwise), coverage status (covered / partial / uncovered) derived from the fetched test scope, gap note specific enough to seed a test-case title, recommended focus | standard | Planner checklist, requirements, test strategy / suite list / testing types | Expanded register run artifact | R1 |
| Coverage validator | Rule-based verdict: every major module has ≥1 risk; ≥1 risk each in security, performance, integration, data-integrity; every row has probability, impact, matrix-consistent score, coverage status, non-generic recommendation. Emits complete / partial / incomplete with named gaps; anything short of complete blocks publication and routes back to the generator | economy | Generated register + requirements-derived module list | Validation verdict run artifact | R1 |
| Report publisher | Push validated register to the wiki (primary) or as a structured comment on the linked epic (secondary); map fields to page columns/labels/action items; create or idempotently update the page matched by source epic id; apply a machine-generated label; keep bidirectional traceability links | economy | Validated register | Wiki page or epic comment (external) | R3 |

> The split keeps judgment expensive and everything else cheap: the planner is the only role that decides which areas matter, so it alone runs on a premium model. Expansion, rule-checking, and publishing are deterministic enough for standard/economy tiers, and confining the R3 write to a single narrow role shrinks the audit surface.

## Flow

1. Lead triggers the pipeline manually at sprint or release planning. Preconditions: requirements finalized, test scope documented and readable.
2. Fetch inputs: epic/feature descriptions, acceptance criteria, and module list from the tracker; test strategy, suite list, and active testing types from the wiki or test management system.
3. Planner reasons across product areas (probability×impact, failure-mode analysis, six categories) and emits the risk checklist: area / category / scenario type / linked module.
4. Generator expands every checklist line into a full register row, cross-referencing the actually fetched test scope to set coverage status and write specific gap notes.
5. Validator checks module coverage, category minimums, and field completeness. Partial or incomplete blocks publication and loops the register back to the generator with the named gaps — no human touches the loop.
6. Publisher writes the register to the wiki page (deduped by source epic id) or as a structured epic comment, applies the machine-generated label, and wires traceability links both ways.
7. **Human review gate** — deliberately placed *after* the R3 write, not before it: the lead reviews the published register directly. There is no pre-publish approval step; entries the lead consistently revises or deletes feed back into planner prompt tuning.

> Placing the gate post-publication is an intentional deviation from the usual pre-R3 pattern: the write is one idempotent, labeled, easily-reverted page, and the validator's block-and-loop already stops malformed output. If the write target were broader, move the gate before step 6.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Fetch requirements: epic/feature titles, descriptions, AC, priority, module | Issue tracker (e.g. Jira, Azure DevOps) | Read | Official MCP server or vendor CLI with a read-scoped service account |
| Fetch test artifacts: strategy doc, suite list, active testing types | Team wiki or test management system (e.g. Confluence / a TMS) | Read | Official MCP server or CLI; read access is enough |
| Publish register and link it back to source requirements | Wiki page (primary) or tracker epic comment (secondary) | Write | Official MCP server or CLI with create/update on the target space and project; one auth setup serves both targets; confirm space layout and ticket schema before deploying; dedupe on source epic id |

> Wiring preference, in order: official MCP server → official CLI → REST/SDK wrapped in a custom skill → fully custom, only when nothing official exists or is permitted.

## Guardrails

- **Injection defense** — fetched ticket and wiki content is input data, never instructions. Scope the trigger to the manual invocation only — never to tracker update/comment events — so the pipeline's own published comment can never re-fire a run.
- **Writable-field allowlist** — the R3 write touches exactly: one wiki page (new, or idempotent update keyed on source epic id), one structured tracker comment, and one machine-generated label. Source requirements, tickets, and existing test assets are never modified.
- **Human gate** — no pre-publish approval; the validator's block-and-loop is the only automatic stop. The lead checks the published register for module fit, score plausibility, and gap-note specificity. Heavy post-publication editing is a signal to tune the planner, not to add a gate.
- **Grounding** — derive coverage status from the retrieved test scope; confirm a scenario type is genuinely absent before marking it uncovered. Every risk links to a named module, and the register carries bidirectional links to source requirements. Generic risks without module context mean the product description is too thin — enrich the input, don't build on it. A partial validation verdict usually points at thin requirements for specific modules; feed richer requirements or an explicit module list.

## Automation

This blueprint is already a manual-trigger, fully-automated pipeline: one invocation (slash command or chat prompt) at sprint/release planning → fetch → plan → expand → validate (loop on gaps) → publish with label and traceability link. To run it unattended, pin the identical steps into a fixed workflow — model, prompt, and toolset frozen per step, no runtime tool selection or task decomposition — because without a human in the loop, predictability beats flexibility. Keep the post-publication human review even in unattended mode until acceptance metrics show registers ship unedited; and in every mode, verify the trigger cannot fire on the pipeline's own published comment.

Trigger → flow: `lead invokes at planning` → `fetch requirements + test artifacts` → `planner checklist` → `generator register` → `validator gate (loop)` → `publisher writes wiki/tracker`.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption rate | Machine-labeled registers vs all risk assessments: filter test-plan-space wiki pages by the generated label (or count tagged tracker comments); compare against the manual-per-quarter baseline |
| Productivity gain | (manual hours − assisted hours) / manual hours; baseline from retrospective estimates of pre-adoption effort, assisted figure from time-tracked runs |
| Acceptance rate | How often the published register is used unchanged vs revised; consistently edited or deleted entries become prompt-tuning candidates |
| Team feedback | Retrospective questions: did the risks match what humans would have caught, and did the gap analysis surface anything previously missed |
| Adoption × acceptance diagnostic | High adoption, low acceptance → planner lacks product context (add module names, integration descriptions). High acceptance, low adoption → invocation friction (simplify the trigger, shrink required inputs) |

> Non-goals: this does not author test cases (it ranks focus areas), does not execute tests or compute instrumented coverage (status comes from documented scope), never modifies source requirements or existing test assets, and does not replace the lead's judgment — the team still owns the test strategy.
