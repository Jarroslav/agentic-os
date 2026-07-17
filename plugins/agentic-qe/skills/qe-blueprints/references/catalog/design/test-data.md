# Generate test data

Turn a data schema plus format, volume, locale, and compliance constraints into a synthetic, schema-conforming dataset with systematic boundary and edge coverage — replacing slow, inconsistent hand-built fixtures.

## When to use this

- **Reach for it when** hand-crafting fixtures is slow and error-prone; real personal data is legally off-limits and synthetic stand-ins are mandatory; edge-case or negative API payloads require schema knowledge nobody wants to encode manually; load datasets are too big to assemble by hand; or you need seeds across many shapes (personal records, API payloads, DB seed rows, file uploads, edge-case sets, bulk sets) in JSON/CSV/HTML/SQL/XML/YAML.
- **Skip it when** the schema is ambiguous — no field constraints, nullability, or format rules. Tighten the schema first; no generator can define validity for you. Also skip the full pipeline for a one-off throwaway dataset (a single prompt to any assistant does it), and skip model-only generation when volume exceeds the project threshold with no deterministic bulk generator available — per-record cost and context limits break it.
- **Outcome** — on-demand synthetic datasets in the chosen format, every record labeled with the scenario partition it covers, personal fields recognizably fake, published with an AI-origin tag and a traceability link back to the originating work item.

> Not a masking/anonymization tool for production records, not a test-case designer, and not a test executor. It generates synthetic data for tests; nothing else.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Documented schema or spec for the data | Without a definition of validity the generator cannot emit conforming records; missing this is the top cause of useless first runs | Schema file, API contract fragment, DB table definition, or a precise inline field description |
| Compliance constraints in writing (or an explicit "none apply") | Decides which fields must be synthetic-only; prevents real-data leakage and pointless masking alike | Privacy/regulatory rules for the domain — which identity fields may never carry real values |
| Agreed output format and record volume | Selects inline model generation vs spec-driven bulk mode and the output template | Team decision per request |
| Create/update credentials on the destination (auto-publish only) | Needed only for the automated publish path; download-only use needs nothing | Service account or token for the git host, tracker, wiki, or test-management tool |
| Optional: deterministic data library wrapped as a skill | Above the volume threshold (~500 records, tunable) model-only output hits context limits and linear cost; hybrid mode has the model design once, a script emit many | Existing fake-data library or in-house generator — check the internal skill marketplace before building |

## Agent design

Split the work so judgment (decomposition, rerouting on rejection) sits apart from mechanical emission and publishing: an orchestrator dispatches a generator, an optional validator scores drafts against quality rules, and a narrow publisher performs the only writes to shared systems.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Orchestrator | Decomposes the request, dispatches sub-roles, reroutes to generation when validation or review rejects a draft; free decomposition when human-invoked, pinned sequence when event-triggered | standard | Request or triggering ticket; run flags (format, volume, locale, compliance, validation mode, approval mode) | Dispatch instructions, run state | R1 |
| Schema retriever (optional) | Fetches the schema when not supplied inline | economy | API-spec catalogs, docs wiki, schema repos | Fetched schema into run context only | R0 |
| Generator | Emits the dataset via equivalence partitioning, boundary value analysis (min/max ± one), and edge injection (nulls, empties, special characters, multilingual text, locale formats); tags each record with its partition; in bulk mode emits a generation spec (field rules, distributions, ratios, relational constraints) instead of records | standard | Schema, compliance flags, format/volume/locale params, few-shot samples of team conventions | Draft dataset or generation spec (run artifact) | R1 |
| Validator (optional) | Scores drafts: required fields typed correctly, no real personal data, formats met, count matched, no duplicates, locale consistency, business rules; emits covered/partial/missing; on failure blocks and routes back with the report; bulk runs validate spec + statistical sample, not every record | standard | Draft (or spec + sample), schema, quality checklist | Validation report (run artifact) | R1 |
| Publisher | Maps approved data to the destination (download, repo fixture dir, ticket/test-case attachment, docs page); applies AI-origin label, machine-generated header note, bidirectional traceability link, and the agreed create-vs-update policy; oversized bulk goes to object storage with a reference link | economy | Approved dataset, destination config, naming conventions, work-item id | Fixture files, attachments, docs pages, one traceability comment on the ticket | R3 |

> The reasoning-heavy parts — decomposition, coverage design, quality judgment — stay on tiers that can reason; publishing is pure mechanics on economy, and its R3 write surface stays as small as the pipeline allows.

## Flow

1. **Trigger** — an engineer asks interactively, or a work item entering a ready-for-testing status fires the automation.
2. **Confirm preconditions** — data type, output format, volume, locale, compliance flags, and whether validation and human approval are on for this run.
3. **Obtain the schema** — inline paste, or fetch via the read connector from an API-spec source, docs wiki, or schema repo.
4. **Generate** — below the volume threshold the model emits records directly; above it the model emits a generation spec and a deterministic skill expands it into the full dataset.
5. **Validate (optional gate)** — check completeness, typing, synthetic-only personal fields, scenario coverage, and count. Partial/missing verdicts route back to step 4 with the report attached and never reach publishing.
6. **Human review gate** — an engineer inspects the draft and approves or returns it. Enable whenever output persists to a shared system or validation is off; skip only for low-risk, non-personal, ephemeral data.
7. **Publish** — write to the destination with the AI-origin tag, traceability link, and agreed create-vs-update behavior; park oversized outputs in object storage and post a link.
8. **Measure** — log adoption, time-per-dataset, and first-pass validation outcomes to steer prompt and workflow tuning.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Schema retrieval (optional) | API-spec catalogs, docs wiki, DB schema repos, local spec files | Read | Official connector, else official CLI, else plain file read; service account needs read access to the schema source; optional — many teams paste the schema inline |
| Deterministic bulk generation (optional) | Local script or fake-data library behind a reusable skill | Read/Write | Skill contract: takes the model's generation spec plus a target count, emits the dataset file in the requested format, model-independent; reuse an approved marketplace skill before wrapping your own generator |
| Dataset publishing | Issue trackers, work-item systems, test-management tools, docs wiki, git hosting | Write | Account needs create/update rights on the destination; verify attachment size limits — large files go to object storage with a posted reference link |

> Wiring preference, in order: official MCP connector → official CLI → REST/SDK wrapped in a skill → custom-built as last resort.

## Guardrails

- **Injection defense** — feed the model schemas, never real example rows: pasted realistic examples get echoed back as if they were templates, leaking real-looking values. Treat fetched schema content as data, not instructions. In the automated path, scope the trigger strictly to the status-change event so the publish-back comment or attachment cannot re-fire the rule into a loop.
- **Writable-field allowlist** — the Publisher may only create/update dataset files, attachments, docs pages, and one traceability comment on the linked work item. Every artifact carries the AI-origin label (metadata tag or file header). Fix create-vs-update behavior before deployment: versioned new file (safe, keeps history), overwrite per schema+ticket (simple, loses history), or ask at publish time.
- **Human gate** — the reviewer checks schema conformance, that personal fields are visibly synthetic, and that the requested scenario partitions are present. Mandatory when output lands in version control or any shared persistent system, or when validation is off. Start with the gate on; relax to auto-publish only after quality proves consistent for that schema type, and only for low-risk non-personal data.
- **Grounding** — every record conforms to the declared schema; the generator invents no fields, locales, or constraints the schema omits. Personal fields must be recognizably synthetic: non-deliverable email domains, unallocated phone ranges, format-valid but never-issued identifiers, birth dates never in the future. The validator enforces per-category coverage (happy path, boundary, null/empty, special characters, locale variants) and blocks publication when a required category is missing.

## Automation

Pin into an unattended workflow when the trigger and shape are stable; keep it a human-invoked agent while schemas and conventions are still settling.

Trigger → flow: work item moves to ready-for-testing → an automation rule posts the item key to the agent endpoint → pinned workflow (fixed step order, pinned model/prompt/toolset per step, no on-the-fly tool choice): fetch schema if a connector is configured → generate → validate if enabled, rerouting on partial/missing → human review if required, rerouting on return → publish.

Default posture is semi-automated: auto-trigger and generate, with validation and approval configurable per data type and risk. Promote to fully automated only for low-risk non-personal datasets once quality is consistently high — keep the human gate until adoption and first-pass metrics justify removing it. Guard the trigger against re-firing on the comment or attachment the publish step writes back.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption rate — AI-produced datasets over all datasets | Filter by the AI-origin tag in the tracker, test-management tool, or fixture folder; AI count / total |
| Productivity gain — time per dataset vs manual baseline | Work-item time logs or retrospective sampling; percent reduction in manual hours |
| First-pass validation rate — clean pass with no regeneration | Count validator verdicts per run: clean vs partial/missing needing a redo; meaningful only with validation on (pre-AI baseline is zero — no automated validation existed) |
| Acceptance rate at the human gate | Approved-as-is vs returned-for-refinement during review |
| Team perception of realism, edge coverage, format correctness | Structured retrospective feedback |
| Diagnostic pairing for evolution | High adoption + low first-pass → generator needs more schema context or better few-shot samples; high first-pass + low adoption → friction is in the workflow — cut setup steps or add formats instead of tuning prompts |
