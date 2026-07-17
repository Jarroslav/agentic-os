# Cursor Implementation Guide

Tool mechanics for running the QE blueprints with Cursor. Read once, then keep as a lookup while you work through any blueprint. Sibling guides in this directory cover other assistants (Claude Code, GitHub Copilot); open the one that matches your tool.

Scope: how to wire blueprint concepts onto Cursor features. Test design, QA method, and process live in the blueprints themselves, not here. Cursor evolves quickly — treat the official docs as the source of truth for exact syntax, especially for hooks.

## Concept map

| Blueprint concept | Cursor mechanism | Blast radius |
|---|---|---|
| Standing instructions / conventions | Rule files in `.cursor/rules/` | R0 |
| Cross-tool instructions | `AGENTS.md` | R0 |
| External system access (browser, tracker, DB) | MCP servers | varies by server |
| Packaged skill / reusable workflow | Custom Mode, manual rule, or MCP-backed rule (no native skill format — see below) | R1–R2 |
| Interactive multi-step work | Agent mode in the composer | R2 |
| Async bulk work | Background Agents | R3 (opens branch/PR) |
| Automated PR review | Bugbot | R3 (posts comments) |
| Session-learned project facts | Memories | R0 |
| Shared scratch briefs | Notepads | R0 |

> Anything tagged R3 must keep a human gate: review Background Agent branches before merge, and treat Bugbot output as advisory. Cursor won't enforce that boundary for you — your review process does.

## Step 1 — Persistent context

Cursor layers instructions from several places. Ranked by preference:

| Layer | Location | Shared? | Notes |
|---|---|---|---|
| Project rules | `.cursor/rules/*.mdc` | yes, versioned | Primary mechanism. Use this. |
| `AGENTS.md` | repo root or subdirectory | yes, versioned | Tool-agnostic; Cursor reads it alongside rules. |
| User rules | Cursor settings | no, personal | Your own habits, not team conventions. |
| Legacy root file | `.cursorrules` | yes | Deprecated single file. Migrate to `.cursor/rules/`. |

Each `.mdc` file opens with YAML frontmatter that controls when it activates:

```markdown
---
description: Test authoring conventions for this repo
globs: ["tests/**", "**/*.spec.ts"]
alwaysApply: false
---
Structure every test as arrange / act / assert...
```

Activation modes and when to pick each:

| Mode | Trigger | Use for |
|---|---|---|
| Always-on | `alwaysApply: true` | Universal conventions that apply to every request |
| Auto-attach | file matching `globs` enters context | Path-scoped guidance — test directories, config files |
| Agent-decided | model reads `description` and opts in | Guidance relevant only in certain situations |
| Manual | you mention `@RuleName` | On-demand workflows you invoke deliberately |

Authoring rules:

- One topic per file. Cursor merges every matching rule into context, so several narrow files beat one broad one — you pay context cost only for what's relevant.
- Ground each rule in facts about this repo (real paths, real fixture locations, real naming). A rule that asserts things the repo doesn't do trains the agent to invent.
- A built-in chat command can draft a starter rule from the current conversation and codebase; use it for a first pass, then trim.

## Step 2 — External connectors (MCP)

MCP servers give the agent tools beyond the repo: browsers, issue trackers, databases.

Two config scopes:

| Scope | File | Commit it? |
|---|---|---|
| Project | `.cursor/mcp.json` | yes — the team shares it |
| User | `~/.cursor/mcp.json` | no — personal servers only |

Three transports: `stdio` (local process, `command` + `args`), SSE (remote `url`), and streamable HTTP (remote). Reference secrets through environment interpolation rather than literals:

```json
{
  "mcpServers": {
    "tracker": {
      "url": "https://tracker.example.com/mcp",
      "env": { "TRACKER_TOKEN": "${TRACKER_TOKEN}" }
    }
  }
}
```

After saving, open Cursor settings to confirm each server is detected and toggle it on.

> Safety: an MCP server executes with your permissions. Get organizational sign-off before enabling one, and audit its source first. A server exposing write tools against an external system is R3 territory — reference it only from a manual rule so it never fires implicitly.

## Step 3 — Executing work

**Agent mode** is the composer default: it plans multi-step work, edits across files, runs terminal commands, and calls MCP tools. This is where you run most blueprint exercises interactively.

**Custom Modes** wrap the agent in a constrained persona: a name, an icon, a model choice, an enabled-tool allowlist, and persona instructions. Switch between them from the composer. Give each mode one responsibility — a mode that both writes tests and reviews security drifts on both jobs. Match model tier to the work: economy for mechanical edits, standard for routine generation, premium for reasoning-heavy planning or review.

| Example mode | Constraint | Suggested tier |
|---|---|---|
| QA agent | may edit test files only, never production code | standard |
| Security reviewer | read-only, no edits | premium |
| Docs writer | no terminal access | economy |

**Background Agents** run without you: an isolated cloud VM clones the repo, executes the task end-to-end, and hands back a branch or PR. Trigger from the composer, a Slack mention, or a GitHub issue/PR. Reach for them when the task is long and non-interactive — bulk test generation, wide refactors, dependency bumps. Because the output lands as a branch/PR (R3), the merge review is your gate.

**Bugbot** is a hosted reviewer that reads your project rules plus repo context and leaves inline PR comments with proposed fixes. Enable it per repository from the dashboard. It complements, never replaces, human review.

Routing summary:

| Need | Use |
|---|---|
| Interactive multi-file task | Agent mode |
| Constrained persona or restricted tool set | Custom Mode |
| Long-running, non-interactive, parallelizable | Background Agent |
| Automatic first-pass PR review | Bugbot |
| One-line or single-block edit | tab completion / composer inline edit — an agent run is overkill |

## No skill packages — three substitutes

Cursor has no packaged-skill primitive. When a blueprint says "install skill X", translate:

1. **Custom Mode** — when the skill is really a persona with a tool boundary.
2. **Manual rule** — when the skill is a procedure; write it as an `.mdc` with manual activation and invoke it by `@`-mention, slash-style.
3. **MCP server + manual rule** — when the skill needs an external system; the server carries the capability, the rule carries the procedure that uses it.

Skill content published for other ecosystems adapts the same way: fold the instructions into a rule, or stand up the tooling as an MCP server.

## Supporting features

- **Hooks** — shell commands wired around agent lifecycle events: lint after edits, block dangerous commands, inject context. The spec is still moving; check current docs before depending on it.
- **Memories** — facts Cursor learns about the project across sessions. Good for context that shouldn't be committed as a rule; audit them occasionally.
- **Notepads** — shared scratch documents you can `@`-mention into any conversation. Useful for a test-charter brief the whole team references.
- **`@`-mentions** — pull files, folders, docs, web pages, git history, or rules into context explicitly instead of hoping the agent finds them.

## QA starter pack

| Item | Why | Where |
|---|---|---|
| Playwright MCP server | drives a real browser — open pages, screenshot, assert, generate selectors; foundation for exploratory and regression exercises | `microsoft/playwright-mcp` |
| GitHub MCP server | read/write issues and PRs — pull bug context in, post triage notes, link tests to tickets | `github/github-mcp-server` |
| Filesystem / DB MCP | inspect seed data, fixtures, and logs without shelling out — add only if needed | `modelcontextprotocol/servers` |
| "QA Agent" Custom Mode | keeps the agent inside test files and out of production code | build in settings |
| Testing-conventions rule | auto-attaches on test globs; records arrange/act/assert structure, fixture locations, naming | write it yourself |

Companion: the Playwright CLI records sessions and generates/inspects selectors — pair it with the Playwright MCP server when building browser suites.

## Setup order

1. Write one conventions rule (always-on).
2. Add path-scoped rules for your test directories (auto-attach).
3. Add `AGENTS.md` if other tools share the repo.
4. Configure MCP — project file for team servers, user file for personal ones.
5. Build the Custom Modes you need.
6. Browse community catalogs for rules and servers worth adopting.
7. Layer on Background Agents and Bugbot once the interactive loop works.

## Community sources

The ecosystem trades in rules and MCP servers, not skill packages:

- **cursor.directory** — curated rules and MCP servers organized by stack.
- A large community repository of example rules.
- The official MCP server catalog.
- Anthropic's public skills repository — content adaptable into rules per the substitutes above.
- Copilot-ecosystem "awesome" lists — instruction files that port to rules with little change.

## Out of scope

Pricing, licensing, account setup, and model selection. This guide also doesn't mandate servers beyond the starter pack — treat filesystem/DB access as opt-in. For anything version-sensitive, the official Cursor documentation wins over this page.
