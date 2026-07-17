# repo-guides

Plants the knowledge foundation for AI-assisted development: surveys the repo, writes guide documents into `.agentic/guides/`, and wires them into your AI entrypoint file. Run it once per repository, before any SDLC pipeline execution.

## Use It For

- Bootstrapping a fresh repository for the plugin and AI tooling.
- Generating the three core guides — project, git-workflow, quality-gates — under `.agentic/guides/`.
- Creating or refreshing an AI entrypoint file (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, etc.) with import references to the guides.
- Onboarding a client repository ahead of its first SDLC run.

Not an orchestrator: it does not implement features, run pipelines, or manage tickets. Other skills read what it plants — commit and MR tooling, for example, consumes the git-workflow guide.

## How To Ask

Plain language works. Any of these triggers the skill:

- "Set up the knowledge foundation for this repo"
- "Initialize this project for AI development"
- "Generate the repo guides"
- "Create a CLAUDE.md entrypoint for this project"
- "Onboard this repository before we start SDLC runs"

The skill then runs three stages: audit the repository, generate the guide files, wire the entrypoint imports.

## What It Needs

All preconditions must hold before the skill runs:

| Requirement | Detail |
| --- | --- |
| Non-empty repository | Source files and manifest files must exist — empty repos are rejected. |
| Entrypoint target | At least one AI entrypoint file selected for wiring (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, etc.). |
| Project settings | You supply the ticket prefix, MR target branch, and project name — the skill never guesses them. |

> The settings interview exists because these three values feed every downstream convention (commit format, branch targeting, guide headers). Wrong guesses here would poison every later run, so the skill refuses to pick them autonomously.
