# Connector Catalog

Lookup table for wiring QE blueprints to external systems: issue trackers, test management, wikis, repos, browser automation, database schemas, and chat. Every blueprint carries a connector section that names systems and recommended MCP/CLI values; resolve those names against the rows below for the preferred mechanism, auth pointers, and response-trimming techniques.

Check this catalog **before** writing any custom connector skill. Odds are the plumbing already exists one tier up.

## Integration ladder

Pick the highest available tier. Descend only when the tier above does not exist for the system or is blocked by your organization's policy.

| Tier | Mechanism | Descend when |
| --- | --- | --- |
| 1 | Vendor-published MCP server | No official MCP, or policy forbids it |
| 2 | Vendor CLI | No official CLI either |
| 3 | Vendor REST/SDK wrapped as a custom skill | No usable API surface, or required fields missing |
| 4 | Custom build from scratch | Last resort |

> Why this order: an official MCP needs near-zero glue code and hands auth to the platform instead of your scripts. A CLI is the portable fallback — it runs in any shell, including assistant hosts that have no MCP support at all. Everything below tier 2 is code you now own and maintain.

One deliberate inversion exists: Playwright prefers the CLI over the MCP. See [system notes](#playwright-cli-first).

## Catalog

Columns: preferred tier-1 integration, tier-2 CLI, and what the row covers. Read operations through any of these are R0. Writes to an external system (creating issues, posting messages, editing pages) are R3 — keep them behind a human gate.

### Issue trackers

| System | MCP (tier 1) | CLI (tier 2) | Covers |
| --- | --- | --- | --- |
| Jira (Cloud/DC) | Atlassian remote MCP | `acli` | Issues, comments, JQL search, attachments, transitions |
| Azure DevOps Boards | Microsoft ADO MCP (official) | `az boards` | Work items, queries, links, comments |
| GitLab issues | GitLab MCP (official) | `glab` | SaaS and self-managed instances |
| GitHub issues | GitHub MCP server (official) | `gh` | Issues, projects, search |

### Test management

| System | MCP (tier 1) | CLI (tier 2) | Covers |
| --- | --- | --- | --- |
| Xray | Atlassian remote MCP | `acli` | Basic CRUD; drop to REST for advanced run/execution fields |
| Zephyr Scale | Atlassian remote MCP | `acli` | Basic CRUD; drop to REST for execution-cycle specifics |
| Azure Test Plans | Microsoft ADO MCP | `az boards` | Plans, suites, points, results |

### Wikis and documentation

| System | MCP (tier 1) | CLI (tier 2) | Covers |
| --- | --- | --- | --- |
| Confluence | Atlassian remote MCP | `acli` | Pages, spaces, attachments, labels |
| ADO Wiki | Microsoft ADO MCP | `az` | Co-located with Boards/Repos tooling |
| GitHub wiki / in-repo markdown | GitHub MCP server | `gh` | Handled as a repo connector |
| Miro | Miro MCP (official) | — (no official CLI) | Architecture and whiteboard parsing; fallback: local PDF export of the board |

If the team's docs live as markdown files inside a repository, do not look for a wiki connector — treat it as a repo-connector need and use the matching row below.

### Repositories and code review

| System | MCP (tier 1) | CLI (tier 2) | Covers |
| --- | --- | --- | --- |
| GitHub repos/PRs | GitHub MCP server | `gh` | Repos, PRs, reviews, releases |
| GitLab repos/MRs | GitLab MCP | `glab` | Repos, MRs, pipelines; a repo-local skill can wrap `glab` for self-managed hosts |
| Azure Repos | Microsoft ADO MCP | `az repos` | Shared with the Boards tooling |

### Browser automation

| System | MCP | CLI | Covers |
| --- | --- | --- | --- |
| Playwright | Playwright MCP | Playwright CLI | **CLI preferred** — see system notes |

### Database schemas

| System | MCP (tier 1) | CLI (tier 2) | Covers |
| --- | --- | --- | --- |
| Postgres / MySQL schemas | Community postgres/mysql MCPs | Native DB CLIs | Read-only schema fetch for test-data generation |

### Chat and notifications

| System | MCP (tier 1) | CLI (tier 2) | Covers |
| --- | --- | --- | --- |
| Slack | Slack MCP (official) | Slack CLI / incoming webhooks | Use a webhook for simple posts; skip the full MCP |

## System notes

### Atlassian remote MCP

One hosted server covers Jira, Confluence, Xray, and Zephyr — the last two are implemented as Jira issue types, so no separate connector exists or is needed.

- Endpoint: single remote SSE service at `mcp.atlassian.com/v1/sse`. Nothing to install locally; no API token to store.
- Auth: browser OAuth. The first tool invocation opens the approval flow.
- Claude Code registration: add the server with the `mcp add` command using SSE transport, then confirm it appears in `mcp list`. Exact syntax per assistant lives in the platform guides (see cross-references).

Known gap: execution-cycle data — test runs, executions, results — is incompletely exposed for Xray and Zephyr. For those fields, wrap the vendor REST API in a small custom skill (tier 3). Keep the MCP for everything else.

### Playwright: CLI first

The ladder inverts here. Default to the Playwright CLI for locator discovery and test code generation: it is faster, cheaper in tokens, and matches the vendor team's own guidance. Reserve the Playwright MCP for live, agent-driven browser control — interactive sessions where the agent must observe and react to a running page.

### Database schemas: read-only by design

Scope database connectors to schema reads only. The use case is grounding test-data generation in real column names and types — not querying or mutating data. Grant read-only credentials; the connector stays R0.

### Slack: webhook over MCP

For fire-and-forget notifications ("gates passed", "run complete"), an incoming webhook is one HTTP POST and zero connector overhead. Bring in the full Slack MCP only when the agent must read channels or threads. Either way, an outbound post is R3 — gate it.

### Miro: PDF fallback

Miro publishes an MCP but no CLI, so tier 2 is empty. Where the MCP is unavailable or blocked, export the board to PDF locally and feed the file to the agent as static input.

## Trimming connector responses

> Raw tracker JSON is the largest hidden context cost in QE flows. A single issue payload drags along changelogs, rendered rich-text duplicates, avatar URLs, and dozens of custom fields the agent never reads. Select fields, paginate with small limits, and project the response *before* it reaches the model.

Rules:

1. Always pass a field selector and a small page size — never fetch default payloads in bulk.
2. If an MCP offers no field restriction, pipe its output through `jq` or a short Python projection that keeps only the keys the agent actually uses.
3. Think rows vs. columns: the query language picks rows; the field list picks columns. Set both.

Per-connector projection techniques:

| Connector | Technique |
| --- | --- |
| Jira REST / `acli` | `fields` parameter (`summary,status,priority,components,labels,assignee`) plus a small `maxResults`. JQL selects rows, `fields` selects columns. Strip rendered rich-text fields entirely. |
| `gh` | `--json` with an explicit key list plus `--limit` — projection is built in. |
| `az` | `--query` with a JMESPath expression projecting title/state before anything prints. |
| `glab` | Emit JSON and pipe through `jq` selecting title/state/labels. |

Full rationale and additional patterns: `../agent_design/token_efficiency.md`.

## Decision rules

- Catalog first: never start a custom connector skill without checking for a tier-1 or tier-2 row here.
- Tier top-down: official MCP → official CLI → wrapped REST/SDK → custom from scratch.
- Xray/Zephyr: Atlassian MCP for basic CRUD; REST wrapper for execution-cycle fields.
- Playwright: CLI by default; MCP only for real-time interactive browser control.
- Markdown docs in a repo: use the repo connector, not a wiki connector.
- Unrestrictable MCP output: project it externally (`jq` / Python) before it enters context.
- Reads are R0 and safe to automate; any connector write to an external system is R3 and stays behind a human gate.

## Cross-references

- Blueprint connector sections (under `blueprints/`) name systems that resolve to rows in this catalog.
- `../agent_design/token_efficiency.md` — the full case for response trimming.
- Platform wiring differs per assistant; use the matching guide:
  - `tool_guides/claude_code.md` — MCP config, project skills, sub-agents
  - `tool_guides/cursor.md` — `mcp.json`, rules
  - `tool_guides/github_copilot.md` — VS Code MCP config, custom agents

## Out of scope

- Step-by-step install tutorials for any single MCP or CLI — the platform guides own that.
- Unofficial or community connectors, except the DB-schema MCPs listed above.
- Test strategy and blueprint content — this document is integration plumbing only.
- Credential management beyond noting OAuth-vs-token characteristics per row.
