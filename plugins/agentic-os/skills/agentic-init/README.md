# agentic-init — the installer

Interviews you (role presets, HITL dial, autonomy matrix, stack confirm,
ticket/MR adapters) and scaffolds a governed multi-agent architecture into
your repo: agent contracts, enforcement hooks, escalation policies,
instruction-quality gates, and generated stack-specific agents. Journaled and
resumable; never commits.

## Use It For

- First-time setup of the agentic-os governance layer in a repo (new or mature).
- Installing for one or several roles at once — presets are additive
  (`--presets developer,qa`), their template sets union, strictest HITL wins.
- Re-running to add a preset later, or to resume an interrupted install —
  both are idempotent: already-journaled files are never rewritten, and
  user-owned files are never touched.
- Accepting every detected default in one shot with `--defaults`.

## How To Ask

- "/agentic-init"
- "Install agentic-os."
- "Scaffold the agent architecture into this repo."
- "/agentic-init --defaults" (skip the interview, take every default)
- "/agentic-init --presets developer,qa" (preselect roles)

## What It Needs

- A git repository as the current working directory (the scaffold goes to the
  repo root; nothing is committed).
- `python3` on PATH — the enforcement hooks and the doctor's checks run on it.
- The `superpowers` plugin (≥ 6.1.0) and the `agentic-sdlc` plugin — Phase 3
  registers/verifies both and pauses for a session restart if they were newly
  enabled.
- Willingness to answer six short screens (or `--defaults`).
