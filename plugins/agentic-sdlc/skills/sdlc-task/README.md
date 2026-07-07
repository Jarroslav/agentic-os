# SDLC Task (Lightweight)

Lightweight SDLC entry point for user-classified XS/S/M tasks. Skips complexity scoring, subagent dispatch, and evidence files in favor of inline TDD with a one-round code review.

## Use It For

- Quickly implementing a small, well-scoped fix or feature without full pipeline ceremony.
- Running brainstorm → spec → plan → inline TDD → code review in the current conversation.
- Handling quick tasks where the full `sdlc-pipeline` subagent machinery is overkill.
- Syncing spec and plan artifacts after post-completion maintenance changes.

## How To Ask

Examples:

- "Use sdlc-task for: rename the `userId` parameter to `accountId`."
- "Quick SDLC for adding input validation to the signup form."
- "Implement this small feature with sdlc-task."
- "Use sdlc-task with mode: sync to reconcile artifacts."

## What It Needs

- superpowers plugin >= 5.0.7.
- A feature branch (the skill will help create one if you are on the base branch).
- `.agentic/guides/` optional but recommended for commit conventions and quality gates.
