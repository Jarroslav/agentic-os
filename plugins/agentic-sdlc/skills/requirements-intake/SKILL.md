---
name: requirements-intake
description: |-
  Takes whatever the user hands it — loose text, an external ticket ID, a story file path, a bare idea — and normalizes it into a single requirements.md. Ticket lookup goes through an adapter declared in `.agentic/guides/`, so no specific ticket backend is baked in. Called by sdlc-pipeline at Phase 1.
version: 0.1.0
license: Apache-2.0
authors:
  - agentic-os
---

# requirements-intake

Channels several possible input shapes into one normalized requirements doc. Downstream phases always read the pipeline's `requirements.md`.
Every intake path must also resolve a work item reference. External tickets are
optional and adapter-driven; when none exists, create or link a repository-local
work item under `docs/superpowers/work-items/` instead.
Lifecycle adapter behavior is defined in
`${CLAUDE_PLUGIN_ROOT}/references/work-item-adapters.md`. This skill only
handles ticket lookup — development lifecycle sync is emitted separately by
`sdlc-pipeline` after branch guard success, using the `prepare_for_development`
intent.

## Inputs

- `raw_input` — what the user passed to `sdlc-start` or `sdlc-autonomous`
- `mode_flag` — `--greenfield` if explicitly set, otherwise auto-detect
- `run_dir` — absolute path of the run state directory

## Detection order

1. **Explicit `--greenfield` flag** → greenfield funnel.
2. **Looks like a local story path** (`docs/stories/*.md`) → story-file funnel.
3. **Looks like a local work item path** (`docs/superpowers/work-items/*.md`) → local work-item funnel.
4. **Looks like an external ticket ID or URL** → ticket-adapter funnel.
5. **Otherwise** → free-form funnel.

## Local work item requirement

A work item reference must be established before `<run_dir>/requirements.md` gets written:

- Existing local work item: use its path as `local-work-item:<path>`.
- Story file: prefer the story's `**Work Item**` field when it's set; otherwise
  create or update `docs/superpowers/work-items/<story-slug>.md` and, if editing
  the story is in scope for this run, write that path back into the story.
- External ticket with adapter receipt: create or update a local work item and
  store the adapter key or URL in `**External Ticket**`.
- External ticket without adapter: create or update a local work item with
  `**External Ticket**: ticket-unresolved:<id>`.
- Free-form or greenfield input: create or update a local work item using a
  stable kebab-case slug derived from the goal.

Whenever a local work item is created or updated, do all of the following:

1. Write the canonical file at `docs/superpowers/work-items/<id-or-slug>.md`.
2. Copy or summarize it to `<run_dir>/work-item.md`.
3. Append whichever of `work_item.created`, `work_item.transitioned`,
   `work_item.linked_artifact`, `work_item.adapter_receipt`, or
   `work_item.adapter_warning` applies to
   `docs/superpowers/work-items/work-item-events.jsonl`.
4. Append that same run-relevant event to `<run_dir>/work-item-events.jsonl`.
5. Link `<run_dir>/requirements.md` from the work item's `## Linked Artifacts`
   and `## History`.
6. When the source has no resolved external ticket, record external sync as
   `pending` in local history, so that `sdlc-pipeline` can later emit
   `prepare_for_development` once the branch guard passes.

## Free-form funnel

Treat `raw_input` as the goal itself. First create or update a local work item
and use that path as the requirements `Source` (`local-work-item:<path>`).
Writing the normalized doc is how understanding gets confirmed here; any
remaining ambiguity is left for the pipeline's downstream
`requirements.ambiguous` gate to surface.

## Story-file funnel

Read the story file and pull out its title, story, background, acceptance criteria, out-of-scope items, open questions, and ticket field where one exists. External tickets are not created or updated from this funnel.
If the story doesn't already point to a local work item, create or update one.
When no external ticket is available, use the local work item path as the
requirements source alongside the story path.

## Local work-item funnel

Read the local work item and pull out its title, source story/task, acceptance
criteria, linked artifacts, external ticket, and any open history warnings.
External tickets are not created or updated from this funnel either. Write the
run-local mirror to `<run_dir>/work-item.md` and set `Source` to
`local-work-item:<path>`.

## Ticket-adapter funnel

Ticket IDs and URLs get resolved through whichever project ticket adapter is declared in `.agentic/guides/project.md` or a related `.agentic/guides/integration/*` guide.

Where an adapter is configured, call the documented skill, MCP server, command, or tool exactly as that guide describes, and ask it for summary, description, and acceptance criteria.
Save successful lookup receipts using whatever normalized fields the adapter
supplies — external key or URL, state, assignee, warnings, and actions.

If no adapter is configured, that alone should not fail the whole intake. Write requirements straight from the provided ticket ID/URL as the original input, set `Source` to `ticket-unresolved:<id>`, and add an open question: "Ticket lookup adapter is not configured in `.agentic/guides/`."
Also create or update the local work item, recording
`work_item.adapter_warning`, a local history row, and external sync `pending`.

If a configured adapter fails instead, keep going with the local work item: write
requirements from the original ticket ID/URL, append `work_item.adapter_receipt`
with `status: "failed"` to both canonical and run-local ledgers, add a local
history row, and mark external sync `failed`.

## Greenfield funnel

Treat `raw_input` as a project idea and capture it verbatim — the eventual plan's first task will be "set up the project skeleton." No scaffolding happens at this stage.
First create or update a local work item and use
`local-work-item:<path>` as the requirements `Source`.

## Output: `<run_dir>/requirements.md`

```markdown
# Requirements — <run-id>

**Source**: free-form | story:<path> | local-work-item:<path> | ticket:<id-or-url> | ticket-unresolved:<id-or-url> | greenfield
**Work Item**: docs/superpowers/work-items/<id-or-slug>.md
**Original input**: |
  <verbatim raw_input>

## Goal

<one sentence>

## Acceptance Criteria

- <criterion 1>
- <criterion 2>

## Context

<any constraints from the source ticket / user / detected greenfield>

## Open questions

<list of items the requirements.ambiguous gate should surface, or "(none)">
```

## Constraints

- Don't invent acceptance criteria that aren't in the source — put anything missing under "Open questions" instead.
- For greenfield input, skip `npm init`, `git init`, and any other scaffold commands; the skeleton is the pipeline's Phase 6 task list's job.
- A missing external ticket is not a blocker as long as a local work item can be created.
- Keep `<run_dir>/work-item.md` in sync with the canonical local work item at intake time.
- Branch name suggestion: ticket → use ticket id verbatim; greenfield → `feature/<kebab-name>` derived from the goal; free-form → ask the pipeline (HITL) or auto-derive (autonomous).
- **Output contract**: the only files this skill writes are `<run_dir>/requirements.md`, `<run_dir>/work-item.md`, `<run_dir>/work-item-events.jsonl`, `docs/superpowers/work-items/<slug>.md`, and `docs/superpowers/work-items/work-item-events.jsonl`. No other file gets written, copied, or moved — and `design.md`, `plan.md`, `complexity.json`, or any other phase artifact is never produced here.
- **Prior-run isolation**: when a work item's `## Linked Artifacts` or `## History` references paths from a prior run, treat those as read-only documentation context only — never copy, adopt, or reference those files from the current run directory.
