---
name: sdlc-status
description: Inspects or resumes a heavy-pipeline agentic-sdlc run. Use it to check SDLC status, look at past runs, pick an interrupted run back up, or serve the legacy sdlc:status command on a skills-based host.
version: 0.1.0
license: Apache-2.0
discoverable: false
authors:
  - agentic-os
---

# sdlc-status

Skill entry point that inspects and resumes agentic-sdlc heavy-pipeline runs, standing in for the old `sdlc:status` command on hosts such as Codex that lack command support.

## Behavior

Read-only unless the user explicitly confirms a resume.

`meta.json` holds the current snapshot, while `events.jsonl` is the append-only run
history. Both status checks and resume decisions look at both of those files,
plus the canonical Markdown work item, run-local `work-item.md`, and the
work-item JSONL ledgers.

## Steps

1. List every directory under `docs/superpowers/runs/`, sorted by name descending.
2. For each run, read `meta.json` and, if present, `events.jsonl`. When `events.jsonl` is missing or contains malformed lines, surface an audit warning but keep going using `meta.json`.
3. For each run, print:

   ```text
   <run_id>  <mode>  phase=<n>  status=<running|completed|aborted|interrupted>  branch=<branch>
   ```

4. When `meta.status === "running"` but the process itself isn't actually live, show it as `interrupted`. The heuristic:
   - `meta.started_at` is older than 1 hour, and
   - no `phases[N].completed_at` was written in the last 30 minutes.
5. Ask the user which run to inspect, or `none` to exit.
6. For the chosen run, print:
   - `requirements.md` summary, first 10 lines
   - `complexity.json`, formatted
   - `meta.json.phases` table with status and timestamps
   - `events.jsonl`, formatted as one row per event, with warnings for malformed lines
   - `decisions.jsonl`, formatted as one row per gate
   - `qa-report.md` summary, last 20 lines, if present
7. Rebuild phase state directly from `events.jsonl`: scan for each `phase.started` and pair it with whatever terminal event for that same phase comes later — `phase.completed`, `phase.failed`, or `phase.interrupted`. A phase whose `phase.started` has no later terminal event is the top candidate for resume. Treat this reconstruction as authoritative whenever `meta.json.current_phase` or `meta.json.phases` is missing, stale, or was skipped.
8. Reconcile the work item by reading:
   - `meta.json.work_item.canonical_path`
   - `meta.json.work_item.run_mirror`
   - `<run_dir>/work-item.md`
   - `<run_dir>/work-item-events.jsonl`
   - `docs/superpowers/work-items/work-item-events.jsonl`
   - the canonical Markdown work item when present
9. When work-item Markdown and work-item JSONL disagree, trust append-only evidence in this priority order: run `events.jsonl`, canonical work-item JSONL, run-local work-item JSONL, canonical Markdown, run-local Markdown. Confirm with the user before repairing, then resume. A repair here means updating only the Markdown snapshots and `meta.json` as needed, appending a `status.repaired` or `work_item.reconciled` event to `events.jsonl`, mirroring that reconciliation into the work-item JSONL ledgers where they exist, and adding a Markdown `## History` row. JSONL itself is never rewritten or truncated.
10. When `meta.json` disagrees with the reconstructed event history, confirm with the user before repairing the snapshot, then resume. A repair here means rewriting only `meta.json` to match the event-derived phase statuses, then appending a `status.repaired` event to `events.jsonl` with the changed fields in `data`. If appending that repair event fails, warn the user and only continue once they've explicitly confirmed.
11. For a run that's `interrupted` or `aborted`, find the first phase with `phase.started` and no terminal event. If there isn't one, find the first phase with `status: "running"` in `meta.json`. If nothing is running, find the first pending phase after the last completed one.
12. Ask:

   ```text
   Resume by re-running Phase <N> (<phase-name>)? It will overwrite that phase's outputs and continue. (yes/no)
   ```

13. On `yes`, invoke `sdlc-pipeline` with the original mode, `raw_input` from `meta.json.task_input`, and a resume hint for phase N.

## Why Re-Run Instead Of Skip

If a phase is marked `running`, it never actually finished, so its outputs can't be trusted. Re-running that same phase idempotently overwrites the deterministic outputs it produced and keeps downstream steps from consuming anything half-written.

The event ledger is what stops the status command from blindly trusting a stale snapshot. If `meta.json` claims a phase completed but `events.jsonl` only has `phase.started` for it, resume from that phase after the snapshot is repaired. Conversely, if `events.jsonl` shows `phase.completed` while `meta.json` still says `running`, repair `meta.json` from the event history and append `status.repaired`.

The work-item ledgers serve the same purpose for resume, guarding against stale Markdown. If
the canonical Markdown says external sync is still pending but a later normalized receipt
in JSONL shows it actually succeeded, update the Markdown, mirror the change into the run-local
work item, append `work_item.reconciled`, and carry on. If the adapter receipt
failed instead, keep that failure recorded in Markdown history and leave the run resumable.

## Constraints

- Never modify a `completed` run.
- Never resume an `aborted` run without explicit user confirmation.
- Resume is a single-shot action. If it fails again, the run remains interrupted and can be resumed once more.
- Phase 6 resume skips already committed tasks and only re-dispatches missing work.
- Phase 7 resume regenerates the review bundle from a fresh diff.
- Never rewrite or truncate `events.jsonl`; repairs are represented by appending `status.repaired`.
