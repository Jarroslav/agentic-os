# Platform Adapter: GitHub Copilot

Wire the QE blueprints onto GitHub Copilot — IDE chat, or the cloud coding agent. Each blueprint names generic building blocks (persistent context, connectors, skills, roles, automation) and defers host-specific plumbing to a platform adapter. This is the Copilot adapter; sibling files in this directory cover other hosts such as Claude Code and Cursor. Read once, then return whenever a blueprint step points at your platform.

**Out of scope:** blueprint QA content itself (strategy, checklists, test design), general Copilot tutorials (autocomplete, editor usage), and licensing / pricing / account administration.

## Building-block map

| Blueprint building block | Copilot mechanism | Blast radius |
|---|---|---|
| Persistent project context | Instruction files under `.github/`, plus `AGENTS.md` | R2 — committed repo files |
| External-system connector | MCP server via `.vscode/mcp.json` or user settings | R0–R3, depends on the server |
| Reusable procedure | Skill folder under `.github/skills/` | R2 to install; runtime radius is the skill's own |
| Role / persona | Custom agent in `.github/agents/`, called with `@name` | Inherits the radius of the tools it references |
| Autonomous multi-step run | Cloud coding agent producing a draft PR | R2, human-gated at PR review |
| Session guardrails | Hooks under `.github/copilot/hooks/` | R1–R2 |
| CI-time automation | Agentic workflows (markdown on GitHub Actions) | Up to R3 — gate externally-visible steps |

## Layer 1 — persistent context

Copilot reads three layered instruction mechanisms:

| Mechanism | Where | Applies to |
|---|---|---|
| Repo-wide instructions | One file under `.github/` | Whole repo: domain, stack, build and test commands |
| Path-scoped instructions | Files under `.github/instructions/` with an `applyTo:` glob in YAML frontmatter | Only files matching the glob |
| Agent instruction files | `AGENTS.md` anywhere in the tree | Nearest ancestor to the touched file wins |

A repo-root `CLAUDE.md` or `GEMINI.md` also works as an agent-instruction file — useful when one repo serves several assistants.

When multiple instruction sets apply they merge, with precedence personal > repository > organization.

Do this:

- Create the repo-wide file first, always. Add path-scoped rules and `AGENTS.md` files only where a directory genuinely needs different behavior.
- Put exact build, run, and test commands in the repo-wide file. This is your grounding surface: tell Copilot to work from the facts written there and never invent commands, endpoints, or APIs the instructions do not list.
- Bootstrap shortcut: the cloud agent can generate the repo instructions file itself — it inspects the codebase, verifies build commands, and hands you the result as a PR to review.
- For standards that must hold across every repo in the org, use organization-level instructions instead of copy-pasting per repo. Shared context spaces, where your plan offers them, handle team-level collaboration.

> Rationale: one authoritative context file beats scattered prompt fragments. Everything downstream (skills, agents, PR review) consumes it.

## Layer 2 — connectors (MCP)

Configuration lives in `.vscode/mcp.json` for project scope or in user settings for global scope. Supported transports: stdio (local command), SSE, and streamable HTTP for remote servers. Remote OAuth servers take an auth block with a client id and optional secret. Environment variables interpolate from the host environment — keep secrets out of the committed file.

Two hard cautions before enabling any server:

1. Get project approval first.
2. Audit the server code — it executes with your permissions. Treat any server that can write to an external system (ticket trackers, test management, CI) as R3: keep a human between the agent and the side effect.

Connector choice:

| Situation | Use |
|---|---|
| MCP server exists and is organization-approved | MCP |
| MCP blocked or unapproved, or the workflow should be self-contained and portable | A custom skill wrapping the integration |

## Layer 3 — skills

A skill is a folder containing a `SKILL.md` plus optional assets, per the open Agent Skills standard. Commit skill folders under `.github/skills/`; Copilot auto-discovers them and triggers them when relevant.

Install paths: either the plugin-install CLI command pointed at the community registry, or copy the folder into the repo and commit it.

Portability: because the format is an open standard, the same folder dropped into `.claude/skills/` is auto-discovered by Claude Code. Author a skill once, run it on both hosts.

Before authoring anything by hand:

- Install the meta-skill from the official community collection that scaffolds standards-compliant skills. Do it once per repo.
- Search the community collection first — 500+ assets across seven categories (skills, agents, instructions, plugins, hooks, workflows, cookbook recipes) with a searchable companion website. Prefer entries with higher usage and ratings.

### QA starter pack

| Skill | Function | Runtime radius | Model tier |
|---|---|---|---|
| make-skill-template | Scaffolds standards-compliant new skills | R2 | economy |
| webapp-testing | Playwright browser E2E checks with screenshots and console capture | R1 | standard |
| playwright-generate-test | Turns a page or flow description into a Playwright script | R2 | standard |
| playwright-explore-website | Explores a site with Playwright, capturing structure and screenshots | R0–R1 | economy |
| breakdown-test | Decomposes a feature into scenarios and test cases | R1 | standard |
| quality-playbook | State-machine analysis and missing-safeguard detection | R0 | premium |
| polyglot-test-agent | Test generation across multiple languages | R2 | standard |
| security-review | AI vulnerability scan of a codebase | R0 | premium |

> Rationale: reasoning-heavy analysis (state machines, vulnerability triage) earns the premium tier; scaffolding and exploration run fine on economy. Radius stays low because these skills read code and write tests — anything that would push results into an external system belongs behind an R3 gate.

## Layer 4 — agents and automation

**Custom agents.** Markdown personas in `.github/agents/`: YAML frontmatter (name, description, tool and MCP references) plus prose instructions. Invoke in chat as `@name`. Give each agent a single responsibility and only the tools that responsibility requires — an agent's effective blast radius is the union of its tool grants.

**Cloud coding agent.** Runs autonomously in an isolated environment, clones the repo, and outputs a draft PR. Trigger it from the Copilot agents web page, an `@copilot` mention on an issue or PR, a chat surface, or the API. Escalate to it when a task is multi-step and should land as a reviewable PR rather than local edits — the PR review is the human gate that keeps the run at R2.

**Hooks.** Shell commands fired at defined points in an agent session: post-edit linting, command blocking, context injection, pre-commit validation. Store them under `.github/copilot/hooks/`. Use them to enforce blueprint gates mechanically instead of trusting prose instructions.

**PR code review.** Copilot's review feature reads both the repo-wide and path-scoped instruction files; enable it in repo settings. Write your review criteria into those files once and the reviewer inherits them.

**Agentic workflows.** Markdown-defined AI automations built on GitHub Actions — the CI-time counterpart to chat-triggered skills.

## Onboarding sequence

Run these in order; stop early if a step is not needed yet.

1. Write the repo-wide instructions file.
2. Add path-scoped rules where directories diverge.
3. Add agent files (`.github/agents/`, `AGENTS.md`).
4. Wire connectors and install skills.
5. Validate everything in live chat against a real task.
6. Browse the community collection for gaps you can fill with existing assets.
7. Add hooks and enable cloud execution.

## Playwright companions

Two companion tools cover browser-level QA work from Copilot:

- A Playwright recorder CLI — records sessions, generates selectors, supports interactive locator testing.
- A Playwright MCP server — live browser control, screenshots, and test execution driven from Copilot.

Both pair with the starter-pack Playwright skills above: record or explore first, then generate and run tests.

## Where to look next

Official GitHub and VS Code documentation for instruction files, MCP configuration, and the cloud agent; the community asset collection and its companion website for reusable skills and agents; the Agent Skills standard site for the skill format; and the two Microsoft Playwright repositories for the recorder CLI and MCP server.
