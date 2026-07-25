# Spend Context Wisely — Context Economy for QE Agents

Every token an agent reads or writes costs money and attention. This reference tells you how to cut token spend while you fill in agent stubs — above all for leaf agents that pull from connectors (Jira, Azure DevOps, GitHub) or chew on large inputs — without lowering output quality.

Apply it during stub completion: as you write each agent's instructions, run every step through the levers below.

## The Four Levers, Ranked

Work them in this order; the first lever usually removes the most spend.

| # | Lever | What it saves |
|---|-------|---------------|
| 1 | Move deterministic work into scripts | Model never touches mechanical steps |
| 2 | Shrink connector/CLI payloads at the source | Bloat never enters context |
| 3 | Pass artifacts between agents by reference | Payloads never transit the orchestrator |
| 4 | Pin each agent to the lowest adequate model tier | Every remaining token costs less |

## Lever 1 — Scripts, Not Tokens, for Deterministic Work

> Models are expensive per token and unreliable at mechanical operations — counting, sorting, joining, deduplicating, parsing, aggregating. A script is exact, repeatable, and free after it exists.

**Rule: if a step has exactly one correct output for a given input, implement it as a script. Never delegate it to the model.**

The working pattern: the agent writes or calls a small helper for the mechanical portion, then reasons only over the helper's compact output. The script does the volume; the model does the judgment. Script output is also a grounding anchor — the model analyzes what the script produced, not what it half-remembers from a raw dump.

Persistence rules:

- A helper an agent authors once goes into the owning skill's `scripts/` directory so later runs reuse it instead of regenerating it. (Saving a script is an R2 action — it writes repo files — so it belongs in the agent's declared blast radius.)
- A deterministic check that recurs across runs becomes a **validator**, not a paragraph of prompt text repeated forever.
- Scripts that only emit run artifacts stay at R1; pure filters are R0.

### Waste patterns and their remedies

| Waste symptom | Remedy |
|---------------|--------|
| Model reads hundreds of tickets to tally counts by status | jq/Python script aggregates; model sees a ~10-row summary |
| Model orders ~80 test cases by priority in prose | Script computes scores and sorts; model reviews only the top slice |
| Model dedupes stack traces across ~200 flaky runs | Script normalizes and hashes traces; model triages the unique buckets |
| Model diffs two API schemas field by field | Script emits added/removed/changed lists; model assesses impact |
| Model scans a multi-MB log or JSON file for errors | grep/jq extracts matching lines; model analyzes only those |

### Worked QE examples

**Defect analysis.** A script fetches the ticket and keeps only summary, description, status, priority, components, labels, recent comments, and linked defects, emitting a compact brief. The model analyzes the brief — never the raw ticket JSON.

**Test prioritization.** The scoring rubric (risk, recency, failure history, coverage gap) lives in a script that outputs a sorted, scored table — reproducible and auditable. The model explains the top entries and sanity-checks the edges.

## Lever 2 — Trim Connector Payloads at the Source

Work-item APIs — Jira, Azure DevOps, GitHub, whether reached via MCP or CLI — wrap each item in a heavy envelope: changelogs, rendered fields, avatars, watchers, custom fields. Ingesting that envelope raw is the single most common hidden token drain in QE pipelines.

> Select fields in the request, not after the fetch. Bytes you discard after they transit the model already cost you their tokens.

Practices:

- **Field selection first.** Ask the API for exactly the fields the step consumes. Never fetch everything "just in case."
- **Bounded pagination.** Set a small, deliberate page size (e.g. a low `maxResults`). When a total or aggregate needs every page, a script iterates the pages — the model never does.
- **Kill rendered fields.** Rendered HTML and Atlassian Document Format bodies are grossly verbose. Have a script convert them to plain text or project them away entirely.
- **Project when the tool won't.** If a tool can't restrict its own output, pipe it through jq or a short Python projection so only the keys you use survive.
- **Prefer CLIs with native projection.** `gh` with JSON field selection, `az` with query expressions, Playwright codegen — these beat their MCP equivalents on both round-trips and payload size.

Per-connector field-selection snippets live in the connector tool guide (`../tool_guides/connectors.md`).

## Lever 3 — Hand Off by Reference

In a multi-agent pipeline, a leaf that returns its full output through chat forces that content into the orchestrator's context — and often into every downstream prompt.

**Rule: a leaf never returns a full payload through chat. It writes its result to a file/artifact and replies with the path plus a one-line status.**

The orchestrator then moves references between stages and opens a file only when a synthesis step genuinely needs the content. This is the same mandatory file-based handoff convention defined in `agent_file_based.md` — token economy is part of why that convention exists. This document does not restate the protocol; see that reference for the mechanics.

## Lever 4 — Lowest Adequate Model Tier

**Rule: pin each agent to the cheapest tier whose eval suite still passes.**

| Role shape | Default tier |
|------------|--------------|
| Coordination, formatting, validation, publishing | economy — these rarely justify more |
| Orchestrators | standard |
| Leaf doing genuine standalone deep reasoning | premium — the only place premium is warranted |

Tier-assignment guidance in depth: `../tool_guides/model_selection.md`. Speak in tiers (economy / standard / premium), never in vendor model ids.

## Context Hygiene

Four habits that keep an agent's window lean regardless of workload:

1. **Progressive disclosure.** Load a reference doc or large example only in the step that consumes it — not up front for the whole run.
2. **Stable before volatile.** Order fixed instructions and tool schemas ahead of runtime state so prompt caching keeps working and summaries aren't rewritten each turn. (See the prompt-caching checklist in the sibling checklists doc.)
3. **State notes over transcripts.** Compress long histories and logs into a brief state note; never carry the full transcript forward.
4. **One job per agent.** Single responsibility means narrow scope, and narrow scope needs less context. If an agent's context keeps growing, split the agent.

## Decision Rules

| Situation | Rule |
|-----------|------|
| Step has one correct output per input | Script, never the model |
| Calling any connector API | Only needed fields, bounded page size |
| Leaf agent finishing its work | File reference + terse status, never the payload |
| Choosing a model tier | Lowest tier that passes evals; premium only for deep standalone reasoning leaves; standard as orchestrator default |
| Deterministic check recurs | Promote to a validator |
| Mechanical helper written once | Save it under the skill's `scripts/` directory for reuse |

## Per-Agent Checklist

Run this against every agent stub before you call it done:

- [ ] Every deterministic step is a script, not a model instruction
- [ ] Every connector call selects fields and bounds page size
- [ ] Raw payloads are projected or summarized by a script before they enter context
- [ ] Outputs hand off by file reference plus one-line status
- [ ] Model tier is the cheapest that passes the agent's evals
- [ ] Large docs and examples load only in the step that uses them
- [ ] Stable content precedes volatile state for cache-friendly prompts

## Scope

This document covers cost and token levers only. It is not a general prompt-engineering or agent-architecture guide. It does not define the artifact-handoff protocol (see `agent_file_based.md`), does not document per-connector API syntax (see `../tool_guides/connectors.md`), and does not name vendor pricing or specific model ids — tier language only.

## Related References

- Sibling checklists doc — skills checklist (saving reusable scripts) and prompt-caching checklist (stable-before-volatile ordering)
- `../tool_guides/connectors.md` — per-tool field-selection snippets
- `../tool_guides/model_selection.md` — tier assignment
- `agent_file_based.md` — the file-based handoff convention Lever 3 builds on
