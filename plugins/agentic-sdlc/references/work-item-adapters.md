# Work-item adapters: resolving the ticket backend without hardcoding one

Skills in the SDLC pipeline talk about work items in the abstract. They never
name Jira, GitHub Issues, Azure DevOps, or any other board. Instead they emit
provider-agnostic lifecycle intents and let a project-declared **adapter**
translate those intents into whatever backend the repository actually uses. This
reference is the contract that makes that indirection safe.

Load it with:

```
${CLAUDE_PLUGIN_ROOT}/references/work-item-adapters.md
```

Read it if you author or maintain `requirements-intake`, `product-owner`,
`sdlc-pipeline`, or `release-manager` — or if you are writing an adapter for a
specific project.

> The whole point is decoupling. A skill that hardcodes a ticket API is a skill
> that breaks on the next repo. A skill that emits an intent keeps working
> everywhere, because the translation lives in the project's guides, not in the
> skill.

## The always-available fallback

The pipeline must never stall waiting on an external system. Every run therefore
carries a repository-local work item that is authoritative on its own:

| Path | Role |
| --- | --- |
| `docs/superpowers/work-items/<id-or-slug>.md` | Canonical local work item — the source of truth. |
| `docs/superpowers/runs/<run_id>/work-item.md` | Run mirror kept inside a pipeline run. |
| `docs/superpowers/work-items/work-item-events.jsonl` | Canonical event ledger. A `work-item-events.jsonl` copy is also written at the run-local path. |

When an adapter is absent, misconfigured, or fails, the local item stands in for
the backend with zero loss of flow. External sync is best-effort layered on top,
never a precondition.

## What flows across the boundary

Two versioned data contracts move between a skill and its adapter. Both carry
`schema: 1`.

- **Input object** — one per intent, describing the current state and the
  artifacts produced so far.
- **Receipt object** — returned by the adapter, normalized so the skill never
  has to parse provider-specific responses.

Because tool invocations are stateless, the create call must be
self-contained. Hand the adapter one complete payload — final title, body,
acceptance criteria, labels, links, parent/epic — as an artifact reference. Do
not lean on conversational shorthand like "as drafted" or "approved above"
unless the adapter also supplies a stable conversation/session id that every
step reuses.

### Lifecycle intents

The skill emits one of these; the adapter maps each to its backend.

| Intent | Emitted when |
| --- | --- |
| `prepare_story` | Story approved; canonical local item created or updated. |
| `prepare_for_development` | Intake resolved a local item and the branch guard passed. |
| `prepare_for_review` | The MR/PR URL is known. |
| `record_delivery_audit` | QA gates plus feature verification produced handoff evidence. |
| `complete_or_handoff` | The run or MR hands off to a human, or completes locally. |

### Input object

Required fields: `schema`, `intent`, `mode`, `run_id`, `phase`,
`local_work_item_path`, `run_work_item_path`, `artifacts`, `policy`.

| Field | Values / shape |
| --- | --- |
| `intent` | `prepare_story \| prepare_for_development \| prepare_for_review \| record_delivery_audit \| complete_or_handoff` |
| `mode` | `hitl \| autonomous \| manual` |
| `local_work_item_path` | `docs/superpowers/work-items/<id-or-slug>.md` |
| `run_work_item_path` | `docs/superpowers/runs/<run_id>/work-item.md` |
| `artifacts[]` | `{ kind, path, url, summary }` |
| `artifacts[].kind` | `story \| requirements \| branch_guard \| mr \| qa_report \| verification \| audit \| handoff` |
| `policy` | `dry_run`, `allow_create`, `allow_transition`, `allow_comments`, `on_missing_adapter` (`warn-and-continue`), `on_adapter_error` (`warn-and-continue`) |

An adapter may ignore fields it does not need, but it must not require
provider-specific fields beyond those declared in the project's integration
guide.

### Receipt object

Required fields: `schema`, `status`, `work_item`, `actions`, `state`,
`assignee`, `audit_url`, `warnings`.

| Field | Values / shape |
| --- | --- |
| `status` | `succeeded \| pending \| failed \| skipped` |
| `work_item` | `{ external_id, external_url, local_path }` where `local_path` = `docs/superpowers/work-items/<id-or-slug>.md` |
| `actions[]` | `{ type, summary, url }` |
| `actions[].type` | `created \| updated \| transitioned \| commented \| linked \| assigned \| skipped` |
| `state` | `ready \| in_development \| in_review \| verified \| handed_off \| completed \| blocked \| unknown` |

On a successful receipt, copy back into the local metadata: external ticket
id/URL, lifecycle state, assignee (when provided), audit URL (when provided),
and append a history row.

## Verify what you created

Creation is not "fire and assume." After a successful create the adapter must
read the item back and confirm the key-or-URL, the title, and the body. If the
body or acceptance criteria are missing on read-back, return a failed or warning
receipt instead of reporting success. A ticket that exists but lost its content
is a failure, not a completion.

## Resolving which work item you mean

Walk this order and stop at the first hit:

1. A configured external adapter's result, joined to the linked local item.
2. An existing local item located via the story, requirements, run mirror, or
   conversation.
3. A new local item, seeded from a story title, a free-form goal, or an
   unresolved external ticket id.

## Behavior by entry point

**Intake — ticket id/URL present, adapter configured.** Invoke the adapter as
its guide documents. Request title/summary, description, acceptance criteria,
and links/comments.

**Intake — ticket id/URL present, no adapter.** Do not block. Write
`ticket-unresolved:<id>` into the requirements, record an open question,
create or update the local item, and append a warning event.

**Intake — free-form input, no ticket.** Use the local item path as the source.
The requirements source becomes `local-work-item:<path>`.

**Creation — `product-owner`.** Only create or update an external ticket after
the user approves the story file. Before any create attempt, create or update
the local item and log a create/link event. If no adapter is configured at
creation time, the story stays approved locally, the ticket is marked not
configured, and the local item is authoritative. That is a complete handoff
state — not a blocker.

## Failure handling

The default posture is `warn-and-continue`.

| Situation | Ledger entry | Markdown sync marker | Handoff |
| --- | --- | --- | --- |
| Adapter miss (none configured) | append `work_item.adapter_warning` | `pending` | surface warning |
| Adapter error / failed receipt | append `work_item.adapter_receipt` with failed status | `failed` | surface warning |

The event ledger entry names (JSONL) are: `work_item.adapter_warning`,
`work_item.adapter_receipt`, `work_item.created`, `work_item.linked_artifact`.

Markdown markers and literals used in the local item and requirements:

- `ticket-unresolved:<id>`
- `local-work-item:<path>`
- `**External Ticket**: ticket-unresolved:<id>`
- `**Ticket**: Not configured`
- `**External Ticket**` — updated from the receipt on success.

## Declaring an adapter

A project declares its adapter in `.agentic/guides/project.md` or in
`.agentic/guides/integration/*.md`, under a "Ticket Adapter" block. Minimum
fields:

| Field | Meaning |
| --- | --- |
| `**Status**` | `configured` or `not configured` |
| `**Adapter**` | the skill / MCP / command / tool name |
| `**Lookup**` | how to fetch an existing item |
| `**Create**` | how to create a new item |
| `**Output**` | the ticket key or URL the adapter returns |

An adapter can be any of those forms — a skill, an MCP server, a command, or a
tool. The declaration is what the pipeline reads; it does not sniff the backend.

## Constraints

- Do not infer the adapter from the shape of a ticket id or URL.
- Do not hardcode a project-specific skill name.
- Do not create tickets before explicit approval.
- Do not require an external ticket when a local item already exists.
- Prefer guide-documented adapters over host defaults.

## Not in scope

- This is not a Jira / GitHub / Azure DevOps client. No provider API shapes are
  defined here.
- The SDLC run never blocks on external sync; sync is best-effort.
- Adapters are never auto-detected from a ticket id or URL shape.
- External tickets are never created without explicit user approval of the story.

## Related

- `mr-adapters.md` — the same indirection for MR/PR platforms. The `mr` artifact
  kind and the `prepare_for_review` intent are the bridge between the two.
- `schemas/` — the versioned shapes for the input and receipt objects.
- Consumers: `requirements-intake` (Lookup contract), `product-owner` (Creation
  contract), `sdlc-pipeline` (emits intents), `release-manager`.
