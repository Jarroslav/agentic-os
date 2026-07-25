# Ticket flow: mapping run events to external work-item transitions

This file is the **schema of record** for translating pipeline events into external
work-item (ticket) state changes. It is not the adapter, and it is not read by end
users — it is consumed at knowledge-planting time and again at runtime by a background
hook. Each host repo derives its own concrete instance from the schema described here.

> One direction only: events flow out of a run, and this mapping decides which ticket
> state should result. Nothing here creates tickets, chooses adapters, or drives states
> that some other system already owns.

## The two files

| File | Role |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/references/ticket-flow.md` | Schema source of truth (this document). |
| `.agentic/guides/integration/ticket-flow.md` | Per-host instance, machine-parsed by the hook. Optional. |

The instance is authored into the host repo; the plugin-root copy stays canonical for the
schema. If the instance is absent, the runtime hook does nothing — it is a clean no-op.

`repo-guides` (Step D) offers to write the instance, but only when the host's
`.agentic/guides/project.md` already declares a Ticket Adapter under its `## Ticket
Adapter` heading. This mapping consumes that declaration; it does not restate it. The
`**Adapter**` value you write into the instance MUST match the adapter named in
`project.md`.

## The runtime consumer

The hook `ticket-sync` runs on **Stop** and **SubagentStop**, asynchronously. Those signals
fire constantly, so the hook is built to bail cheaply: when no untracked, eligible
transition is pending it returns in tens of milliseconds without ever touching the
adapter. Only when a row is both triggered and not already satisfied does it shell out.

Two ledgers feed it:

| Ledger | Purpose |
|---|---|
| `events.jsonl` | The current run's event stream — the trigger source. |
| `docs/superpowers/work-items/work-item-events.jsonl` | Canonical work-item ledger — the dedup authority. |

## Instance schema

An instance is a small set of `**Marker**` fields plus one transition table. Required
fields are starred.

| Marker | Value |
|---|---|
| `**Status**` | `configured \| not configured` |
| `**Adapter**` | Adapter name, matching `project.md`. |
| `**Workflow source**` | Human-readable label for where the state names come from. |
| `**Adapter invocation**` * | One-line shell command carrying a `{message}` placeholder. |
| `**Known states**` * | Comma-separated state names, in workflow order. |
| `**Action message template**` * | Body text; substitutes `{ticket_id}` and `{state}`. |
| `**Timeout**` | Seconds to wait on the adapter; default `120`. |
| `**Transitions**` * | Forward-only table in workflow order — columns `When` \| `Set state`. |
| `**Out of scope**` | States this pipeline deliberately does not drive. |

Two of these markers are a **hard parsing contract** — the hook reads them as single
lines and depends on their exact spelling and the literal `{message}` placeholder:

```
**Adapter invocation**: <one-line command that embeds "{message}">
**Known states**: STATE_A, STATE_B, STATE_C
```

Default action message template, used when the instance does not override it:

```
"Transition ticket {ticket_id} to status {state}, then tell me the current status of the ticket."
```

### How the hook talks to the adapter

- **Invocation.** `**Adapter invocation**` is run as a single-line sub-shell. The hook builds
  the message body from `**Action message template**` and substitutes it into the literal
  `{message}` placeholder before executing.
- **Read-back.** The hook parses the adapter's reply by scanning it for any `**Known states**`
  entry appearing as a substring; that tells it the ticket's current state after the call.

## Trigger grammar (the `When` column)

Each transition row matches on one trigger expression:

| Pattern | Fires when |
|---|---|
| `phase.completed phase=<N>` | The run's `events.jsonl` holds a `phase.completed` event for phase N. |
| `work_item.linked_artifact kind=mr` | Either ledger holds `work_item.linked_artifact` with `data.kind: "mr"` for this work item. |
| `feature.verified` | The run's `events.jsonl` holds a `feature.verified` event. |

Patterns the hook does not recognize (typos, unknown events) are skipped silently and never
block the rest of the table.

## How a row is chosen

1. **Last match wins.** Among all rows whose trigger is satisfied, the hook applies the
   **last** matching row in table order. Because the table is authored forward in workflow
   order, a later state can leapfrog an earlier one when several triggers have already
   fired. Author rows forward-only, in workflow order — never out of sequence.
2. **Dedup against the receipt.** The most recent `work_item.adapter_receipt` in the canonical
   ledger is the authoritative current state. A row is skipped when its `Set state` equals
   that receipt's `state` field. The `state` field is the **only** dedup mechanism — there is
   no sidecar file, no correlation id, no added schema.
3. **Failed and pending don't count.** A receipt whose `status` is `failed` or `pending` does
   not satisfy dedup, so the hook retries the transition on the next Stop fire.

Because retries happen across resumes, crashes, and repeated stops, the **adapter must be
idempotent**: re-issuing the same intent against a ticket already in the target state
returns success with no duplicate side effects.

## Default event to state mapping

When an instance does not specify otherwise, the cross-referenced defaults are:

| Trigger | Target |
|---|---|
| `phase.completed phase=2` | A dev / in-progress state. |
| `work_item.linked_artifact kind=mr` | A review state. |
| Neither | No transition — ask explicitly. |

## Worked example — Jira via MCP

Illustrative instance for a Jira board driven through an MCP server:

```
**Status**: configured
**Adapter**: Jira MCP
**Known states**: BACKLOG, DEV, TO REVIEW, TO MERGE, QA, READY FOR PROD, RELEASED
**Adapter invocation**: transition Jira ticket via the Jira MCP server — "{message}"
**Timeout**: 120
```

| When | Set state |
|---|---|
| `phase.completed` phase=2 | DEV |
| `work_item.linked_artifact` kind=mr | TO REVIEW |

Out of scope in this example: `TO MERGE`, `QA`, `READY FOR PROD`, `RELEASED`. These are driven
by reviewer approval, the post-merge QA pipeline, and release tooling respectively — add
rows later if `mr-watch` or an external integration begins emitting matching events.

## Boundaries

- **Not an adapter declaration.** The adapter lives in `project.md` under `## Ticket Adapter`
  (MR/PR skills read `## MR Adapter`). This file is purely the event to state mapping.
- **Transitions only, never creation.** Tickets are created by `product-owner` through the
  `prepare_story` lifecycle intent. The hook moves existing tickets and nothing more.
- **Base pipeline stops at review.** Post-merge, QA, and release states are out of scope
  unless matching events are emitted.
- **One dedup mechanism.** Receipt `state` is the sole guard — no sidecar state, no
  correlation id, no schema additions.

## Related material

- `repo-guides` (SKILL.md) — lists this instance as an optional integration guide and keeps
  it distinct from `integration/external-integrations.md`.
- `repo-audit-guides` — surveys repo docs and assistant setup before knowledge planting.
- `BUNDLE.md` — documents the `ticket-sync` hook that consumes this mapping.
- `product-owner` (`prepare_story`) owns ticket creation; `mr-watch` is a likely future
  emitter of downstream transition events.
