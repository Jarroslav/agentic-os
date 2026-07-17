# requirements-intake

Normalize whatever the run started with — loose text, a ticket id, a story file, or a raw idea — into one canonical `requirements.md` that every later phase reads.

## Use It For

- Turning a free-form task description into a structured requirements document.
- Resolving an external work-item id (e.g. `PROJ-123`) through a project adapter.
- Loading an existing story file (e.g. `docs/stories/2025-05-01-bulk-export.md`) and normalizing it.
- Capturing a greenfield idea when there is no ticket or story yet.
- Clearing up open or ambiguous requirement questions before planning starts — this is the resolution point.

> Intake only normalizes and clarifies. No planning, estimation, or implementation happens here.

## How To Ask

You don't call this skill by hand. `sdlc-pipeline` runs it automatically at Phase 1, and it receives whatever argument you gave an entry skill:

- `sdlc-start` — human-in-the-loop run.
- `sdlc-autonomous` — autonomous run.

Whatever you hand either starter is classified and dispatched here:

| You pass | Routed to |
| --- | --- |
| String matching a ticket-id pattern | Adapter lookup |
| Path to an existing file | Story-file normalization |
| `--greenfield "project idea"` | Idea capture |
| Anything else | Free-form description |

## What It Needs

- Exactly one of the four inputs: ticket id, story file path, free-form text, or a greenfield flag plus idea.
- For ticket lookup only: a ticket adapter declared in `.agentic/guides/project.md`. This is optional — without it the non-ticket input shapes still work, but external ticket resolution does not.

Output: a single `requirements.md`. It is the only hand-off downstream SDLC phases consume.
