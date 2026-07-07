# Requirements Intake

Normalizes any input — free-form text, ticket ID, story path, or greenfield idea — into a single `requirements.md` document consumed by downstream SDLC phases.

## Use It For

- Converting an external ticket ID into structured requirements with acceptance criteria.
- Normalizing a story file for use in the implementation pipeline.
- Capturing a greenfield project idea as initial requirements.
- Resolving open or ambiguous requirements questions before planning.

## How To Ask

This skill is invoked automatically by `sdlc-pipeline` at Phase 1. Pass any of the following to `sdlc-start` or `sdlc-autonomous` and the intake runs automatically:

- A ticket ID (e.g. `PROJ-123`)
- A story file path (e.g. `docs/stories/2025-05-01-bulk-export.md`)
- A free-form task description
- `--greenfield "project idea"`

## What It Needs

- A task description, ticket ID, story path, or greenfield flag.
- Optionally, `.agentic/guides/project.md` with a ticket adapter for external ticket lookup.
