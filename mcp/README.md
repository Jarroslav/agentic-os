# agentic-os-mcp

<!-- mcp-name: io.github.Jarroslav/agentic-os -->

Read-only MCP server for the agentic-os methodology: governance
(**agentic-os**), the SDLC pipeline (**agentic-sdlc**), and Quality
Engineering blueprints (**agentic-qe**).

It serves documents, not actions. Every tool is read-only — the server never
writes to your repository. Your assistant performs the file writes itself, so
you review each one.

## Install

> **Not yet published.** `agentic-os-mcp` is not on npm yet — publishing is a
> later phase of this project (see `RELEASE.md`). The one-click links,
> badges, and `npx -y agentic-os-mcp` commands below are the shape the
> install will take once it ships; clicking or running them today will
> either fail or resolve to an unrelated package of the same name. **This
> caveat, and only this caveat, is removed by a follow-up commit once the
> first release actually lands** — the snippets themselves are meant to be
> correct in advance, not placeholders to rewrite later. Until then, point
> your host at the local build instead:
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

VS Code — one-click:

[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect?url=vscode%3Amcp%2Finstall%3F%257B%2522name%2522%253A%2522agentic-os%2522%252C%2522command%2522%253A%2522npx%2522%252C%2522args%2522%253A%255B%2522-y%2522%252C%2522agentic-os-mcp%2522%255D%257D)

<!--
  The badge above uses the https://insiders.vscode.dev/redirect?url=... form,
  not a bare `vscode:` href — GitHub's markdown sanitizer strips custom URI
  schemes from rendered links, which makes a `vscode:`/`cursor://` href
  inert on the rendered README even though it works when pasted into a
  browser address bar directly. The redirect form is what VS Code's own
  ecosystem (and other MCP servers' READMEs) uses for exactly this reason.
  It double-encodes: the inner `vscode:mcp/install?{json}` link is itself
  URL-encoded as the outer redirect's `url=` value. Decodes to:
  vscode:mcp/install?{"name":"agentic-os","command":"npx","args":["-y","agentic-os-mcp"]}
-->

or from the command line:

    code --add-mcp '{"name":"agentic-os","command":"npx","args":["-y","agentic-os-mcp"]}'

Cursor — one-click:

[![Add to Cursor](https://img.shields.io/badge/Cursor-Add_MCP-000000?style=flat-square)](https://cursor.com/en/install-mcp?name=agentic-os&config=eyJjb21tYW5kIjoibnB4IC15IGFnZW50aWMtb3MtbWNwIn0%3D)

<!--
  Same reasoning as the VS Code badge above: cursor.com/en/install-mcp is
  Cursor's own https redirect form, replacing the bare `cursor://` deeplink
  that GitHub's sanitizer would strip. `config` is base64 of a single JSON
  object with the whole command line in one "command" string (this is
  Cursor's own convention for this endpoint, not this server's cursor-deeplink
  format) -- decodes to: {"command":"npx -y agentic-os-mcp"}
-->


or add to `.cursor/mcp.json` directly, same as Claude Desktop's
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
the host," not as a failure. `host_must_run` is never empty on a single
server-side call, so this server alone never returns `"passed"`.

**A host that automatically runs `host_must_run`'s commands writes to the
target repo, even though the server itself never does.** Two of the three
command sets do: `dry_runs` creates `.agentic/agents/__agentic_doctor_probe__.md`
(a one-line dummy contract, to exercise `instruction_gate.py`'s
never-graded case) and deletes it in the next command, unconditionally;
`hitl_smoke` creates a temporary working directory outside the target repo
(via `mktemp -d`) holding synthetic transcript files, removed automatically
on exit by a shell `trap`. Both are the doctor's real, documented
procedure — nothing here is left behind — but it means the "read-only"
claim above is a property of this server's own code, not of what happens
if a host executes what `run_doctor` hands back. See each `host_must_run`
entry's `why` field for the exact commands.

## Resources

31 `agentic-os://skills/<plugin>/<skill>` resources, one per `SKILL.md`
across the three plugins, plus a resource template,
`agentic-os://file/{+path}`, that serves any other file shipped by a plugin
that is tracked in `content-index.json` — not just markdown, JSON, or text:
template sources (`.md.tmpl`/`.json.tmpl`/`.py.tmpl`), plain hook scripts
(`.py`/`.sh` and six extensionless git hooks), and a long tail of one-off
files (`sdlc.html`, `scaffold.ps1`, `run-hook.cmd`, `.ts`/`.mts` sources,
`.shellcheckrc`, `*.md.template` repo-guide templates) are all servable too
(e.g. `agentic-os://file/agentic-sdlc/agents/guide-sync.md`). Index
membership is the entire access-control model — see `mcp/src/content.ts`.
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

## Releasing

Maintainer-only. See [RELEASE.md](RELEASE.md) for the one-time setup and
per-release runbook.

## Requirements

Node **>= 20**.

## Build & test

```bash
npm install
npm run build   # build:content (indexes plugins/ + copies dist/content) + build:ts
npm test        # vitest — requires the build above, since the content layer reads dist/content
```
