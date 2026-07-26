# BA/PO operating model

This guide is the role-specific entrypoint for business analyst and product
owner work. It delegates execution to the existing `product-owner`,
`requirements-intake`, and work-item adapter contracts. It does not replace
those contracts or create a provider-specific workflow.

## Choose an input path

- **Pasted Excel/Power BI material** — paste a table, attach a CSV, share a
  screenshot, or describe the finding. This path works without MCP.
- **Read-only MCP data** — verify the approved server and visible read tools,
  then cite the connected source in the story context. Do not request write
  access just to read analysis.
- **Existing external ticket** — pass the ticket ID or URL to
  `requirements-intake`; it uses only the adapter declared in
  `.agentic/guides/project.md`.

If MCP is unavailable, denied, or missing the needed tool, continue with the
pasted/manual path. MCP availability is never a blocker for local requirements
work.

## Safe workflow

`input → clarify → local story → local work item → review → approval → adapter sync → read-back → handoff`

1. Clarify the user, problem, desired outcome, scope, and open questions. A
   broad request gets focused questions before a story is drafted.
2. Invoke the existing `product-owner` workflow to explore relevant context,
   draft `docs/stories/<date>-<feature>.md`, and run its review loop.
3. Create or update the canonical local work item under
   `docs/superpowers/work-items/` before any external sync.
4. Present the story, acceptance criteria, open questions, and complete ticket
   payload. Wait for explicit user approval.
5. After approval, emit the provider-agnostic `prepare_story` lifecycle intent
   through the declared adapter. Never call provider-specific APIs directly.
6. Normalize the adapter receipt, read back the created/updated ticket, and
   verify its title, body, and acceptance criteria. Record successful or failed
   receipts as `work_item.adapter_receipt` and warnings as
   `work_item.adapter_warning` in the existing append-only work-item and run
   event ledgers, with a matching local history entry.
7. If the adapter fails or is not configured, keep the approved local story and
   work item authoritative; show the warning, retry instructions, and a manual
   fallback. A failed or unavailable external sync never erases the local
   artifacts or blocks handoff.

Never create or update an external ticket before explicit approval. Never
invent acceptance criteria from missing business context. Never use
conversation-only references such as “the story above” as an adapter payload;
pass the approved story or work-item artifact.

## MCP verification

For Cursor, use the host's approved MCP flow, then verify with
`cursor-agent mcp list` and `cursor-agent mcp list-tools <server-name>`.
For Claude Code, use the host's approved MCP flow, then verify with
`claude mcp list`, `claude mcp get <server-name>`, or `/mcp`.

A configuration file alone does not prove that the server is available or that
the required read tool exists. Keep credentials in OAuth or environment
variables, never in repository instructions, stories, or committed JSON.

## First tasks

- “Turn this Power BI insight into a customer-ready requirement.”
- “Convert this Excel analysis into acceptance criteria.”
- “Prepare clarification questions for the customer and delivery team.”
- “Prepare customer/team clarification questions before the next conversation.”
