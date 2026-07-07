# Agent Memory

Per-role persistent memory stored as plain markdown under `.agents/memory/<role>/`. Keeps durable facts, preferences, and decisions across sessions alongside an append-only daily log.

## Use It For

- Saving durable facts, user preferences, and architectural decisions for future sessions.
- Logging ephemeral working notes to today's daily log.
- Recalling what was decided or learned in prior conversations.
- Tracking corrections and validated approaches so the agent doesn't repeat mistakes.

## How To Ask

Examples:

- "Remember that we use pnpm, not npm."
- "Log this decision."
- "What did you learn yesterday?"
- "Recall our testing preferences."

## What It Needs

- Write access to `.agents/memory/<role>/` inside the project directory.
- No external services — all storage is local plain markdown files.
