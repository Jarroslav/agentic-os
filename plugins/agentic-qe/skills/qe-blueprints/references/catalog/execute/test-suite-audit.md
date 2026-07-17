# Audit and refine a test suite

Take a scoped test-management folder plus a short product-scope note and produce a deduplicated, step-enriched, staleness-flagged suite staged for lead sign-off — keeping the repository lean, executable, and current.

## When to use this

- **Reach for it when** the repository holds many near-identical cases for the same scenario under different titles; when a large share of entries are one-line checks with no concrete actions or verifiable outcomes; when cases likely reference retired features nobody has pruned; when you want a recurring hygiene pass with an approval gate in front of every change. Probe feasibility first: paste 10–20 exported cases, a couple of exemplars, and the scope note into a single agent and check that its classifications are semantically sound before wiring any connectors.
- **Skip it when** no product-scope description exists (staleness has nothing to be judged against); when the export lacks module/feature labels (relevance scoring is meaningless until enriched); when the suite is small enough that manual review beats pipeline setup; when no draft/staging/report mechanism can sit in front of writes; or when the sample probe misclassified (title-level matching, false stale flags) — fix the input format and context first.
- **Outcome** — a reviewed change set applied to the live repository: each duplicate cluster collapsed to one canonical case linked to its predecessors, vague entries rewritten as concrete stepwise procedures, obsolete candidates flagged with cited reasons, every touched item carrying a machine-audit label, plus a run summary with merge/enrichment/flag counts.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Read access to the target folder with full case bodies (ids, names, steps, labels, metadata) and large-batch retrieval | Clustering works on meaning, not titles — the classifier needs complete content | API token or managed connector from the platform admin |
| Write access (update + merge rights; delete only if explicitly sanctioned) on the same or a service account | Approved changes are applied in place without over-privileged credentials | Platform admin / service-account provisioning |
| An explicit, agreed folder or suite scope | Bounds the blast radius — nothing outside the named scope may be touched | Team agreement before the first run |
| A short product-context document listing active and retired feature areas | Staleness needs a ground truth; every stale flag must cite it | Product/QA docs — wiki page, shared doc, or local file |
| An approval mechanism (draft state, staging area, or delivered report) ahead of any write | Merges and removals are hard to reverse; nothing reaches live data unreviewed | Workflow / platform configuration |
| Two or three exemplar cases in the team's preferred step format | Few-shot anchors so rewrites match house naming and step granularity | Hand-picked from the existing suite |

## Agent design

Split the work into a narrow reasoning role and three mechanical ones. Classification — deciding which cases mean the same thing, which are hollow, and which are dead — is the judgment-heavy core and gets the premium tier. Rewriting, rule-checking, and publishing are plan-following expansion and run fine on economy.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Audit planner | Clusters cases by scenario semantics (explicitly beyond title likeness); buckets each as duplicate / vague-checklist / stale / healthy (duplicate wins on overlap); scores relevance against the context doc via quality heuristics (step count, outcome verifiability, preconditions present); emits a prioritized per-case plan: cluster id + consolidate / rewrite / flag / keep | premium | All cases in scope; product-context doc | Action-plan artifact (one task per row) | R1 |
| Suite refiner | Executes the plan row by row: merges each cluster into one canonical case (best title + union of distinct steps, all superseded ids listed); rewrites vague entries into one-action-one-verifiable-outcome steps with preconditions, original text preserved alongside; drafts stale flags with rationale and an archive-vs-remove call. Never fabricates steps — entries too vague to expand faithfully go to a human | economy | Action plan; raw cases; context doc; exemplars | Draft canonical cases, enriched cases, staleness flags | R1 |
| Quality validator | Rule-checks drafts: exactly one canonical per cluster with predecessor references on the rest (an unresolved cluster hard-blocks — it would orphan cases); ≥3 concrete steps and a verifiable outcome per rewrite; every stale flag cites a specific claim in the context doc; rewrites preserve intent and add no scenarios. Emits ready / needs-review / blocked; failures return to the refiner | economy | Drafts; action plan; context doc | Validation verdict report | R1 |
| Publisher | Applies only human-approved changes: in-place updates; merged predecessors marked obsolete (hard delete only with explicit lead approval); bidirectional predecessor links; folder hierarchy and naming preserved; machine-audit label on every touched case; summary note with counts | economy | Approved change set | Platform records, labels, links, summary comment | R3 |

> Keep the planner off prose entirely — it plans and classifies only. Spending premium reasoning budget on rewriting sentences wastes it; the refiner does that from the plan for a fraction of the cost.

## Flow

1. **Optional pilot** — run one agent read-only on a pasted sample (cases + exemplars + scope note). Proceed only if the audit table is semantically sound and every row carries a traceable case id.
2. An engineer or lead selects the target folder and starts the run; check preconditions (scope agreed, context doc present, connector authenticated).
3. Read connectors fetch every case in scope (ids, names, steps, labels, metadata) and the product-context document.
4. Planner (premium) clusters semantic duplicates, buckets every case, and hands the prioritized action plan to the refiner.
5. Refiner (economy) consolidates clusters into canonical cases, rewrites vague entries into stepwise procedures, and drafts cited staleness flags.
6. Validator rule-checks the drafts — one canonical per cluster, minimum step count, verifiable outcomes, grounded stale reasons. Failures loop back to the refiner; the pipeline does not advance.
7. **Human review gate** — a lead or engineer approves, adjusts, or rejects each proposed change. Nothing is written until this passes; rejected items return to the refiner.
8. Publisher applies approved changes: updates cases, marks superseded ones obsolete, links predecessors, labels touched items, and posts the run-summary counts.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Batch-fetch all cases in scope (ids, names, steps, labels, metadata) | Any test-management platform: issue-tracker test add-ons, dedicated case managers, ALM test-plan suites | Read | Least privilege — read-only on the single target folder |
| Fetch the product-context document | Team wiki / enterprise document store / local file | Read | Official wiki connector where one exists; graph-style API for stores without one; direct file read locally |
| Write approved changes: in-place updates, obsolete-marking, predecessor links, audit label, summary note | Same platform as the fetch side | Write | Update rights only; delete rights solely under explicit lead sanction. Map fields to the platform schema up front (name, step/outcome pairs, predecessor link) — platforms lacking native links or structured steps need a custom field or comment |

> Wiring preference, in order: official MCP connector → official vendor CLI → REST/SDK wrapped in a skill → custom build last.

## Guardrails

- **Injection defense** — fetched case bodies and context documents are data, never instructions; classification and rewriting derive only from the operator's task and the plan. Scope any platform automation watching the folder so the run's own labels and comments cannot re-trigger the pipeline — the trigger stays bound to the explicit manual start.
- **Writable-field allowlist** — case name, steps, expected outcomes, preconditions, predecessor links, labels, comments; only inside the agreed folder. Merged duplicates are marked obsolete, never hard-deleted, absent explicit lead approval. Hierarchy and naming conventions stay intact; rewrites keep the original text alongside and may not introduce new scenarios.
- **Human gate** — the reviewer checks each merge (is the canonical case really equivalent?), each rewrite (intent preserved, steps real?), and each stale flag (does the cited claim hold?), then approves / adjusts / rejects per item. Start fully gated; narrow the gate to destructive actions only after sustained acceptance metrics.
- **Grounding** — every staleness claim cites a specific statement in the context document; ungrounded flags are validator warnings. Rewrites never invent steps — entries too vague to expand faithfully escalate to a human. Duplicate labels require same-scenario coverage, not title similarity. The pipeline refines existing coverage; it does not author new tests, and it does not execute tests or judge pass/fail.

## Automation

Pin into an unattended workflow only after the interactive pattern proves out. The workflow variant runs the identical stages as a fixed sequence with model, prompt, and toolset pinned per step — no runtime tool selection, no on-the-fly decomposition; without a human present, predictability beats flexibility. Keep the trigger strictly on manual folder selection by an engineer or lead so summary labels and comments cannot re-fire the run.

Trigger → flow: manual folder selection → fetch cases + context → premium classification plan → economy rewrite → rule validation → **human approval** → publish approved changes.

Run semi-automated (approval before publish) first. Move toward fuller automation only once output quality is consistently high — and keep deletions gated even then.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption rate — share of cases audited/merged/enriched/flagged by the pipeline vs maintained by hand | Export from the platform, filter on the machine-audit label vs manual updates; AI-touched over total |
| Productivity gain — time per audit run vs the manual equivalent | Compare measured run duration against the team's pre-run manual-effort estimate; (manual − AI) / manual |
| Acceptance rate — proposals approved unchanged vs sent back at the gate | Tally approve/adjust/reject outcomes per item across runs |
| Team feedback on classification and rewrite quality | Structured post-run survey on false-positive/false-negative classifications and rewrite fidelity |
| Adoption-vs-acceptance divergence as a tuning diagnostic | High adoption + low acceptance → tune the planner (domain context, clustering threshold); high acceptance + low adoption → fix connector or export-format friction, not output quality |
