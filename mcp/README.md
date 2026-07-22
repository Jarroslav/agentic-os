# agentic-os-mcp

<!-- mcp-name: io.github.jarroslav/agentic-os -->

Read-only MCP server for the agentic-os methodology: governance
(**agentic-os**), the SDLC pipeline (**agentic-sdlc**), and Quality
Engineering blueprints (**agentic-qe**).

It serves documents, not actions. Every tool is read-only — the server never
writes to your repository. Your assistant performs the file writes itself, so
you review each one.

## Install

> **Not yet published.** `agentic-os-mcp` is not on npm yet — publishing is a
> later phase of this project. The `npx -y agentic-os-mcp` commands below are
> the shape the install will take once it ships; running them today will
> either fail or resolve to an unrelated package of the same name. Until then,
> point your host at the local build instead:
>
> ```bash
> claude mcp add agentic-os -- node /absolute/path/to/mcp/dist/index.js
> ```
>
> Build the local server first with `npm run build` from `mcp/`, and use an
> absolute path — relative paths are not reliably resolved by every host.

Claude Code:

    claude mcp add agentic-os -- npx -y agentic-os-mcp

Codex:

    codex mcp add agentic-os -- npx -y agentic-os-mcp

VS Code:

    code --add-mcp '{"name":"agentic-os","command":"npx","args":["-y","agentic-os-mcp"]}'

Cursor or Claude Desktop — add to `.cursor/mcp.json` or
`claude_desktop_config.json`:

    { "mcpServers": { "agentic-os": { "command": "npx", "args": ["-y", "agentic-os-mcp"] } } }

## Tools

| Tool | Purpose |
| --- | --- |
| `search_methodology` | Find the right document. Start here. |
| `get_document` | Fetch one document by its `agentic-os://` URI. |
| `list_presets` | List the agentic-os role presets with HITL default, orchestration mode, and SDLC skills. |
| `list_qe_blueprints` | List the agentic-qe Quality Engineering blueprints, filterable by STLC stage. |
| `list_sdlc_phases` | List the agentic-sdlc pipeline phase map with its judgment gates. |

## Resources

31 `agentic-os://skills/<plugin>/<skill>` resources, one per `SKILL.md`
across the three plugins, plus a resource template,
`agentic-os://file/{+path}`, that serves any other markdown, JSON, or text
file shipped by a plugin (e.g. `agentic-os://file/agentic-os/presets/roles/developer.json`).
The template is the primary integration point for clients that want to reach
content beyond the curated skill list.

Two families of shorter canonical aliases resolve to the same content:
`agentic-os://presets/{role}` for a role preset and
`agentic-os://qe/blueprints/{stage}/{id}` for a QE blueprint. `list_presets`
and `list_qe_blueprints` return these aliases as each item's `uri`, and
`search_methodology` returns whichever form applies to a given result — both
forms always resolve via `get_document` or a direct resource read.

## Prompts

`agentic-init`, `agentic-doctor`, `agentic-upgrade`, `sdlc-start`,
`sdlc-task`, `qe-blueprint-scaffold`.

## Requirements

Node **>= 20**.

## Build & test

```bash
npm install
npm run build   # build:content (indexes plugins/ + copies dist/content) + build:ts
npm test        # vitest — requires the build above, since the content layer reads dist/content
```
