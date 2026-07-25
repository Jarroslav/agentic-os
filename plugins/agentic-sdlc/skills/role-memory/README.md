# role-memory

Per-role agent memory that survives across sessions. Durable facts, preferences, and decisions plus an append-only daily log — all plain markdown, stored inside the project under `.agents/memory/<role>/`.

## Use It For

Two tiers, one namespace per role.

| Tier | Holds | When |
| --- | --- | --- |
| Durable store | Stable facts, user preferences, architectural decisions | Info must outlive the session |
| Daily log | Transient working notes, keyed to the current day | Scratch notes for today only |

Core operations:

- Save a durable item so a later session recalls it.
- Append a note to today's log.
- Recall prior decisions and learnings.
- Record a correction or a validated approach the moment it surfaces.

> Recording corrections and confirmed-working approaches is the point — it stops future sessions repeating a mistake you already fixed.

## How To Ask

Natural language, no commands. Trigger it with remember / log / recall phrasing:

- "Remember that we use pnpm, not npm."
- "Log this decision."
- "What did you learn yesterday?"
- "Recall our testing preferences."

## What It Needs

- Write access to `.agents/memory/<role>/` inside the project directory. That is the only prerequisite.
- Nothing else — plain markdown files, no service, database, or network.

> Local-only by design. Not shared, not cloud, not a vector index. Each role gets an isolated `<role>` namespace; behavior details live in this skill's own definition file alongside this README.
