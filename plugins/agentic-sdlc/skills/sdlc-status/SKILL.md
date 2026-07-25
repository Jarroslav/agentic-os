---
name: sdlc-status
description: >-
  Read-only inspector and resumer for agentic-sdlc heavy-pipeline runs kept
  under docs/superpowers/runs/. Invoke when the user asks what a run's status
  is, wants to list or drill into past pipeline runs, needs to pick back up an
  interrupted run, or is on a skill-only host (for example, Codex) that has no
  `sdlc:status` slash command and needs the same behavior exposed as a skill.
  Trigger phrases: "sdlc status", "what's the run status", "list sdlc runs",
  "resume the pipeline", "resume run <id>", "is the run stuck", "sdlc:status".
  Never mutates a completed run, and never resumes an aborted one without an
  explicit yes.
version: 0.1.0
license: Apache-2.0
discoverable: false
author: agentic-os
---

# sdlc-status

## What this does

Inspects `sdlc-pipeline` heavy-mode runs and, on explicit confirmation, hands off
a resume request to `sdlc-pipeline`. It is a stand-in for the legacy `sdlc:status`
slash command on hosts that only support skills (Codex is the reference example) —
same information, same resume gate, exposed through the skill interface instead
of a command.

This skill never executes or re-runs a pipeline phase itself. It decides *what*
should resume and *why*, then delegates the actual execution to `sdlc-pipeline`.

> Default posture is read-only. The only writes this skill performs on its own
> are corrective: fixing a stale mutable snapshot to match the append-only
> event history, and mirroring work-item ledger reconciliation. Anything that
> restarts pipeline work requires the user to say yes first.

## When to invoke

- The user asks for the status of an SDLC run, all runs, or a specific run ID.
- The user wants to resume a run that stopped mid-phase.
- The user is on a host without slash-command support and asks for `sdlc:status`.
- Another skill or the orchestrator needs a run's current phase/state before
  deciding whether to dispatch further work.

## Guardrails

| Rule | Effect |
|---|---|
| Completed runs are immutable | Never write to a run whose `meta.status` is `completed`, under any circumstance. |
| Aborted runs need explicit consent | Never resume a run whose `meta.status` is `aborted` without the user answering yes to a direct prompt. |
| Event log is append-only | Never rewrite or truncate `events.jsonl`. All corrections are additive appends. |
| Log beats snapshot | When `meta.json` and `events.jsonl` disagree, treat the event log as ground truth and correct the snapshot — never the other way around. |
| Resume is single-shot | One resume attempt per invocation. A failed resume leaves the run `interrupted`, not `aborted` — it stays resumable later. |

Blast-radius shape of this skill's own actions:

| Action | Tag | Notes |
|---|---|---|
| List runs, render catalog, compute status line | R0 | Read-only, no writes. |
| Correct `meta.json` phase fields, append `status.repaired` / `work_item.reconciled`, mirror JSONL ledgers, add a Markdown history row | R1 | Confined to run artifacts under `docs/superpowers/runs/` and `docs/superpowers/work-items/`. |
| Hand off a confirmed resume to `sdlc-pipeline` | R2/R3 (downstream) | This skill doesn't perform the repo writes or external side effects itself — it only issues the confirmed handoff. The resumed phase may touch tracked files (R2) or trigger external sync (R3); that's why the resume prompt is a hard gate. |

## Inputs

- Optional run selector: a run ID, `latest`, or nothing (list mode).
- Optional resume intent, expressed by the user after seeing a run's status.
- The on-disk run corpus under `docs/superpowers/runs/` (see below).
- The work-item ledger quartet (canonical + run-local, Markdown + JSONL).

## Records read and written

| Record | Path | Role |
|---|---|---|
| Run directory | `docs/superpowers/runs/<run_id>/` | Enumerate all run directories; sort by directory name descending (newest first) for list mode. |
| Mutable snapshot | `meta.json` | Per-run status snapshot. Fields referenced: `meta.status`, `meta.started_at`, `meta.json.phases`, `phases[N].completed_at`, `meta.json.current_phase`, `meta.json.work_item.canonical_path`, `meta.json.work_item.run_mirror`, `meta.json.task_input`. |
| Event log | `events.jsonl` | Append-only run history, one JSON object per line. Authoritative on any conflict with `meta.json`. |
| Requirements doc | `requirements.md` | Per-run; show only the first 10 lines. |
| Complexity doc | `complexity.json` | Per-run; show formatted in full. |
| QA report | `qa-report.md` | Per-run; show only the last 20 lines, and only if the file exists. |
| Gate ledger | `decisions.jsonl` | One row per gate, formatted. |
| Run-local work item | `<run_dir>/work-item.md` | Run-local Markdown mirror of the work item. |
| Run-local work-item ledger | `<run_dir>/work-item-events.jsonl` | Run-local append-only work-item history. |
| Canonical work-item ledger | `docs/superpowers/work-items/work-item-events.jsonl` | Global append-only work-item history across all runs. |
| Canonical work item | path from `meta.json.work_item.canonical_path` | Canonical Markdown work item, outside any single run's directory. |

This skill never talks to the external ticket/MR backend directly — it only
reads and reconciles these local ledger mirrors. Adapter sync into and out of
these files is somebody else's job; this skill just trusts the append-only
layers over the mutable ones when they disagree.

## Operating steps

1. **Enumerate.** List `docs/superpowers/runs/`, sorted by directory name
   descending. If no run was specified, show the list (or the newest run's
   summary) and stop unless the user picks one.
2. **Load.** For the selected run, read `meta.json` and `events.jsonl`.
   - If `events.jsonl` is missing or contains malformed lines, surface an
     audit warning and continue using `meta.json` alone — don't block on a
     broken log.
3. **Detect staleness.** If `meta.status` reads `running`, apply the stale-run
   check (below) and reclassify to `interrupted` if it fires.
4. **Reconstruct phase state.** Whenever `meta.json.current_phase` or
   `meta.json.phases` is missing, stale, or was never populated for a phase,
   derive the real phase state from `events.jsonl`: pair each phase's
   `phase.started` event with whichever terminal event (`phase.completed`,
   `phase.failed`, `phase.interrupted`) follows it.
5. **Reconcile snapshot vs. log**, if steps 3–4 surfaced a disagreement (see
   below).
6. **Emit the status line** (verbatim format below).
7. **If inspecting a specific run**, render the catalog in the fixed order
   below.
8. **If the user asks to resume**, reconcile the work-item ledgers if needed,
   select the resume candidate, confirm with the user, then hand off to
   `sdlc-pipeline`.

## Reconciliation rules

### Stale-"running" detection

Reclassify a run's status from `running` to `interrupted` when **both** hold:

- `meta.started_at` is more than 1 hour in the past, **and**
- no `phases[N].completed_at` timestamp falls within the last 30 minutes.

### Missing or malformed event log

Surface an audit warning and continue with `meta.json` alone. Don't attempt
partial reconstruction from a log you can't fully parse.

### Snapshot vs. reconstructed event history

> Append-only history can't be half-written by a crash the way a mutable
> snapshot file can. When the two disagree, the log wins — always correct
> the snapshot toward the log, never the reverse.

1. Confirm the discrepancy and the intended fix with the user.
2. Rewrite only `meta.json`'s phase-status fields to match the reconstructed
   state.
3. Append a `status.repaired` event to `events.jsonl`, with the changed
   fields in its data payload.
4. If the append itself fails: warn, and require explicit user confirmation
   before continuing any further action on this run.

### Work-item ledger conflicts

Trust priority, highest first:

1. Run event log (`events.jsonl`)
2. Canonical work-item JSONL (`docs/superpowers/work-items/work-item-events.jsonl`)
3. Run-local work-item JSONL (`<run_dir>/work-item-events.jsonl`)
4. Canonical Markdown work item (`meta.json.work_item.canonical_path`)
5. Run-local Markdown work item (`<run_dir>/work-item.md`)

Repair procedure:

1. Confirm the repair with the user before touching anything.
2. Update the Markdown snapshots (canonical and/or run-local) and the mutable
   snapshot (`meta.json.work_item.*`) to match the highest-priority source.
3. Append the outcome to `events.jsonl` as a `work_item.reconciled` event —
   its payload distinguishes which of the two reconciliation directions fired
   (canonical-sourced vs. run-local-sourced) and which fields changed.
4. Mirror the change into whichever JSONL ledgers exist (canonical and/or
   run-local).
5. Add one row under the `## History` marker in the affected Markdown file(s).
6. Proceed with whatever the user originally asked for (typically: resume).

### External-sync adapter receipts

| Adapter receipt | Markdown state | Action |
|---|---|---|
| Success, recorded in JSONL | Still shows pending | Update Markdown, mirror the change. No user confirmation needed — this is forward sync, not conflict repair. |
| Failure, recorded in JSONL | Shows failure already | Leave the failure in Markdown history as-is. Do not force a reconciliation. Leave the run resumable. |

## Resume mechanics

> A phase without a terminal `phase.completed` event can't be trusted to have
> produced valid outputs — so resume always restarts the whole phase rather
> than trying to salvage or skip partial work. Re-running a phase is treated
> as idempotent/overwriting for that phase's own deliverables.

### Resume-candidate selection order

1. First phase with a `phase.started` event and no terminal event.
2. Else, first phase the snapshot marks `running`.
3. Else, first pending phase immediately after the last completed one.

### Special-cased phase resume behaviors

| Phase | Resume behavior |
|---|---|
| Phase 7 | Skip sub-tasks already committed; dispatch only what's missing. |
| Phase 9 | Regenerate the review bundle from a fresh diff rather than reusing the prior one. |

All other phases resume by fully re-running, overwriting that phase's prior
outputs.

### Confirmation

Always confirm before resuming, using this exact template:

```text
Resume by re-running Phase <N> (<phase-name>)? It will overwrite that phase's outputs and continue. (yes/no)
```

On anything other than an explicit yes, stop — do not hand off.

### Handoff

On confirmed resume, dispatch to `sdlc-pipeline` with:

- the run's original mode (hitl or autonomous),
- `raw_input` sourced from `meta.json.task_input`,
- a resume hint naming Phase `<N>`.

If the resume attempt fails, leave the run `interrupted` — it remains
resumable on a later invocation. This skill never marks a run `aborted` on a
failed resume.

## Outputs

- **Status line** (machine-parsed, verbatim format):

  ```text
  <run_id>  <mode>  phase=<n>  status=<running|completed|aborted|interrupted>  branch=<branch>
  ```

- **Catalog display**, for a specific run, in this fixed order:

  1. `requirements.md` summary — first 10 lines.
  2. `complexity.json` — formatted, in full.
  3. `meta.json.phases` table — status + timestamps per phase.
  4. `events.jsonl` — one row per event, with malformed-line warnings inline.
  5. `decisions.jsonl` — one row per gate.
  6. `qa-report.md` summary — last 20 lines, only if the file exists.

- **Audit trail**: any reconciliation this skill performs appends
  `status.repaired` and/or `work_item.reconciled` events to `events.jsonl` —
  never a rewrite, always a new line.

- **Resume handoff**: a single dispatch to `sdlc-pipeline` per the Handoff
  section above, or no handoff at all if the user declines.

> Report only what the ledgers actually contain. Never infer or guess a
> phase's status when both `meta.json` and `events.jsonl` are silent on it —
> surface it as unknown instead.

## References

This skill has no bundled `references/` tree. Its scope is narrow enough —
parse two ledger formats, apply a fixed set of deterministic reconciliation
rules, hand off to exactly one downstream skill — that keeping the full
contract inline in this file is cheaper for a host to load than splitting it
out. Contrast with skills that fold a larger reference set in in (for example,
`code-review-orchestrator`'s `references/review-lenses.md`): this skill has no
equivalent, by design.

## Cross-references

- `sdlc-pipeline` — the orchestrator this skill resumes into. It is the
  mode-dependent phase runner for both hitl and autonomous runs; this skill
  never duplicates its phase logic, only decides where to re-enter it.
- Legacy command superseded: `sdlc:status`. This skill exists specifically for
  skill-only hosts (Codex is the example given) that can't expose that
  command directly.

## Non-goals

- Does not execute or re-run pipeline phases itself — it only decides what to
  resume and delegates to `sdlc-pipeline`.
- Does not modify a completed run, under any circumstance.
- Does not resume an aborted run without explicit user confirmation.
- Does not rewrite or truncate `events.jsonl` — corrections are additive
  appends only.
- Does not silently trust the mutable snapshot when the event log disagrees —
  always reconciles via the append-only source first, with user confirmation
  before any repair-write.
