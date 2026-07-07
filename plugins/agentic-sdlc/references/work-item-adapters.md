# Work Item Adapters

Work-item lookup and ticket creation are adapter-driven. agentic-sdlc must not
hardcode Jira, GitHub, Azure DevOps, or any project-specific skill name.
When no adapter is configured, repository-local work items under
`docs/superpowers/work-items/` are the fallback source of truth.

## Lifecycle Intent Contract

agentic-sdlc emits provider-agnostic lifecycle intents. Adapters translate these
intents into provider-specific ticket, issue, board, comment, audit, or workflow
operations. Skills must never call a provider-specific operation directly unless
that operation is the adapter declared by project guides.

Lifecycle intents:

- `prepare_story` — after a story is approved and a canonical local work item is
  created or updated. The adapter may create or update an external work item,
  sync acceptance criteria, and return the external key or URL.
- `prepare_for_development` — after requirements intake resolves a local work
  item and the branch guard has passed. The adapter may move the external work
  item into a development-ready state, assign an owner, and record the branch.
- `prepare_for_review` — after an MR/PR URL is known. The adapter may attach the
  review URL, transition the work item to review, or add reviewer metadata.
- `record_delivery_audit` — after QA gates and feature verification produce
  handoff-ready evidence. The adapter may attach audit evidence, verification
  summaries, or release notes.
- `complete_or_handoff` — when the SDLC run or MR workflow hands off to a human
  or completes locally. The adapter may transition to done, ready-to-merge,
  blocked, or handoff states according to project policy.

## Lifecycle Adapter Input

For lifecycle intents, skills pass one structured input object to the configured
adapter:

```json
{
  "schema": 1,
  "intent": "prepare_story | prepare_for_development | prepare_for_review | record_delivery_audit | complete_or_handoff",
  "mode": "hitl | autonomous | manual",
  "run_id": "<run id or null>",
  "phase": 1,
  "local_work_item_path": "docs/superpowers/work-items/<id-or-slug>.md",
  "run_work_item_path": "docs/superpowers/runs/<run_id>/work-item.md",
  "artifacts": [
    {
      "kind": "story | requirements | branch_guard | mr | qa_report | verification | audit | handoff",
      "path": "<repo-relative path or null>",
      "url": "<external url or null>",
      "summary": "<single-line summary>"
    }
  ],
  "policy": {
    "dry_run": false,
    "allow_create": true,
    "allow_transition": true,
    "allow_comments": true,
    "on_missing_adapter": "warn-and-continue",
    "on_adapter_error": "warn-and-continue"
  }
}
```

Required fields are `schema`, `intent`, `mode`, `run_id`, `phase`,
`local_work_item_path`, `run_work_item_path`, `artifacts`, and `policy`.
Adapters may ignore fields they do not need, but they must not require
provider-specific fields outside the declared project integration guide.

## Normalized Receipt Schema

Adapters return a normalized receipt object. Skills persist the receipt in the
canonical work item, the run-local work item when present, and the applicable
event ledger.

```json
{
  "schema": 1,
  "status": "succeeded | pending | failed | skipped",
  "work_item": {
    "external_id": "<provider key or null>",
    "external_url": "<provider url or null>",
    "local_path": "docs/superpowers/work-items/<id-or-slug>.md"
  },
  "actions": [
    {
      "type": "created | updated | transitioned | commented | linked | assigned | skipped",
      "summary": "<single-line summary>",
      "url": "<provider url or null>"
    }
  ],
  "state": "ready | in_development | in_review | verified | handed_off | completed | blocked | unknown",
  "assignee": "<provider assignee or null>",
  "audit_url": "<audit artifact url or null>",
  "warnings": ["<warning text>"]
}
```

Required receipt fields are `schema`, `status`, `work_item`, `actions`,
`state`, `assignee`, `audit_url`, and `warnings`.

## Warning and Failure Behavior

Missing or failing adapters are non-blocking by default. The skill that emits
the lifecycle intent must:

1. Continue the local SDLC flow.
2. Append a local work-item history row describing the skipped or failed
   external sync.
3. Append `work_item.adapter_warning` for a missing adapter, or
   `work_item.adapter_receipt` with `status: "failed"` for an adapter failure,
   to the canonical and run-local work-item JSONL ledgers when available.
4. Mark external sync in the Markdown work item as `pending` when no adapter is
   configured, or `failed` when the adapter returns an error or failed receipt.
5. Surface the warning in the user-facing handoff.

An adapter success updates local external ticket metadata from the normalized
receipt: `**External Ticket**`, linked external URL, lifecycle state, assignee
when provided, audit URL when provided, and a history row summarizing actions.

## Adapter Declaration

Projects declare adapter behavior in `.agentic/guides/project.md` or a related
`.agentic/guides/integration/*.md` guide.

Minimum contract:

```markdown
## Ticket Adapter

**Status**: configured | not configured
**Adapter**: <skill, MCP server, command, or tool name>
**Lookup**: <how to fetch an existing work item>
**Create**: <how to create a work item from a story file>
**Output**: <ticket key or URL returned by the adapter>
```

## Lookup Contract

`requirements-intake` may receive an external ticket ID or URL. If an adapter is
configured, it invokes the documented adapter exactly as written and requests:

- title or summary
- description
- acceptance criteria
- relevant links or comments when available

If no adapter is configured, intake MUST NOT block the run. It writes the
original ID/URL into `requirements.md` as `ticket-unresolved:<id>`, records an
open question, and creates or updates a local work item at
`docs/superpowers/work-items/<id-or-slug>.md` with
`**External Ticket**: ticket-unresolved:<id>`. It also appends
`work_item.adapter_warning` to `docs/superpowers/work-items/work-item-events.jsonl`.

If the input is free-form and has no ticket at all, intake treats the local work
item path as the source reference instead of asking for a ticket. The
requirements source should be `local-work-item:<path>` once the local item is
created or linked.

## Creation Contract

`product-owner` creates or updates an external ticket only after the story file
is approved by the user. If an adapter is configured, it passes the story file
path and records the returned key or URL in the story.

Before any external ticket creation attempt, `product-owner` MUST create or
update the local work item, link the approved story path, and append
`work_item.created` or `work_item.linked_artifact` to the local event ledger.

If no adapter is configured, the story remains approved locally with
`**Ticket**: Not configured` and the local work item remains authoritative. This
is a complete handoff state, not a blocker.

Story approval emits the `prepare_story` lifecycle intent. The adapter input
must include the approved story file as an artifact and the canonical local work
item path. The normalized receipt drives all local metadata updates;
provider-specific response shapes must be converted before they are stored.

Ticket creation adapters must be safe across stateless tool invocations. The
create operation must receive one complete payload or artifact reference that
contains the final title, description/body, acceptance criteria, labels, links,
and parent/epic metadata needed to create the ticket. Skills must never invoke a
create operation with conversational references such as "as drafted",
"approved above", or "use the previous response" unless the adapter declaration
also provides a stable conversation/session id and the same id is used for every
step in that flow. When a conversational adapter is the only available adapter,
prefer passing the approved story or local work-item file with the create call.

After a successful create operation, the adapter must read back or otherwise
verify the created ticket's key or URL, title/summary, and description/body. If
the read-back shows the description/body or acceptance criteria are missing, the
adapter must return `status: "failed"` or a warning receipt instead of silently
treating creation as complete.

## Local Work Item Fallback

Skills that need a work item reference resolve in this order:

1. Configured external adapter result, plus a linked local work item.
2. Existing local work item path from the story, requirements, run mirror, or
   conversation.
3. New local work item created from the story title, free-form goal, or unresolved
   external ticket ID.

The local fallback MUST preserve:

- canonical path: `docs/superpowers/work-items/<id-or-slug>.md`
- run mirror when inside a pipeline run: `docs/superpowers/runs/<run_id>/work-item.md`
- event ledgers: `work-item-events.jsonl` at the canonical and run-local paths
- external adapter receipts or warnings as `work_item.adapter_receipt` or
  `work_item.adapter_warning`

## Constraints

- Do not infer an adapter from ticket shape alone.
- Do not hardcode a project-specific skill name.
- Do not create tickets before explicit approval.
- Do not require an external ticket when a local work item exists.
- Prefer guide-documented adapters over host defaults.
