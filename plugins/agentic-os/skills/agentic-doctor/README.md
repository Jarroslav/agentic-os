# agentic-doctor — install verifier

Read-only 8-check verification of an agentic-os install: file manifest vs the
install journal, hook compile **and** import, canned-event dry-runs of the
enforcement gates, HITL output-contract smoke, settings registration, git hook
+ dependency plugins, scorecard coverage/thresholds, and agent-registry table
integrity. Writes the verdict to `.agentic/agentic-os/doctor.json`.

## Use It For

- Confirming an install or upgrade actually enforces what it claims — every
  gate is exercised with synthetic events (a block hook must exit 2 on a
  violation, 0 on clean), not just parsed.
- Diagnosing why a hook, gate, or generated agent isn't behaving: each failed
  check comes with a one-line remedy.
- Producing a machine-readable health verdict (`doctor.json`) for CI or for a
  bug report.

## How To Ask

- "/agentic-doctor"
- "Verify the agentic-os install."
- "Check the agent setup."
- "Run doctor."

## What It Needs

- An existing install journal at `.agentic/agentic-os/install.json` (written
  by `/agentic-init`) — without it the doctor reports "not installed" and
  stops.
- `python3` on PATH and a git repository (the git-hook check resolves the
  repo's hooks dir).
- Nothing else: it fixes nothing and writes only `doctor.json` plus one
  temporary probe file it deletes itself.
