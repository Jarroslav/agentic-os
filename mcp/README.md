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
| `plan_install` | Compose one or more role presets into an ordered file manifest (a plan; you perform the writes). |
| `run_doctor` | Audit an agentic-os install in a target repo you name. |

The tool surface is deliberately capped at 8 tools. Agent tool-selection accuracy degrades sharply as the number of available tools grows — research shows the performance cliff occurs around 30–40 tools, and real deployments (e.g., GitHub's MCP server) report measurable gains (2–5 points on SWE-Lancer and SWEbench-Verified, plus ~400ms lower latency) after cutting from ~40 tools to 13. The current surface exposes seven tools, one short of the cap.

### `run_doctor`'s split verdict

`run_doctor` audits `.agentic/agentic-os/install.json` and the files it
journals in a target repo you name, through a reader (`mcp/src/target.ts`)
gated by root containment rather than the bundle's build-time index — see
[SECURITY.md](../SECURITY.md) for exactly how that gate works and the one
accepted risk it documents. It verdicts what it can inspect natively as
plain file reads, and returns everything else as `host_must_run`: exact
commands for three checks that require executing Python (hook
compile+import, canned-event dry-runs, HITL smoke) — the server never runs
them itself.

Because of that split, **`verdict: "incomplete"` is the expected,
correct result of a server-side-only run**, not a sign that something went
wrong. `verdict` is `"passed"` only when every native check passed *and*
`host_must_run` is empty (i.e., your host actually ran the returned
commands and folded their results back in); it is `"incomplete"` whenever
`host_must_run` still has entries, and `"failed"` only when a native check
itself found a real problem. A reader who sees `"incomplete"` on its own
should read it as "native checks passed; three checks are still owed to
the host," not as a failure.

## Resources

31 `agentic-os://skills/<plugin>/<skill>` resources, one per `SKILL.md`
across the three plugins, plus a resource template,
`agentic-os://file/{+path}`, that serves any other markdown, JSON, or text
file shipped by a plugin (e.g. `agentic-os://file/agentic-sdlc/agents/guide-sync.md`).
The template is the primary integration point for clients that want to reach
content beyond the curated skill list.

Two families of shorter canonical aliases resolve to the same content:
`agentic-os://presets/{role}` for a role preset and
`agentic-os://qe/blueprints/{stage}/{id}` for a QE blueprint. `list_presets`
and `list_qe_blueprints` return these aliases as each item's `uri`, and
`search_methodology` returns the blueprint alias for a blueprint hit — it
searches markdown documents only, so a preset (JSON) can never be a
`search_methodology` result in the first place. Both alias forms, and the
plain `file/` form, always resolve via `get_document` or a direct resource
read.

## Prompts

`agentic-init`, `agentic-doctor`, `agentic-upgrade`, `sdlc-start`,
`sdlc-task`, `qe-blueprint-scaffold`.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Requirements

Node **>= 20**.

## Build & test

```bash
npm install
npm run build   # build:content (indexes plugins/ + copies dist/content) + build:ts
npm test        # vitest — requires the build above, since the content layer reads dist/content
```
