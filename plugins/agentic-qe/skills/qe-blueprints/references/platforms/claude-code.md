# Claude Code — platform guide for QE blueprints

Read this once, then implement any blueprint in the suite on Claude Code. Blueprints describe *what* to build (roles, gates, artifacts); this page describes *how* Claude Code's primitives work so you can wire a blueprint onto them. Sibling guides in this directory cover other assistants (Cursor, GitHub Copilot) — pick the one matching your tool.

**Audience:** QA engineers who can edit repo files, run CLI commands, and commit configuration.

**Out of scope:** test methodology, any specific blueprint's workflow, other assistants' setup, deep SDK API reference. Follow the links at the bottom for depth.

---

## 1. Primitive map

| Primitive | Lives in | What it gives you | Typical blast radius |
|---|---|---|---|
| Memory files | repo root, subdirs, home dir | Persistent context loaded every session | R0 |
| MCP servers | `.mcp.json` / user config | Connectors to trackers, test management, DBs | R0–R3 (depends on server) |
| Skills | `.claude/skills/<name>/SKILL.md` | Auto-invoked reusable workflows with bundled assets | inherits session |
| Sub-agents | `.claude/agents/<name>.md` | Isolated single-responsibility workers with tool allowlists | you set it via allowlist |
| Hooks | `.claude/settings.json` | Shell commands on lifecycle events (lint, block, inject) | R1–R2 |
| Slash commands | `.claude/commands/<name>.md` | Parameterized prompt shortcuts | inherits session |
| Headless / SDK | pip / npm package, `claude -p` | Same stack, no interactive session — CI, cron, batch | as configured |
| Plugins | marketplace via `/plugin` | Skills + agents + commands + hooks in one installable unit | as declared |

> Decision rules, in order: (1) search marketplaces first — install beats build; (2) if an approved connector to an external system exists or can be built, use MCP; (3) if MCP is unavailable or unapproved, or the need is a self-contained workflow, write a skill; (4) if the job runs unattended or on a schedule, go headless.

---

## 2. Persistent context (memory)

Claude Code merges several memory sources each session. Deepest file nearest the working directory wins on conflict; all applicable layers combine.

| Layer | Location | Committed? | Use for |
|---|---|---|---|
| User-global | home config dir | no | Personal defaults across all repos |
| Project root | repo root memory file | yes | Team conventions, build/test commands |
| Project local | gitignored variant at repo root | no | Personal per-repo overrides |
| Nested | per-subdirectory files | yes | Directory-scoped rules (e.g. `tests/` conventions) |
| AGENTS.md | anywhere in tree | yes | Cross-tool instructions; nearest file takes precedence |

Merge order: user-global → repo root → nested, deepest last.

Workflow:

1. Run `/init` once — it scans the codebase and drafts the root memory file (structure, conventions, build commands). Hand-edit the gaps.
2. Put subdirectory-specific rules (test naming, fixture policy, locator strategy) in a nested memory file inside that subdirectory — not in the root file.
3. Prefix any chat line with `#` to persist it to memory on the spot; run `/memory` to open and edit the files.

> Keep memory short and high-signal. Long memory files dilute attention on the actual task. If a rule only applies to one file type or one workflow, move it to a nested file or a skill.

Grounding note: memory is where you pin the facts the assistant must not invent — real command names, real environment URLs, real tracker project keys. If a fact isn't in memory or the repo, expect the model to guess; don't let it.

---

## 3. External connectors (MCP)

MCP servers connect Claude Code to trackers (Jira, Azure DevOps), test management (TestRail, Xray, Zephyr), databases, and browsers.

**Scopes**

| Scope | Where | Shared with team? |
|---|---|---|
| Project | `.mcp.json` at repo root | yes — commit it |
| User | home config file or `claude mcp add` | no |

**Transports:** stdio (local process), SSE, and streamable HTTP (remote). Remote servers may authenticate via OAuth. Config env vars can reference shell variables, so keep secrets out of the committed file:

```json
{
  "mcpServers": {
    "tracker": {
      "type": "http",
      "url": "https://tracker.example.com/mcp",
      "headers": { "Authorization": "Bearer ${TRACKER_API_KEY}" }
    }
  }
}
```

**Safety.** An MCP server runs with your permissions. Before enabling one: confirm organizational approval, and audit the server's source. Treat any server that can create tickets, post comments, or mutate test-management state as R3 — external side-effects belong behind a human gate, so leave those tools out of autonomous flows or require confirmation in front of them.

---

## 4. Skills

A skill is a directory holding a `SKILL.md` with YAML frontmatter (a `name` plus a trigger `description`) and optional bundled scripts and templates. The format follows the Agent Skills open standard (agentskills.io), which makes skills portable between Claude Code and GitHub Copilot.

- Location: `.claude/skills/<skill-name>/`
- Discovery: automatic; Claude self-invokes a skill when the request matches its description. Write the description as trigger phrasing, not marketing copy.
- Installing a community skill: copy its folder into `.claude/skills/` and commit; it's discovered next session.

```yaml
---
name: flaky-test-triage
description: Use when a CI run shows intermittent test failures and the user asks to triage, quarantine, or deflake tests.
---
```

Skeleton:

```
.claude/skills/flaky-test-triage/
├── SKILL.md          # frontmatter + procedure
├── scripts/          # optional helpers the procedure calls
└── templates/        # optional report/output templates
```

---

## 5. Sub-agents

A sub-agent is a Markdown file under `.claude/agents/` whose frontmatter declares `name`, `description`, a tool allowlist, and a model tier. It runs in its own context window and can touch only the tools you list. Scaffold interactively with `/agents`, or write the file directly:

```yaml
---
name: coverage-auditor
description: Analyzes coverage reports and flags untested critical paths. Read-only.
tools: Read, Grep, Glob
model: standard
---
You audit test coverage. Ground every claim in files you actually read;
never invent coverage numbers. Report gaps as a table: path, risk, suggested test.
```

Rules that keep sub-agents safe and cheap:

- **Single responsibility.** One job per agent. A "does everything QA" agent is un-auditable and un-tunable.
- **Minimum tools.** The allowlist is your blast-radius control: read/grep only → R0; add file writes → R2; add an MCP tool that posts to a tracker → R3, so gate it. Grant the least that the job needs.
- **Model tier by workload.** `economy` for retrieval and formatting, `standard` as default, `premium` for reasoning-heavy work (risk analysis, test design from ambiguous requirements).
- Dispatch happens either explicitly via the Agent tool or automatically from the description — so write descriptions that match how users actually phrase requests.

---

## 6. Hooks, slash commands, settings

**Hooks** bind shell commands to lifecycle events: pre/post tool use, prompt submit, stop, subagent stop, session start, notification. Configure in `.claude/settings.json`. QE-relevant patterns:

| Event | Use |
|---|---|
| post tool use (edit) | Auto-lint / format the touched file |
| pre tool use (bash) | Block risky commands (destructive git, prod URLs) |
| prompt submit / session start | Inject context (current sprint, environment) |
| stop | Pre-commit validation before the session hands work back |

**Slash commands** are reusable prompts stored as `.claude/commands/<name>.md`, invoked as `/<name>`; an arguments placeholder lets one file serve many inputs. Use them for prompts you repeat verbatim (e.g. "draft regression notes for release X").

**Settings** also carry permission allowlists (pre-approve safe commands to cut prompt fatigue), output style, and the status line. Long bash or agent work can run in the background.

---

## 7. Headless and CI

Everything above — tools, MCP, skills, agents — works identically outside interactive sessions:

| Path | Entry point | Fits |
|---|---|---|
| Python SDK | `pip install claude-agent-sdk` | Schedulers, custom harnesses |
| TypeScript SDK | `npm install @anthropic-ai/claude-agent-sdk` | Node-based pipelines |
| CLI one-shot | `claude -p "<prompt>"` with streaming JSON output | CI steps, cron, quick batch jobs |

Choose this path whenever a blueprint calls for autonomous or scheduled multi-step runs (nightly triage, scheduled report generation). In unattended runs, be strict about blast radius: R0/R1 freely, R2 only onto branches, R3 never without a human gate.

---

## 8. Plugins and marketplaces

Plugins bundle skills, agents, commands, and hooks into one installable package, distributed through marketplaces and managed via `/plugin`. Before authoring anything, search these sources:

| Source | What's there |
|---|---|
| Official Anthropic skills repo (GitHub) | Maintained first-party skills |
| skills.sh | Community skill index |
| awesome-claude-code (curated list) | Skills, commands, workflow references |
| GitHub's awesome-copilot skills | Format-compatible; usable as-is |

### QA starter kit

| Item | Type | Why install it |
|---|---|---|
| skill-creator | meta-skill | Scaffolds new skills correctly; install once per repo before authoring |
| webapp-testing | skill | Playwright-driven browser checks, screenshots, console capture — exploratory and regression work |
| mcp-builder | skill | Guided construction of an MCP connector for a tracker or test platform that lacks one |
| awesome-copilot Playwright companions | skills | Test generation, site exploration, test breakdown |
| Playwright CLI | companion tool | Record sessions, generated locators, live inspection |
| Playwright MCP server | MCP server | Direct browser control over MCP |

---

## 9. Onboarding sequence

Bring a repo from zero to blueprint-ready in this order:

1. `/init` → edit the root memory file.
2. Add nested memory files for test directories.
3. Configure MCP (`.mcp.json` for team connectors; user scope for personal ones).
4. Install skills — skill-creator first, then the QA starter set.
5. Define sub-agents for the roles your blueprint names.
6. Add slash commands for recurring prompts.
7. Tune `.claude/settings.json`: hooks, then permission allowlists.

---

## 10. Further reading

Canonical docs — link, don't duplicate:

- Claude Code docs: memory, MCP, skills, sub-agents, hooks, slash commands, settings, Agent SDK — https://docs.claude.com/en/docs/claude-code/
- Agent Skills standard — https://agentskills.io
- AGENTS.md spec — https://agents.md
- Anthropic skills repo — https://github.com/anthropics/skills
- Playwright and Playwright MCP — https://github.com/microsoft/playwright , https://github.com/microsoft/playwright-mcp
