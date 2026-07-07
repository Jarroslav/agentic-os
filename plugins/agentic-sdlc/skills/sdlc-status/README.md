# SDLC Status

Inspects agentic-sdlc pipeline runs and optionally resumes an interrupted one. Reads run state from `meta.json` and `events.jsonl` to reconstruct the authoritative phase history.

## Use It For

- Checking the current phase and status of a running or interrupted SDLC run.
- Resuming a pipeline that was interrupted mid-phase.
- Reviewing gate decisions and QA reports from a past run.
- Reconciling stale `meta.json` snapshots against the append-only event ledger.

## How To Ask

Examples:

- "SDLC status."
- "Check my current run."
- "Resume the interrupted SDLC run."
- "What phase is the pipeline on?"

## What It Needs

- At least one run directory under `docs/superpowers/runs/` created by a prior `sdlc-start` or `sdlc-autonomous` run.
- User confirmation before resuming — the skill is read-only by default.
