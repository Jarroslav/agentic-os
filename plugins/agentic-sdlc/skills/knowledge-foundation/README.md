# Knowledge Foundation

Onboards a project for AI-assisted development. Audits the repo, generates structured guides under `.agentic/guides/`, and wires guide imports into the project's AI entrypoint file (CLAUDE.md, AGENTS.md, etc.).

## Use It For

- Setting up a new repository for agentic-sdlc and AI tools.
- Generating project, git-workflow, and quality-gates guide files.
- Creating or updating CLAUDE.md, AGENTS.md, or GEMINI.md for the project.
- Onboarding a client repo before starting SDLC runs.

## How To Ask

Examples:

- "Knowledge foundation."
- "Initialize this project for AI."
- "Set up guides for this repo."
- "Create CLAUDE.md."
- "Onboard this repo for AI-assisted development."

## What It Needs

- A repository with source files and manifests (not empty).
- At least one AI tool target to wire guides into (CLAUDE.md, AGENTS.md, etc.).
- User answers to project-settings questions (ticket prefix, MR target branch, project name).
