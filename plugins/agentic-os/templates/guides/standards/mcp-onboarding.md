# MCP onboarding for business work

MCP is optional. You can complete requirements and customer work without it by
pasting a table, attaching a CSV, sharing a screenshot, or describing a Power
BI finding.

## Choose the easiest route

1. **Connect now** — use the host's MCP directory or an organization-provided
   connector when one is available.
2. **Configure later** — continue without MCP and return to this guide when IT
   or a connector owner is ready.
3. **Use an existing organization connection** — ask your administrator which
   server is approved and whether it is read-only.

Read-only access is the recommended starting point. Do not put API keys or
tokens in this repository; use OAuth or environment variables instead.

## Cursor

- Project configuration belongs in `.cursor/mcp.json`.
- A personal global configuration belongs in `~/.cursor/mcp.json`.
- Verify with `cursor-agent mcp list`.
- Authenticate with `cursor-agent mcp login <server-name>` when required.
- Confirm available capabilities with `cursor-agent mcp list-tools <server-name>`.

## Claude Code

- Shared project configuration belongs in `.mcp.json`.
- Add a server with `claude mcp add <name> --scope project ...` or
  `claude mcp add-json <name> '<json>'`.
- Verify with `claude mcp list` and `claude mcp get <server-name>`.
- Use `/mcp` for OAuth and approval prompts.

## If setup does not work

Do not block the work. Record the source manually, continue with the same
Portfolio prompts, and retry MCP after access or approval is resolved.

Useful first tasks:

- “Turn this Power BI insight into a customer-ready requirement.”
- “Convert this Excel analysis into acceptance criteria.”
- “Prepare clarification questions for the customer and delivery team.”
