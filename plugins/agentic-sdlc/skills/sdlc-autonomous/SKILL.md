---
name: sdlc-autonomous
description: Kicks off an autonomous agentic-sdlc run given a task description, an external work-item reference, or just a greenfield idea. Triggers include "run autonomously", "factory mode", "ship this without asking", or a request for the legacy sdlc:autonomous command on a host that uses skills rather than commands.
version: 0.1.0
license: Apache-2.0
discoverable: false
authors:
  - agentic-os
---

# sdlc-autonomous

Skill entry point for the autonomous agentic-sdlc flow, standing in for the old `sdlc:autonomous` command on hosts such as Codex that lack command support.

## Inputs

- `raw_input` — task description, external work-item reference, story path, or greenfield idea
- `mode_flag` — optional `--greenfield`
- `escalate_on` — optional comma-separated or list-style risk flags; default `["security", "breaking-change"]`

## Usage Examples

```text
Use the sdlc-autonomous skill for "refactor the logger to pino with structured fields"
Use the sdlc-autonomous skill with --greenfield "tiny note-taking CLI in Python"
Use the sdlc-autonomous skill with --escalate-on security,breaking-change "add OAuth callback handling"
```

## Steps

1. Parse the user's intent:
   - `--greenfield "<text>"` sets `mode_flag = "--greenfield"` and captures `<text>` as `raw_input`.
   - `--escalate-on <comma-list>` splits that list into `escalate_on`.
   - Whatever text is left becomes `raw_input`.
2. Invoke the `sdlc-pipeline` skill with:

   ```json
   {
     "mode": "autonomous",
     "raw_input": "<as captured>",
     "mode_flag": "<--greenfield or none>",
     "escalate_on": ["security", "breaking-change"]
   }
   ```

3. The pipeline then runs end to end, with judgment gates resolved through `decision-router`: deterministic checks come first, fast paths second, and stand-in subagents only get used when actually needed.
4. The user is prompted only when the escalation rule fires — e.g. low confidence, or a risk flag that intersects `escalate_on`.

## Preconditions

Full SDLC runs need knowledge-foundation output already in place. If any required `.agentic/guides/` files are missing, `sdlc-pipeline` halts and points the user to the `knowledge-foundation` skill.

Before reaching any implementation-capable phase, the delegated `sdlc-pipeline` run must clear the branch guard: current branch, configured base branch, `git status --porcelain`, upstream state, target branch existence, dirty-state resolution, and latest-base handling. In autonomous mode, a dirty state halts the run unless project policy explicitly allows auto-stash — the flow must never hard-reset or push forward on a dirty tree without that policy in place.

## Notes

- Autonomous mode never auto-merges and never creates an MR/PR on its own — Phase 9 stops once the branch is ready, and `mr-creator` or a PR tool has to be invoked manually afterward.
- Every decision gets recorded in `<run_dir>/decisions.jsonl` for audit purposes.
- No core workflow logic lives in this skill; it only normalizes user intent and delegates to `sdlc-pipeline`.
