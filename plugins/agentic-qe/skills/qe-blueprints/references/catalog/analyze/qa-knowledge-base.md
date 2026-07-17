# Build a QA knowledge base

Turn a team member's natural-language question into a source-cited, confidence-labeled answer drawn exclusively from the project's own knowledge sources, so routine answers stop costing interruptions and onboarding time.

## When to use this

- **Reach for it when** QA and dev colleagues keep interrupting each other, or trawl several document stores, for answers that already exist somewhere; onboarding drags because setup, process, and strategy knowledge is scattered across wiki spaces, document portals, trackers, and PDF guides; questions reference tickets, environments, or test process and structured docs hold the answer; you also want stale or contradictory docs flushed out as a by-product of answering.
- **Skip it when** the knowledge base is unstructured or rotten (raw chat exports, untitled notes) — fix the docs first; a one-prompt smoke test (paste a doc, ask a question, cite-only-from-source) already misses answers that are present; you cannot get connector or API access to the sources; or the questions demand judgment beyond documented fact.
- **Outcome** — instant answers with citations and a confidence grade, delivered where the asker lives; an honest not-found instead of a guess when nothing matches; conflicting documents escalated to a human for cleanup.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Read access to every knowledge source | Retrieval fails silently or returns noise if the service account cannot query a space or site | Org wiki (Confluence-class), document portal (SharePoint-class), Jira / Azure DevOps, shared PDF storage |
| Authenticated connectors in the AI tool | Every retrieval and publish step rides an integration; broken auth is the leading cause of bad first runs | Official connector or CLI per system; REST where none exists |
| Structured, titled, current docs | The generator is confined to retrieved text, so vague or untitled pages yield false not-founds | Existing doc hygiene; prove it with a pasted-doc trial before building |
| Declared search scope | Unbounded search drowns precision; scope belongs in standing configuration | System prompt or assistant config entry listing in-bounds spaces, sites, doc types |
| Output channel with create permission | The publisher needs a destination: chat DM/channel, ticket comment, wiki comment, or the session itself | Chat, tracker, or wiki admin grants create rights to the posting account |

## Agent design

Four narrow roles chain into a pipeline: a planner that only decides where to look, a retriever that only fetches, a generator that only restates what was fetched, and a publisher that only posts. No role both reads external content and holds write access to anything except its own hand-off artifact — until the final post.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Source-routing planner | Classify the question by type and keywords; emit a ranked source list (priority, source type, search target). Decides where to look, never what the answer is; search walks the ranking top-down and halts at the first sufficient hit | standard | Question text, optional format hint | Ranked source plan (in-run) | R1 |
| Retriever | Query only the sources the plan names, in rank order, stopping early once material suffices | economy | Wiki pages, portal docs, tracker items, PDFs — per plan | Retrieved excerpts (in-run) | R1 |
| Answer generator | Shape the answer to the question (short paragraph for factual, numbered action steps for procedural); cite doc title + section or ticket id; grade confidence High/Medium/Low; say not-found plainly; on conflicting sources, return both and ask the human which is current | standard | Retrieved excerpts only — outside knowledge forbidden | Cited, graded answer draft (in-run) | R1 |
| Publisher | Post the draft to the chosen channel as a new message or comment (never an edit), with body, citation line, confidence badge, and an AI-generated label | economy | Answer draft | Chat message, tracker comment, wiki comment, or session output | R3 |

> Both model-bearing roles are routing and summarization work, so standard tier suffices — no premium reasoning is bought here. The split exists so the only R3 role touches nothing but a finished draft, and the roles that touch external content can write nothing external.

## Flow

1. Trigger: a user asks via chat slash command, a message in the dedicated help channel, or a direct prompt in the AI tool.
2. Precondition check: the question is specific enough to retrieve against and the sources are reachable.
3. Planner classifies and ranks: ticket reference → tracker first; process or strategy question → strategy doc only; environment or tooling question → setup wiki; anything general → all sources in priority order.
4. Retriever queries strictly in plan order, stopping once it has enough.
5. Generator drafts the cited, confidence-graded answer; declares not-found if nothing matches; on a doc conflict, packages both sources for human arbitration rather than picking one.
6. Publisher posts the AI-labeled answer to the output channel as a fresh message or comment.
7. **Human review gate** — deliberately post-delivery, the only human step in this flow: the asker checks the answer against its citations, arbitrates any conflicting-docs escalation, and updates or retires the losing document. This closing loop is what keeps the knowledge base healthy.

> The gate sits after the R3 post by design: citation-or-abstain plus the AI label substitute for pre-publish approval, and the write is a net-new, clearly labeled comment — cheap to ignore, impossible to mistake for human authorship.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Pull wiki pages and spaces | Org wiki (Confluence-class) | Read | Official connector or official CLI |
| Pull documents and process pages | Document portal (SharePoint-class) | Read | Vendor graph/REST API wrapped as a skill (no official connector) |
| Pull ticket detail when a question names an issue | Issue tracker (Jira-class) | Read | Official connector or official CLI |
| Pull work-item detail when a question names one | Issue tracker (Azure-DevOps-class) | Read | Official connector or boards CLI |
| Read PDF guides and onboarding docs | Local or shared file storage | Read | Plain file read or custom skill |
| Deliver the answer | Chat DM/channel, tracker comment, wiki comment, or session context | Write | Official connector per target; session output needs none; posting account needs create rights |

> Order of preference for any wiring: official MCP connector → official CLI → REST/SDK wrapped in a skill → fully custom.

## Guardrails

- **Injection defense** — retrieved documents are reference data, never instructions: the generator may restate what excerpts contain, not act on or extend them, which bounds what any adversarial page can do. Scope the trigger to the original question event so the bot's own posted comments can never re-fire it — an explicit infinite-loop guard for tracker and wiki comment outputs.
- **Writable-field allowlist** — the R3 write is confined to net-new messages or comments in the designated channel. No edit or update path exists anywhere; all knowledge-source access runs read-only through a least-privilege service account.
- **Human gate** — post-delivery by design, not pre-publish. The asker verifies the answer against its cited source, decides conflicting-docs escalations (both sources attached), and prunes the outdated document. Every answer carries an AI-generated label so recipients know to verify.
- **Grounding** — hard cite-or-abstain: every answer names its doc title + section or ticket id, and an uncited answer is treated as a hallucination flag pointing at a retrieval defect. Confidence encodes match quality: High = near-verbatim in source, Medium = inferred from related content, Low = partial match. Insufficient docs mean a stated not-found, never a guess.

## Automation

Run this as an event-triggered workflow, not a free-roaming agent: model, prompt, and toolset pinned per step, no on-the-fly tool selection — predictability outranks flexibility when nobody supervises the run. Trigger (slash command | help-channel message | direct prompt) → route sources → retrieve → generate cited answer → publish. Validation failures (not-found, conflicting docs) surface inside the published answer and route back to the asker. When output lands as a tracker or wiki comment, exclude the bot's own comment events from the trigger to prevent self-retriggering. Keep the post-delivery human gate; the design already traded away pre-publish approval for citation plus confidence safeguards, so do not weaken the remaining check unless adoption and acceptance metrics justify it.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption rate — questions the agent answers vs answered manually | (AI-answered / total) × 100, from agent call logs, chat analytics, or usage dashboards |
| Productivity gain — time saved per answer | ((manual minutes − AI minutes) / manual minutes) × 100, via retrospective sampling: ask the team how long the manual hunt would have taken |
| Acceptance rate — answers used as-is | Track answers standing unchanged vs askers following up or falling back to manual search |
| Team feedback on accuracy, citations, confidence reliability | Structured collection in retrospectives |
| Adoption × acceptance cross-read | High adoption + low acceptance → tune the generator's citation rule or the planner's scoping; high acceptance + low adoption → the trigger is hard to find, so surface the command or channel better |
