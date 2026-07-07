# Knowledge Auditor

Read-only audit of a repository's documentation, structure, and AI assistant setup. Produces a structured report that `knowledge-foundation` uses to decide what to preserve, incorporate, replace, or skip.

## Use It For

- Surveying existing docs and AI configs before running knowledge foundation.
- Identifying conflicts between CLAUDE.md, AGENTS.md, GEMINI.md, or Copilot instructions.
- Checking if a repo is ready for knowledge planting.
- Reviewing the quality of skills, subagents, hooks, and assistant entrypoints.

## How To Ask

Examples:

- "Audit this repo's documentation."
- "Survey the AI assistant setup."
- "Is this repository ready for knowledge foundation?"
- "Review assistant instructions and flag any conflicts."

## What It Needs

- Read access to the repository.
- No writes are performed — this skill is strictly read-only.
