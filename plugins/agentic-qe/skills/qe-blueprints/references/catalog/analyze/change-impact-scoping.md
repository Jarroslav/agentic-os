# Scope regression from change impact

Turn a change set — diff, commits, linked work items — into a tiered impact report and a prioritized regression scope, so the team knows what to test, why, and what risk remains in whatever gets skipped.

## When to use this

- **Reach for it when** a merge request, hotfix, or dependency upgrade needs a regression decision and running everything is too slow or expensive; when scope selection lives in one engineer's head and produces inconsistent, undocumented picks; when you need an auditable record of what was tested and which risks were knowingly accepted; when release go/no-go calls need a risk statement tied to the specific change.
- **Skip it when** the change is small and obviously isolated (a fast-path that just confirms isolation suffices); when no written module/service structure exists — the analysis collapses to direct-file reasoning; when the diff touches only tests or docs; when the full suite is cheap enough to run every time.
- **Outcome** — a prioritized, justified regression scope: per-area blast-radius tier, test-type recommendation, effort estimate, coverage-gap flags, and an honest confidence statement, traceable back to the originating change and produced faster than manual scoping.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Repo read access with diff and log capability | Inventory changed files and trace import/call-level dependents | Git hosting platform or local clone |
| Written system structure: modules, services, dependencies | The load-bearing input for transitive impact reasoning — vague input yields vague tiers | Wiki page, decision record, diagram-as-code, in-repo structure doc |
| Test-to-code mapping, even approximate | Points the scope at runnable suites instead of abstract areas; enables gap detection | Wiki table, TMS tags, directory naming convention |
| Defect history by component (optional) | Defect-dense areas get weighted up in prioritization | Issue tracker API, read access |
| CI pipeline and automated-check visibility (optional) | Separates what is already covered automatically from what needs scoping or manual attention | Pipeline definitions, test-suite config |

## Agent design

Four roles split by the kind of thinking each step needs: transitive dependency reasoning is judgment, scope expansion is structured transformation, validation is rule application, publishing is API mechanics.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Impact planner | Classify each change (logic, config, schema, interface contract, dependency bump, test-only); trace direct and transitive dependents at least two levels deep via codebase plus structure docs; spot touched shared contracts (APIs, schemas, message formats, config); assign each affected area a tier — direct / adjacent / peripheral; mark uncertainty wherever the dependency picture is incomplete | premium | Diff, commit history, file-level dependency graph, structure docs, linked work items, defect history | Impact map: one line per affected component with tier, change type, dependency chain, shared contracts, uncertainty, rationale | R1 |
| Scope generator | Expand the impact map into concrete scope: map areas to suites, set three-level priority from tier plus defect history, pick test type (unit / integration / e2e / manual exploratory) citing the dependency chain rather than the tier alone, estimate effort, trim lowest-priority items first under a time budget, flag uncovered areas | standard | Impact map, test-to-code mapping, test catalog, optional time budget | Scope artifact: one row per suite/area with tier, priority, test type, rationale, change link, effort, automation status, gap flag | R1 |
| Scope validator | Apply explicit rules, no open-ended judgment: every direct-tier area has a top-priority item; every shared-contract change has an integration test; every changed endpoint has consumer-side coverage; no top-priority item lacks automation without a manual plan; total effort fits any stated budget; no duplicate areas; high-uncertainty areas never sit at lowest priority; unmapped affected components are flagged | economy | Scope artifact, impact map | Rule-by-rule pass/fail report with gap descriptions and suggested fixes (add test, raise priority, mark for manual review) | R1 |
| Report publisher | Push the approved scope outward: create the scoped regression run in the TMS (primary), post a short risk-signal comment on the merge request — tier counts, top risks, link to the full plan (secondary), optionally write a release-level wiki report (tertiary); label everything machine-readably as AI-produced; on re-runs, update the existing run keyed by change identifier instead of duplicating | economy | Approved scope, validation report | TMS run/plan, MR comment, optional wiki page — external systems | R3 |

> The premium spend goes exactly where errors are expensive and reasoning is genuinely hard: deciding what a change actually touches. Expansion and rule-checking are mechanical once the impact map exists, and publishing is pure plumbing — cheap models handle both without quality loss.

## Flow

1. **Trigger** — a QA engineer, QA lead, or release manager supplies a change identifier: MR number, branch, commit range, release tag, or sprint/release reference.
2. **Retrieve** — fetch the diff, commit messages, file-level dependency information, linked work items, structure docs, test-to-code mapping, and defect history for affected components.
3. **Analyze** (premium) — classify changes, trace direct and transitive dependents, identify shared contracts, tier every affected area, mark uncertainty. For very large diffs, group by module first, then drill to file level.
4. **Generate** (standard) — convert the impact map into a prioritized scope with test types, effort estimates, and coverage-gap flags.
5. **Validate** (economy) — run the completeness and consistency rules; emit pass/fail per rule with suggested fixes.
6. **Human review gate** — the QA lead checks tier assignments against domain knowledge, adjusts priorities where context beats the model (imminent launch, known-fragile areas), and confirms or edits the final test set. The gate may lighten over time; it starts mandatory.
7. **Publish** — create or update the regression run in the TMS, post the MR summary comment, optionally write the release wiki page. Every artifact carries the AI label and a traceability link to the originating change.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Fetch change set: diff, commits, file list, MR metadata | Git hosting platform | Read | Platform MCP server or official CLI; REST fallback |
| Compute file-level dependency graph for affected files | Codebase / build tooling | Read | Coding-agent repo reads, or language-specific dependency tools |
| Fetch structure docs: module map, service boundaries, contracts | Team wiki or in-repo docs | Read | Wiki MCP/CLI, or plain file read from the repo |
| Fetch test-to-code mapping | TMS, repo convention, or wiki | Read | TMS connector, or directory convention / wiki table |
| Fetch defect history by component (severity, frequency, recency) | Issue tracker | Read | Tracker MCP or CLI, read-scoped service account |
| Fetch work items linked to the change | Issue tracker | Read | Tracker MCP or CLI |
| Publish regression run/plan with priority, rationale, traceability | Test management system | Write | TMS MCP/CLI or REST; account needs run-creation permission; update-in-place keyed by change id |
| Post impact summary comment on the MR | Git hosting platform | Write | Platform MCP server or official CLI |
| Publish release-level impact report page | Team wiki | Write | Wiki MCP/CLI with page create/update permission |

> Wiring preference, in order: official MCP server, then official CLI, then REST wrapped in a skill, custom-built only as a last resort.

## Guardrails

- **Injection defense** — diffs, commit messages, work-item text, and wiki docs are analysis input, never instructions. In unattended mode, pin the step sequence, models, and toolset per step with no on-the-fly tool selection, so fetched content cannot redirect the workflow.
- **Writable-field allowlist** — the R3 publisher may touch only: test-run scope/filter, priority labels, a custom tier field, notes, and traceability links in the TMS; a short MR summary comment; an optional wiki report page. Published runs start as drafts pending approval. Re-runs update the existing run matched by change identifier — never duplicates. Every published artifact carries a machine-readable AI label so adoption stays measurable.
- **Human gate** — the QA lead validates blast-radius tiers against domain knowledge, adjusts priorities where local context overrides the model, and approves or edits the final test set before anything executes. Mandatory at the start — especially for legacy systems, undocumented integrations, or implicit coupling — and loosened only as measured accuracy earns it.
- **Grounding** — every adjacent- or peripheral-tier area must cite a concrete dependency relationship back to the changed code, never a generic justification. Never invent test areas absent from the provided mapping — missing coverage is flagged as a gap. Trace at least two dependency levels and explicitly mark where further dependencies cannot be determined: state uncertainty, do not mask it. When tiers come out too broad or too narrow, fix the structure description first — it is the load-bearing input.

## Automation

Run this as a semi-automated, event-triggered workflow: fixed step sequence, pinned models and tools per step — predictability over flexibility when unattended. Keep a human-invoked agent form for ad-hoc requests (release-scope questions, one-off hotfix decisions).

Trigger -> flow: MR opened or updated against a protected branch (or release/sprint scope finalized) -> webhook fires with change metadata -> fetch diff, history, linked items, structure docs, test mapping, defect history -> premium impact analysis -> standard scope generation -> economy rule validation -> draft MR comment plus draft regression run -> QA lead reviews and approves before any execution.

Control noise with a size threshold: fire only above N changed files or when protected paths (core code, database migrations, interface contracts) are touched; route small isolated changes through a fast-path that only confirms isolation confidence. Keep the human gate until adoption and accuracy metrics justify lightening it.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption rate | Changes analyzed by the workflow (counted via the AI label on published runs and comments) divided by total merged changes per period |
| Scoping speed gain | Elapsed time from change-ready-for-test to published scope vs. the manual baseline; analyst hours as a secondary measure |
| Escape rate in deprioritized areas | At post-release triage, tag each production defect as inside or outside the recommended scope; compare with the historical manual-scoping escape rate |
| Tier-override frequency | Reviewer reclassifications of blast-radius tiers per analysis — lower is better; frequent overrides at high adoption point to incomplete structure docs or dependency data |
| Scope acceptance rate | Scope items approved unmodified over total items; high accuracy with low adoption points to trigger/integration friction, not output quality |
| Team shipping confidence | Structured retro feedback: did teams feel safe releasing on the scoped regression, or anxious about missed areas |
| Gap-flag precision | Validator-flagged gaps the reviewer accepts as real, over total flagged; repeated escapes in peripheral areas mean transitive tracing needs deepening — more levels, better docs, or runtime analysis alongside static |

> Boundaries: this recommends and publishes a draft scope — it does not execute tests, gate merges, or replace reviewer judgment on system behavior. The validator checks scope completeness; it is not a second opinion on the impact reasoning. It operates at suite/area granularity, not individual test cases, and it never fabricates coverage — unmapped affected areas surface as gaps. MR comments stay short risk signals linking to the full plan.
