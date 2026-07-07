---
name: sdlc-pipeline
description: |-
  The orchestrator behind both hitl and autonomous runs — the phases are identical between the two modes; only the decision-router call at each judgment gate varies by mode. It loads memory once, at Phase 0, records per-task evidence as implementation proceeds, holds off on model-heavy code review until the implementation is fully done, and always tries deterministic QA/verification checks before reaching for a subagent.
version: 0.4.0
license: Apache-2.0
discoverable: false
authors:
  - agentic-os
---

# sdlc-pipeline

This skill is the single authority governing the SDLC flow. `sdlc-start` (hitl) and `sdlc-autonomous` both call into it with a `mode` flag, and that flag is the only thing that changes between them.

## Judgment Gates

Every judgment gate is routed through `decision-router` together with the active `mode`, `run_dir`, and a bounded set of `ArtifactRefs`. Under HITL mode, `decision-router` is required to put these gates in front of the user; prompt caps, low-risk signals, deterministic checks, and stand-in subagents are never allowed to turn an approval gate into a rubber stamp.

The gates requiring HITL judgment are:

- Ambiguous requirements: `requirements.ambiguous`
- Spec clarification and approval: `spec.clarification`, `spec.approved`
- Plan approval: `plan.approved`
- Review decisions: `code-review.final`, `code-review.check`
- Drift decisions: `qa.drift`
- Blocking feature verification: `feature.verification`

Checks that are purely structural and don't decide anything about user intent or approval — say, rejecting an unrecognized gate or a deterministic skip when there's no user-visible change — are free to stay mechanical.

## Inputs

- `mode` — `hitl` | `autonomous`
- `raw_input` — verbatim user input (task description, ticket id, or greenfield idea)
- `mode_flag` — optional `--greenfield`
- `escalate_on` — list of risk flags that force escalation in autonomous mode (default `["security","breaking-change"]`)

## Run state

Generate `run_id = YYYYMMDD-HHMM-<branch>` and create `<repo>/docs/superpowers/runs/<run_id>/`. Initial `meta.json`:

```json
{
  "run_id": "<id>",
  "mode": "hitl|autonomous",
  "started_at": "<ISO>",
  "task_input": "<raw_input>",
  "branch": null,
  "work_item": {
    "canonical_path": null,
    "run_mirror": "docs/superpowers/runs/<run_id>/work-item.md",
    "event_ledger": "docs/superpowers/runs/<run_id>/work-item-events.jsonl"
  },
  "current_phase": 0,
  "status": "running",
  "escalate_on": ["security","breaking-change"],
  "phases": {
    "0":  {"status": "pending"},
    "1":  {"status": "pending"},
    "2":  {"status": "pending"},
    "3":  {"status": "pending"},
    "4":  {"status": "pending"},
    "5":  {"status": "pending"},
    "6":  {"status": "pending"},
    "7":  {"status": "pending"},
    "8":  {"status": "pending"},
    "9":  {"status": "pending"},
    "10": {"status": "pending"},
    "11": {"status": "pending"},
    "12": {"status": "pending"}
  }
}
```

Run initialization also creates `<run_dir>/work-item.md` and
`<run_dir>/work-item-events.jsonl`. The initial mirror is allowed to be a placeholder
derived straight from `raw_input`; Phase 1 later replaces or syncs it once
`requirements-intake` has resolved the canonical local work item. Append
`work_item.created` to the run-local ledger, whether it's for the placeholder or the
resolved item. External tickets are optional, but the run-local mirror is not.

### Branch guard contract

The pipeline MUST run a branch guard before any phase capable of implementation begins, and it MUST record the outcome in run state. This guard sits inside Phase 2 for full runs, and Phase 6 implementation stays blocked until it has passed for the current branch.

What the repository inspection must cover:

- Inspect the current branch with `git branch --show-current`.
- Pull the configured base branch out of `.agentic/guides/standards/git-workflow.md`; when that's absent, fall back to the repository's default branch as reported by git remote metadata, and failing that, use `main`.
- Inspect dirty working tree state with `git status --porcelain`, counting untracked files too.
- Check upstream state for both the current branch and the target branch: ahead, behind, or diverged.
- Verify the target feature branch already exists (locally or remotely) before switching to it; if it doesn't, only create it once the base branch has been checked and refreshed.

Persist the decision in `meta.json.branch_guard`:

```json
{
  "current_branch": "<branch>",
  "base_branch": "<configured-base>",
  "target_branch": "<feature-branch>",
  "working_tree": "clean|dirty",
  "upstream": "none|ahead|behind|diverged|in-sync",
  "target_branch_exists": true,
  "base_refreshed": true,
  "decision": "continue|stash|commit-first|hard-reset|proceed-dirty|abort|halted"
}
```

The choices available to a HITL user facing a dirty tree:

- `stash`: stash the existing dirty working tree before continuing, then record the stash ref in `branch_guard`.
- `commit first`: stop and let the user commit the existing work before the SDLC run continues.
- `hard reset`: only run a destructive reset after explicit user confirmation that names the branch and acknowledges data loss.
- `proceed with the existing dirty state`: continue only after warning that unrelated changes may be mixed into the run and recording that warning in `branch_guard.decision`.
- `abort`: stop the run before requirements, planning, or implementation touches files.

Autonomous mode handles a dirty tree more conservatively:

- It halts on any dirty working tree unless project policy explicitly permits auto-stash for SDLC runs.
- Where auto-stash is permitted, it may stash and continue, but only if the stash command succeeds and the resulting tree comes back clean.
- It MUST NOT hard reset, MUST NOT commit user changes, and MUST NOT proceed with the existing dirty state without explicit project policy backing that choice.

How the latest base and target branch get handled:

- Fetch the remote base whenever network access and project policy allow it.
- Before creating a new feature branch, switch to the configured base branch and fast-forward it if possible.
- Should the base update fail to stay clean, require a merge commit, or leave `git status --porcelain` non-empty, halt: ask for reconciliation in HITL mode, or halt for manual intervention in autonomous mode.
- When the target branch already exists, inspect its unique commits and local changes before continuing. A clean branch already based on the latest target branch can proceed as-is. One with unique commits, a stale base, or local changes triggers a question — continue, recreate, rebase/fast-forward, or abort — and autonomous mode halts unless policy hands it exactly one deterministic choice.

### Run event ledger

Each run has its own append-only `<run_dir>/events.jsonl` ledger. Think of `meta.json` as the current snapshot and `events.jsonl` as the durable history that status, resume, audit, and repair flows all rely on. The pipeline and its helper skills MUST append event lines on a best-effort basis and MUST NOT rewrite or truncate the ledger.

Each line is one JSON object:

```json
{
  "schema": 1,
  "ts": "<ISO>",
  "event": "phase.started | phase.completed | phase.failed | phase.interrupted | artifact.written | decision.recorded | work_item.created | work_item.assigned | work_item.transitioned | work_item.linked_artifact | work_item.adapter_receipt | work_item.adapter_warning | work_item.reconciled | status.repaired | <semantic-event>",
  "run_id": "<id>",
  "phase": 0,
  "actor": "sdlc-pipeline | decision-router | sdlc-status | <skill-or-subagent>",
  "summary": "<single-line human summary>",
  "artifacts": ["<run-relative path>", "..."],
  "data": {}
}
```

What each field means:

- `schema`: integer event schema version, currently `1`.
- `ts`: ISO timestamp marking when the event was appended.
- `event`: a stable event name. The required lifecycle events are `phase.started`, `phase.completed`, `phase.failed`, `phase.interrupted`, `artifact.written`, `decision.recorded`, plus the local work-item events (`work_item.created`, `work_item.assigned`, `work_item.transitioned`, `work_item.linked_artifact`, `work_item.adapter_receipt`, `work_item.adapter_warning`).
- `run_id`: the id of the current run.
- `phase`: the numeric phase id, when the event belongs to one; `null` marks a run-level event instead.
- `actor`: whichever skill, subagent, or host component appended the event.
- `summary`: a concise, human-readable description of the event.
- `artifacts`: run-relative paths for artifacts the event wrote or consumed.
- `data`: an event-specific structured payload; use `{}` if there's nothing extra to carry.

### Lifecycle adapter emissions

Lifecycle adapter behavior doesn't assume any particular provider — it's spelled out in
`${CLAUDE_PLUGIN_ROOT}/references/work-item-adapters.md`. The pipeline only ever emits
these lifecycle intents:

- `prepare_for_development` after requirements intake resolves a local work item
  and the branch guard succeeds.
- `record_delivery_audit` after QA gates and feature verification reach
  handoff-ready evidence.
- `complete_or_handoff` during Phase 9 handoff.

Every emission carries the standard lifecycle adapter input — `schema`,
`intent`, `mode`, `run_id`, `phase`, `local_work_item_path`,
`run_work_item_path`, `artifacts`, and `policy`. Adapter responses need to be
normalized to the receipt schema before they're stored.

An adapter that's missing or failing must never block the run. Keep going locally: append a
history row to both the canonical and run-local Markdown work items, log
`work_item.adapter_warning` for a missing adapter or `work_item.adapter_receipt`
with `status: "failed"` for one that failed, and mark the work item's external sync as `pending`
or `failed`. Successful receipts, by contrast, update the external ticket's
metadata, lifecycle state, assignee, audit URL, linked artifacts, and history.

### Per-phase lifecycle (resume safety)

1. On entering phase N: set `phases[N].status = "running"`, record `started_at`, then append `phase.started` with `phase: N`.
2. Whenever a phase writes or overwrites a durable artifact, append `artifact.written` with that artifact's path. Also append `work_item.linked_artifact` to `<run_dir>/work-item-events.jsonl`, and — whenever `meta.work_item.canonical_path` is known — to `docs/superpowers/work-items/work-item-events.jsonl`; add the artifact path under the work item's `## Linked Artifacts` section too.
3. Once the phase completes successfully: set `phases[N].status = "completed"`, record `completed_at`, advance `meta.current_phase`, then append `phase.completed` with `phase: N`.
4. If a phase fails in a handled way: append `phase.failed` with a summary of the failure and leave the phase in a resumable state.
5. If an error goes unhandled or the host is interrupted: leave `phases[N].status = "running"` and `meta.status = "running"` as-is. Treat the run as **interrupted** rather than advanced, and append `phase.interrupted` if there's still a chance to write before exiting.

### Resume contract

The resume rule `sdlc-status` follows: examine `meta.json`, `events.jsonl`, the canonical
Markdown work item, the run-local `work-item.md`, and the work-item JSONL ledgers, then
re-run every phase whose `phase.started` has no later terminal event
(`phase.completed`, `phase.failed`, or `phase.interrupted`), or whose snapshot
status still reads `running` (idempotently — details below). Phases already marked `completed`
with a matching `phase.completed` event are skipped. The pipeline only moves on to the next phase
once the resumed one reaches `completed`.

If the work-item sources disagree on resume, trust append-only evidence in
this priority order: the run's `events.jsonl`, the canonical `work-item-events.jsonl`, the run-local
`work-item-events.jsonl`, the canonical Markdown, and finally the run-local Markdown. Repair the
disagreement by appending a `status.repaired` or `work_item.reconciled` event and adding a
Markdown history row — never rewrite or truncate the JSONL ledgers. Where the canonical
Markdown lacks data the JSONL proves happened, update both the Markdown and its run mirror.
Where the Markdown holds local-only history the JSONL doesn't have, append a reconciliation
event that keeps the Markdown row rather than dropping it.

### Idempotency requirement

- Phase outputs live at deterministic paths (`requirements.md`, `complexity.json`, `design.md`, `plan.md`, `qa-report.md`, `evidence/*.json`).
- Re-entering a phase **overwrites** its output rather than appending to it — skills need to treat every re-run as an authoritative replacement.
- The exceptions are `events.jsonl` and `decisions.jsonl`: these stay append-only audit ledgers.
- Phase 7 task subagents check whether a task's commits are already on the branch; anything already there is skipped, and only new tasks proceed.
- Phase 9 rebuilds the review bundle from a fresh `git diff`, so any files changed since the last attempt are picked up.
- Phase 10 rebuilds the gate plan from a fresh `git diff` for the same reason — changes since the last attempt are honored.

This supersedes the older `current_phase + 1` resume rule, which used to advance past artifacts that were only partially written.

---

## Phase 0 — Doctor + memory load

1. A full SDLC run can't start without knowledge-foundation output already in place. These files must exist:
   - `.agentic/guides/project.md`
   - `.agentic/guides/standards/git-workflow.md`
   - `.agentic/guides/quality-gates.md`
2. Should any of those be missing, HALT with:
   ```
   [GUIDE MISSING] `.agentic/guides/<filename>` not found.
   Run the `knowledge-foundation` skill to generate project guides before starting a full SDLC run.
   ```
3. Read `.agentic/agentic-sdlc/doctor.json` if it exists. Compute `fingerprint = hash(node version + superpowers version + plugin version)`. Re-run every check and rewrite the cache file whenever the file is missing, `checked_at` is older than `doctor.ttl_days` (default 7), or the fingerprint doesn't match.
4. The checks themselves: is the `superpowers` skill resolvable (i.e., does `superpowers:brainstorming` exist), `node --version`, `git --version`. Missing superpowers means printing an install hint and halting.
5. Load `memory_brief` exactly once: read `.agents/memory/sdlc/MEMORY.md` alongside the last two files under `.agents/memory/sdlc/daily/*.md`, concatenated into one string and capped around 6 KB (trim the oldest daily log first if it needs to shrink).
6. Store `memory_brief` in run state so it can propagate forward.

## Phase 1 — Requirements

Invoke `requirements-intake` with `raw_input`, `mode_flag`, `run_dir`. It writes `requirements.md`.
It also has to resolve the canonical local work item, write `<run_dir>/work-item.md`,
append `<run_dir>/work-item-events.jsonl`, and return or record the canonical
path in `meta.work_item.canonical_path`.

Where `requirements.md` has items under "Open questions", call `decision-router` once per question, with `gate_id: "requirements.ambiguous"`, and append the answers under "## Resolved questions".

## Phase 2 — Feature branch

Work out the branch name — a ticket id verbatim, a local work item slug, or a kebab-case `feature/<name>`. Claude and Codex hosts MUST always work on a feature branch in the current checkout and MUST NOT create a git worktree. Run the branch guard contract before switching to or creating branches.

1. Inspect the current branch, the configured base branch, `git status --porcelain`, the upstream ahead/behind/diverged status, and whether the target branch exists.
2. Work out the dirty-tree resolution using the HITL or autonomous branch guard rules above before moving forward.
3. Refresh the target/base branch to the latest state where allowed: fetch, switch to base, fast-forward only, and confirm the base is still clean afterward.
4. When the current branch already is the target feature branch, check whether it's based on the latest target branch and whether it carries unique commits or local changes before proceeding.
5. When the current branch is the configured base branch, only create and switch to the target feature branch once the base refresh has passed.
6. When the current branch is some other feature branch, halt and ask: continue on the current branch, switch to the target branch, recreate the target branch off the refreshed base, or abort.
7. Update `meta.json.branch` and `meta.json.branch_guard`.
8. Update `<run_dir>/work-item.md` and the canonical work item with the chosen
   branch, append `work_item.assigned`, and record the branch guard metadata as a
   work-item history entry.
9. Emit `prepare_for_development` whenever requirements intake resolved a local work
   item and the branch guard decision came back `continue`, `stash`, or
   `proceed-dirty`. The adapter input should include `requirements.md`, the branch guard metadata, the
   selected branch, the canonical work item, and the run-local work item.
   Adapters that are missing or fail still let the run continue, with warnings and local history
   recorded per the lifecycle adapter contract.

## Phase 3 — Complexity scoring

**Heuristics come first**, sparing a subagent dispatch whenever the routing decision is already obvious:

1. Derive cheap signals from `requirements.md` plus a fresh `git ls-files`:
   - `affected_file_estimate` — count of files matching keywords drawn from the goal
   - `keyword_signals` — boolean flags for `security`, `auth`, `migration`, `breaking`, `provider`, `integration`, `refactor`
   - `goal_word_count` — total word count of the goal description
2. Then apply these rules:
   - Single-file scope, no risk keywords, and a goal under 25 words → score 8, routing `writing-plans`. **Skip the agent.**
   - A risk keyword present, or `affected_file_estimate >= 7`, or the goal describes multi-system integration → score 24, routing `brainstorming`. **Skip the agent.**
   - Anything else → invoke `complexity-scoring`, which in turn dispatches the `complexity-assessor` agent.
3. Persist the result to `<run_dir>/complexity.json`, recording `source: "heuristic" | "agent"`.

Should the final `routing` come back `"split-required"`, HALT with a clear message asking the user to break the work down.

## Phase 4 — Spec (conditional)

`routing === "writing-plans"` (score 6-14) means skipping straight to Phase 5.

`routing === "brainstorming"` (score 15-36) means the following:

**Phase 4 is executed from scratch on every single run. Don't skip brainstorming just because a `design.md` happens to already sit in `<run_dir>` or in some sibling run directory — a `design.md` that wasn't produced by `superpowers:brainstorming` during this run doesn't count as valid Phase 4 output and can't be used.**

1. Invoke `superpowers:brainstorming`. Whenever the brainstorming skill raises clarifying questions, route each one through `decision-router` with `gate_id: "spec.clarification"`, then feed the resulting verdict back in as the user's response.
2. Brainstorming produces a design doc under `docs/superpowers/specs/`. Copy or symlink it to `<run_dir>/design.md`.
3. Call `decision-router` with `gate_id: "spec.approved"` and `artifacts: <ArtifactRefs>` (see "Artifact summaries" below). A `request-changes` verdict loops back into brainstorming with the follow-ups attached; an `abort` verdict sets `meta.json.status = "aborted"` and HALTs.
4. Once approved, emit the semantic event `spec.approved` (this feeds memory auto-write).

## Phase 5 — Plan

Invoke `superpowers:writing-plans`, handing it the design doc (or the requirements directly, for low-complexity cases). The plan format MUST include a `Test-first: yes/no — <failing test description>` line for every implementation task.

**Greenfield seeding**: whenever `requirements.md` reports its source as `greenfield`, the pipeline MUST instruct `superpowers:writing-plans` to set the first plan task to "set up the test runner and write the first failing test" — for greenfield POCs, bootstrapping TDD this way isn't optional.

**Clarifying-question cap**: honor `config.mode_defaults.<mode>.max_clarifying_questions_per_phase` (default 3). Once a phase hits that cap, remaining ambiguities get deferred to a follow-up run instead of triggering more prompts.

That cap only bounds ambiguity prompts — it never auto-approves `spec.approved`, `plan.approved`, review, drift, or blocking verification gates. Those still go through `decision-router` and still ask the user under HITL mode.

The plan itself is written under `docs/superpowers/plans/`, then copied or symlinked to `<run_dir>/plan.md`.

Call `decision-router` with `gate_id: "plan.approved"` and `artifacts: <ArtifactRefs>`. A `request-changes` verdict loops back into writing-plans with the follow-ups; approval emits the semantic event `plan.approved`.

## Phase 6 — QA Checklist

If `.agentic/guides/testing/qa-strategy.md` does not exist, skip this phase (qa-foundation has not been run). Log a warning: "QA knowledge foundation not found — skipping qa-planner. Run the `qa-foundation` skill to enable QA-guided development."

Otherwise:

Invoke `qa-planner` with `mode: "--checklist"`, `run_dir`, and `merge_base`.

Receive `{checklist_path}` — the absolute path to `<run_dir>/qa-checklist.md`.

Store `checklist_path` in run state. Pass it to every Phase 7 implementation subagent context so subagents can read checklist scenarios before invoking `superpowers:test-driven-development`.

Gate: `qa-checklist.approved` (called inside `qa-planner`; pipeline waits for resolution before entering Phase 7).

## Phase 7 — Implementation (TDD via evidence files, no model review)

Invoke `superpowers:subagent-driven-development` with the plan path, repo path, branch, and `memory_brief`, and `checklist_path` (from Phase 6 run state; omit if Phase 6 was skipped). Each task subagent MUST invoke `superpowers:test-driven-development` for its task. If `checklist_path` is provided, the subagent reads `qa-checklist.md` and filters scenarios matching its task's affected files; the `failing_test_command` in its evidence file should correspond to a checklist scenario where one exists. Subagents must operate in the current checkout on the active feature branch; they must not create or request worktrees.

### Task evidence requirement

Before the task subagent finishes, it writes `<run_dir>/evidence/<task-id>.json`:

```json
{
  "schema": 1,
  "task_id": "<id>",
  "test_first": true,
  "failing_test_command": "<exact command run BEFORE implementation>",
  "failure_excerpt": "<~500 chars showing the failure>",
  "implementation_summary": "<1-3 sentences on what changed>",
  "passing_command": "<exact command run AFTER implementation>",
  "passing_excerpt": "<~500 chars showing the pass>",
  "files_touched": ["path/a.ts", "path/b.test.ts"],
  "diff_lines_added": <int>,
  "diff_lines_removed": <int>
}
```

Evidence is validated deterministically by the pipeline before Phase 7. A missing or malformed evidence file blocks the run, but **does not dispatch a code-review subagent**. Model-based code review is intentionally deferred until the full implementation diff exists.

### Evidence validation

For every task in `plan.md`:

1. Load `<run_dir>/evidence/<task-id>.json`.
2. If the file is missing or malformed, dispatch a fix-up implementation task with the exact evidence issue.
3. If the plan line says `Test-first: yes`, require:
   - `evidence.test_first === true`
   - `failure_excerpt` matches `/FAIL|Error|Assert|expected|exit code/i`
   - `passing_excerpt` matches `/PASS|ok|passed/i`
4. On deterministic evidence failure, retry the implementation task at most 2 times, then escalate.
5. On success, continue without review.

## Phase 8 — QA Test Review

If Phase 6 was skipped (qa-foundation not run), skip this phase.

Otherwise:

Invoke `qa-planner` with `mode: "--review-tests"`, `run_dir`, and `merge_base`.

On `approve`: proceed to Phase 9.
On `request-changes`: dispatch one fix-up implementation task (`superpowers:subagent-driven-development`) with the specific high-severity findings from `<run_dir>/qa-test-review.md` as context. After the fix-up completes, re-invoke `qa-planner --review-tests` once. If still `request-changes` after the single retry, escalate to the user with the review findings.

## Phase 9 — Final code review (two rounds)

Build `<run_dir>/review-bundle.json` from fresh repository state:

```json
{
  "schema": 1,
  "diff_base": "<merge_base>",
  "changed_files": ["path/a.ts"],
  "diffstat": {"files": 3, "added": 120, "removed": 20},
  "risk_flags": ["security", "public-api", "ui"],
  "evidence_summaries": [{"task_id": "T1", "test_first": true, "passing_command": "..."}],
  "artifact_refs": ["requirements.md", "design.md", "plan.md", "qa-checklist.md"]
}
```

If `qa-checklist.md` is present in `run_dir`, include it as an ArtifactRef with `kind: "qa-checklist"`. The code reviewer uses it to cross-reference implementation against planned QA scenarios.

Run exactly two model-review opportunities:

1. **Round 1: review** — call `decision-router` with `gate_id: "code-review.final"` and the review bundle as an ArtifactRef.
   - On `approve`, continue.
   - On `request-changes`, dispatch one fix-up implementation task with the reviewer findings.
2. **Round 2: check** — only if Round 1 requested changes, call `decision-router` with `gate_id: "code-review.check"` and include:
   - original findings with stable IDs
   - fix-up diff since Round 1
   - commands/evidence from the fix-up task
   - On `approve`, continue.
   - On `request-changes`, dispatch one final fix-up task. Do **not** run another full review unless the user explicitly asks.

Round 2 is findings-only. It must not re-review the full implementation unless the fix-up diff creates a new high-risk flag (`security`, `breaking-change`, `public-api`).

## Phase 10 — QA gates and feature verification

Invoke `qa-gates` with `branch`, `merge_base`, `repo_path`. Receive `{passed, blocked_gate, drift_detected, gate_plan}`.

- If `passed === false`:
  - HITL: print failure, ask the user to fix, then re-invoke `qa-gates`.
  - Autonomous: dispatch a fix-up task (one more `superpowers:subagent-driven-development` task with the failure context). Max 2 retries, then escalate.
- If `drift_detected === true`: call `decision-router` with `gate_id: "qa.drift"`. On `approve`, continue. On `request-changes`, invoke `spec-refinement` (if available) and re-run `qa-gates`.

Phase 8 mechanical QA is **necessary but not sufficient** for shipping a user-visible change. Continue to feature verification regardless of UI involvement; the verification skill itself decides whether to do real work.

### Feature verification

Invoke `feature-verification` with `gate_plan`, `qa_report`, `branch`, `merge_base`, `repo_path`, `run_dir`. Receive `{required, verified, tool, results, blocking}`.

- `required === false` (no user-visible surface in diff) → skip the gate, emit `qa.ready` deterministically, then emit `record_delivery_audit` with the QA report and gate plan.
- `required === true AND verified === true AND blocking === false` → emit semantic event `feature.verified`. Then emit `qa.ready` deterministically and emit `record_delivery_audit` with QA and verification evidence.
- `required === true AND blocking === true` → call `decision-router` with `gate_id: "feature.verification"`, passing the verification-evidence files as ArtifactRefs.
  - HITL: user reviews evidence and decides.
  - Autonomous: `tech-lead-reviewer` reviews evidence shape + per-feature results; verdict drives the loop:
    - `approve` → emit `feature.verified`, emit `qa.ready`, then emit `record_delivery_audit` with QA and verification evidence.
    - `request-changes` → dispatch a fix-up task (`superpowers:subagent-driven-development`) with the failing feature_id and console/network errors; then re-invoke `feature-verification`. Max 2 retries, then escalate.

Feature verification is deterministic in the no-user-visible-change case. In user-visible changes, green evidence can auto-approve unless risk flags require escalation. **There is no path that lets a user-visible change reach handoff without explicit verification evidence.**

If `record_delivery_audit` has no configured adapter or the adapter fails,
continue to Phase 12 after appending warning or failed receipt events, updating
local work-item history, and marking external sync `pending` or `failed`.

## Phase 11 — QA Health Update

If Phase 6 was skipped (qa-foundation not run), skip this phase.

If `qa-gates` result was `passed === false`, skip this phase (health update only runs on green builds).

Otherwise:

Invoke `qa-planner` with `mode: "--update"`, `run_dir`, and `merge_base`.

No gate — always completes. Updates `.agentic/guides/testing/qa-health.md` with coverage changes from this run.

## Phase 12 — Handoff

- HITL: print `Branch <branch> ready. Invoke mr-creator (or your preferred PR tool) to open the pull request.`
- Autonomous: print `Branch <branch> ready. Invoke mr-creator manually to commit, push, and open the pull request.`

Before printing handoff, emit `complete_or_handoff` with the branch, work item,
requirements, plan, QA report, verification evidence, and latest lifecycle
receipt artifacts. Missing or failed adapters do not block handoff; append local
history and warning or failed receipt events, then include the external sync
state in the handoff message.

Update `meta.json.status = "completed"` and set every `phases[N].status = "completed"`.
Update `<run_dir>/work-item.md` and the canonical local work item status to
`Ready for review`, append `work_item.transitioned`, and link the final branch,
QA report, verification evidence, and SDLC report as available. This handoff
history is what `mr-creator` uses when it later records the MR/PR URL.

---

## Artifact summaries (token-efficiency contract)

Gate calls to `decision-router` MUST pass `ArtifactRefs` rather than full file bodies. Shape:

```
ArtifactRefs = [{
  "kind":      "spec" | "plan" | "diff" | "qa-report" | "evidence",
  "path":      "<absolute path inside run_dir or repo>",
  "summary":   "<extract, hard-capped at 2 KB per artifact>",
  "signature": "<sha-256 of the file contents>"
}]

Total summary budget per gate: ~6 KB across all artifacts.
```

Stand-ins read `path` directly when they need full content. The `summary` is the cheap default; the `signature` lets a stand-in detect that the file changed since the summary was extracted (and re-read if so).

The pipeline NEVER inlines a multi-page spec or plan into the gate prompt. Per-gate context stays bounded.

---

## Memory writes (semantic events)

After each emitted semantic event, if `config.memory.auto_write_on` includes the event name, append a curated entry to `.agents/memory/sdlc/`:

| Event | Type | Content |
|-------|------|---------|
| `spec.approved` | `project` | Architectural decisions captured in the design doc |
| `plan.approved` | `project` | Key constraints / shared fixtures discovered during planning |
| `feature.verified` | `feedback` | Browser verification gotchas — only if a verification retry was needed this run |
| `qa.passed` | `feedback` | Recurring class of issue, only if observed in `code-review` retries this run |

Daily log entries (`.agents/memory/sdlc/daily/<date>.md`): one line per phase boundary, plus one line on each `code-review` retry.

## Constraints

- Never re-implement logic that lives in superpowers; always call those skills.
- Claude and Codex hosts always use feature branches in the current checkout; never create git worktrees.
- Never block the pipeline on `decisions.jsonl` write failures.
- All file IO is via Read/Write/Edit tools; no shell-out for file reads.
- `memory_brief` is read ONCE (Phase 0) and propagated; do not re-read mid-run.
- Gate calls always pass `ArtifactRefs`, never raw file bodies.
- Phase status transitions are atomic — write to `meta.json` after each phase completes, not periodically.
- **Run isolation**: every run is completely isolated. Never read, copy, reference, or adopt artifacts from sibling run directories (`docs/superpowers/runs/<other-run-id>/`). Each phase must produce its own outputs from scratch. Prior run artifacts are not a substitute for running the phase that produces them.
- **No cross-run adoption**: never copy or symlink `design.md`, `plan.md`, `requirements.md`, `complexity.json`, or any phase artifact from a prior run into the current `<run_dir>`. Existence of a prior run for the same work item does not skip or short-circuit any phase.
