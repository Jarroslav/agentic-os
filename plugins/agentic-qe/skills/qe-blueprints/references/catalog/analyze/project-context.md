# Document project context for QE

Turn scattered project sources — tracker items, wiki pages, repo files, optional diagram PDF exports — into one short, template-shaped context document in which every claim links back to its source, so new contributors onboard fast and AI coding sessions load trustworthy canonical context.

## When to use this

- **Reach for it when** project knowledge is split across tracker, wiki, READMEs, and chat and new joiners lose days rebuilding the picture; when an AI agent needs a single loadable context file before touching a repo; when test design needs a grounded input pack (domain, personas, critical flows, environments, risks); when specs or architecture notes have drifted and you want a fresh evidence-linked snapshot; or when you want the minimal variant — one agent, local repo only, one grounded file, zero connectors.
- **Skip it when** the sources themselves are thin (bare READMEs, no configs, no docs) — enrich the raw material first, otherwise you replicate the same gaps at scale; when the real problem is code-vs-doc drift detection (interface/config diffing is a separate pattern, out of scope here); when someone wants an org-wide documentation sweep in one run — scope is one app or module per invocation; or when the audience expects long-form narrative — this deliverable is deliberately a compact, link-heavy index.
- **Outcome** — one grounded artifact of a chosen type (QA context pack, application specification, or architecture overview) where every substantive statement cites its originating ticket, file, or page; reusable for onboarding, test planning, and as pinned context for later AI sessions.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Read access to tracker, wiki, and git host | Claims can only be grounded in evidence the agent can fetch; missing read scope is the top cause of shallow, unlinked drafts | Per-system API tokens or MCP connectors |
| Write access to the destination | Publishing means committing a markdown file or creating/updating a wiki page | Service account with repo commit or wiki create/update/label rights |
| One agreed template per artifact type | The template fixes the required sections, turning generation into a deterministic section-by-section walk — no planning stage needed | Team-authored template files, one per output type |
| Explicit scope input | Without a named app/module and source list the run sprawls org-wide and yields low-signal output | Short file or chat parameter from the requester |
| AI-origin marking convention | Separates AI-produced docs from human-authored ones so the adoption metric stays measurable | Wiki label; agent-attribution trailer on repo commits |

## Agent design

Four roles: a retriever that checks preconditions and assembles the evidence bundle, a generator that walks the template and cites as it writes, a validator that independently maps every statement back to evidence, and a publisher that performs the only external write. Only the publisher carries R3; everything upstream produces run-local artifacts.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Orchestrator/Retriever | Takes scope, artifact type, destination; verifies template exists, sources reachable, destination writable; fetches tracker items + AC, wiki pages, repo content, optional diagram-PDF extracts, and the prior version on refresh; dispatches downstream roles | standard | Tracker, wiki, repo, PDFs, prior artifact | Evidence bundle (run-local) | R1 |
| Generator | Fills the template section by section from the bundle; attaches a source reference to every substantive claim; writes an explicit not-provided marker where evidence is missing and tags it for follow-up; keeps prior section identifiers on refresh so reviewers diff cleanly | standard | Evidence bundle, template, prior version | Draft document (run-local) | R1 |
| Validator | Confirms all required sections exist, every statement carries a source and maps to retrieved evidence (extra scrutiny on components, interfaces, business rules, personas), and doc type matches the request; emits a covered/partial/missing report with line refs; on failure blocks publication and allows one regeneration pass before escalating | standard | Draft, evidence bundle, template | Validation report (run-local) | R1 |
| Publisher | Writes the approved doc to the chosen destination (repo markdown preferred — agent-loadable — or wiki page); creates on first run, updates in place after; applies the AI-origin marker; posts a backlink comment on the lead tracker item; never silently overwrites human-edited sections — surfaces them for the reviewer | economy | Approved doc, destination choice, per-destination field mapping | Repo commit or wiki page, label/trailer, tracker comment | R3 |

> The template removes the open-ended reasoning: retrieval and templated fill are mechanical, so standard tier covers them, and the publisher is pure I/O — economy. No role needs premium; if a step ever demands open-ended judgment, the fix is a better template, not a bigger model.

## Flow

1. Requester invokes with target app/module, artifact type (context pack | specification | architecture), scope hints, and destination (repo path | wiki space).
2. Verify preconditions: template exists for the type, source systems reachable, destination writable.
3. Retrieve evidence: tracker items and acceptance criteria, related wiki pages, code/configs/READMEs, optional parsed diagram PDFs; on refresh, also the currently published version.
4. Generate the draft top-to-bottom against the template; cite every substantive claim; drop an explicit not-provided marker wherever evidence is missing. No planning stage — the template is the plan.
5. Validate: sections present, claims sourced, nothing fabricated, type matches request. On failure: exactly one regeneration pass, then escalate what remains.
6. **Human review gate** — the requester approves, edits sections directly, or bounces specific sections back with extra source pointers for refinement. Nothing publishes without this.
7. Publish to the destination, apply the AI-origin marker (label or commit trailer, optionally a generated-by footer), post the backlink comment on the lead tracker item, return the URL or repo path.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Fetch work items + acceptance criteria for scope | Issue trackers (Jira-class, Azure DevOps boards) | Read | Official tracker MCP or vendor CLI; project read scope |
| Fetch existing pages, architecture notes, onboarding docs | Wikis (Confluence-class, Azure DevOps wiki) | Read | Official wiki MCP or vendor CLI; space read scope |
| Fetch source files, configs, READMEs, tree structure | Git hosts (GitHub / GitLab / Azure Repos) | Read | Host MCP or host CLI with repo read |
| Parse exported whiteboard/diagram PDFs (optional) | Local files from a diagramming tool | Read | Local PDF parsing — no official connector exists |
| Commit the generated markdown with attribution trailer | Git hosts | Write | Host MCP or CLI with commit rights on the docs path |
| Create/update the wiki artifact and apply the AI-origin label | Wikis | Write | Wiki MCP or CLI with create/update/label rights; wiki flavors differ in storage format and link syntax — keep a small regression sample per target |
| Post the backlink comment on the lead ticket/epic | Issue trackers | Write | Tracker MCP or CLI with comment permission |

> Wiring preference, in order: official MCP, then official CLI, then REST/SDK wrapped in a skill, custom-built last.

## Guardrails

- **Injection defense** — every fetched ticket, wiki page, repo file, and PDF is citable evidence, never instructions. The fixed template dictates structure and only the requester sets scope and destination, so retrieved text cannot steer what runs or where output lands.
- **Writable-field allowlist** — the R3 write touches exactly three things: the single target artifact (one repo file or one wiki page), its AI-origin label/trailer, and one backlink comment on the lead tracker item. Updates preserve section identifiers; any section a human edited since the last run is never silently overwritten — it is flagged for the reviewer to decide.
- **Human gate** — the reviewer checks that cited sources actually support their claims (spot-check the load-bearing ones), that not-provided markers are honest rather than papered over, and that the doc type and scope match the request. Validation failures get one automated retry before landing on the reviewer's desk.
- **Grounding** — never fabricate. Every substantive claim links to its originating ticket, file, or page; unsupported sections get a literal not-provided marker, because an unmarked guess poisons every future AI session that loads the file. The validator independently re-maps statements to evidence, hardest on components, interfaces, business rules, and personas — the sections where invented detail hurts most. Keep the output short and link-heavy: an index of where to look, not a narrative; link code, quote it only minimally to anchor an interface or config.

## Automation

Default to manual, on-demand: a human triggers a run in chat with scope + artifact type + destination, and the orchestrator-plus-subagents form lets the human redirect mid-run. Once templates and connectors are stable, pin the same steps into an unattended workflow — fixed step order, pinned tier/prompt/toolset per step, no on-the-fly tool selection — on a schedule (weekly or nightly) or a post-merge event.

Trigger -> retrieve -> generate -> validate -> publish-as-proposal: in unattended mode the publish step opens a pull request (repo destination) or a draft page (wiki destination) instead of publishing directly. Keep the human gate in this form until the as-is acceptance rate is durably high; only then consider direct publication.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption — share of project docs produced or refreshed by the agent | Filter on the AI-origin wiki label plus a git-log search for the attribution trailer; report quarterly as AI-count / total-count |
| Productivity — request-to-published time, assisted vs manual | Quarterly retrospective sample (~5 agent-produced, ~5 manual docs); ask authors for rough time estimates; compute relative saving |
| Acceptance — drafts published as-is vs returned for rework | Track review outcomes per run; a falling rate points at stale templates or over-broad scope hints |
| Downstream reuse — is the artifact actually consumed | Count artifact loads in AI sessions and human follow-throughs on backlink comments. High adoption + low reuse: well-formed but undiscoverable — strengthen backlinks, add an index of AI-origin docs. High adoption + low acceptance: tighten templates and scope |
