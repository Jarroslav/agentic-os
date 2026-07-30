Check the state of an agentic-sdlc pipeline run, review its history, or resume it where it stopped.

## Use It For

| Situation | What you get |
|---|---|
| A run is in progress or was interrupted | Current phase, status, and what happens next |
| You need to see past gate calls or QA results | Gate decisions and QA reports pulled from the run's history |
| The saved run state looks out of date | Reconciled phase history, rebuilt from the full event record |

> The skill reads before it writes. It never mutates a run's state on its own — the one exception is resuming, and that always waits on your go-ahead first.

## How To Ask

- "What's the status of the current SDLC run?"
- "Show me where that pipeline run stopped."
- "Resume the interrupted run."
- "What did the QA gate decide on that last run?"
- "The run state looks stale — reconcile it."

## What It Needs

- At least one existing run directory to inspect — there's nothing to check on a repo that hasn't started one yet.
- The run's state snapshot and event ledger, both written by the run itself as it progresses.
- Your explicit go-ahead before it resumes anything — inspection alone never asks.

> Snapshot and ledger occasionally disagree, usually because the snapshot was captured before a later event landed. When they diverge, the skill rebuilds phase history from the ledger, not the snapshot.

Runs are created by other skills that launch pipelines, not by this one — this skill only inspects and resumes what already exists on disk.
