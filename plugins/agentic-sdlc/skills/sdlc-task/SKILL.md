---
name: sdlc-task
description: |-
  The lightweight orchestrator for tasks the user has already sized as XS/S/M. It sits alongside sdlc-start and sdlc-autonomous but skips complexity scoring, per-task subagents, and evidence files: brainstorm-lite → spec → plan → inline TDD → one code-review round → qa-gates, all on the current feature branch. spec.md and plan.md live under docs/superpowers/tasks/<slug>/, and mode: sync reconciles them with whatever changed after the initial run.
version: 0.1.0
license: Apache-2.0
discoverable: false
authors:
  - agentic-os
---

# sdlc-task

A stripped-down entry point into the SDLC flow, meant for work the user has already sized as XS, S, or M — small enough that running the full `sdlc-pipeline` would cost more ceremony than it's worth.

## Why this skill exists

`sdlc-pipeline` earns its keep on medium-to-large tickets: it loads the doctor check and memory, normalizes requirements, sets up a feature branch, scores complexity, conditionally writes a spec, writes a plan, hands implementation to subagents, runs two rounds of code review, runs mechanical QA, verifies the feature, and hands off — with every phase leaving durable artifacts behind.

For two kinds of work the user already knows is small, that's overkill:

- **XS / S tasks** — a one-file change, a renamed parameter, a single new validator. Running the full pipeline against these still means feature-branch setup, complexity scoring, plan writing, per-task subagents, evidence-file validation, a code-review bundle, and qa-gates.
- **M tasks the user has already scoped mentally** — a small endpoint with TDD coverage, a focused refactor with a clear acceptance bar. Nobody needs a stand-in tech lead re-confirming what the user already knows.

Two specific costs justify a lighter path:

1. **Ceremony overhead.** Even the smallest run under the full pipeline spins up a run-dir plus a `meta.json` tracking all 10 phase slots, alongside several artifact files — overkill for something that takes 30 minutes.
2. **Per-task subagent overhead.** `superpowers:subagent-driven-development` spins up a separate subagent for every plan task. A 3-task XS run means 3 subagent launches, 3 reloads of project context, and 3 round-trips through evidence files — all before code review even begins. Doing TDD inline, in the same conversation, avoids that overhead and keeps the model's grasp of the project warm.

## Scope

`sdlc-task` is one of three ways into `agentic-sdlc`. It sits alongside `sdlc-start` and `sdlc-autonomous` without replacing or altering either of their flows. Picking the right one is always a human call:

| Use | Entry point |
|---|---|
| Ticket-sized work, ambiguity expected, full audit trail wanted | `sdlc-start` |
| Ticket-sized work, low-touch automation, audit trail | `sdlc-autonomous` |
| User has already classified the task as XS / S / M and wants minimum ceremony | `sdlc-task` |

There's no built-in complexity classifier here on purpose — choosing this entry point *is* the user's classification.

If the task description smells heavier than XS/S/M (say, an external ticket id combined with risk words like `security`, `auth`, `migration`, `breaking`), surface a one-line nudge toward `sdlc-start` but keep going regardless. Never refuse the request outright.

## Inputs

- `task_description` — the user's free-form description of what to build
- `mode` — `main` (default; runs the full flow from Stage 0) or `sync` (reconciles artifacts only; requires an existing `<task-dir>` with `.state.json.phase === "maintenance"`)
- `slug` — optional override; defaults to `kebab-case(task_description)` truncated to 50 chars
- `ui` — boolean, default `false`

## Entry Points

- Main mode: invoke this skill with `mode: "main"` and a `task_description`.
- Sync mode: invoke this skill with `mode: "sync"` to reconcile artifacts after maintenance changes.
- Any coding-agent host that supports the Skill mechanism can call `sdlc-task` with the inputs above.

## Run state

This skill tracks state in exactly one file: `<task-dir>/.state.json`:

```json
{
  "schema": 1,
  "slug": "<slug>",
  "branch": "<current branch>",
  "phase": "main | maintenance",
  "started_at": "<ISO>",
  "completed_at": "<ISO, set at Stage 11>",
  "last_sync_commit": "<HEAD sha at the moment of the last sync>"
}
```

There's no `meta.json`, no per-phase status slots, no per-task evidence files — the conversation transcript stands in as the record of everything else.

`<task-dir>` resolves to `docs/superpowers/tasks/YYYY-MM-DD-<slug>/`, with `YYYY-MM-DD` set to the UTC date of the initial Stage 1 invocation (technical research). Judgment gates that go through `decision-router` may add `decisions.jsonl` and `events.jsonl` to this same directory as their audit trail.

### Branch guard contract

`sdlc-task` MUST run a lightweight branch guard in the current checkout before Stage 3 brainstorming/spec work and before Stage 6 implementation touches any files. The overall flow is HITL-only, but the guard is still needed to stop small tasks from getting tangled up with unrelated local changes.

The guard needs to inspect the repository for:

- Inspect the current branch with `git branch --show-current`.
- Read the configured base branch from `.agentic/guides/standards/git-workflow.md` when available; otherwise use the repository default branch and fall back to `main`.
- Inspect dirty working tree state with `git status --porcelain`, including untracked files.
- Inspect upstream state for the current branch: ahead, behind, or diverged.
- Confirm whether the target branch exists when the user asks to switch/create a named feature branch.

When the working tree is dirty, the choices offered to the user are:

- `stash`: stash the existing dirty working tree before continuing.
- `commit first`: stop and let the user commit the existing work before the task continues.
- `hard reset`: only run a destructive reset after explicit user confirmation that names the branch and acknowledges data loss.
- `proceed with the existing dirty state`: continue only after warning that unrelated changes may be mixed into the task.
- `abort`: stop before writing the task spec, plan, tests, or implementation.

Handling a stale base or an existing target branch:

- If the current branch is the configured base branch, refresh it when network access and policy allow: fetch, fast-forward only, then verify `git status --porcelain` is clean before creating a feature branch.
- If the requested target branch already exists, inspect its unique commits and local changes before continuing. A clean existing feature branch may be reused; a dirty, stale, ahead-only, behind, or diverged branch requires an explicit user choice to continue, recreate, reconcile, or abort.
- `sdlc-task` isn't meant to run autonomously. If a host tries to drive it without HITL prompts while the tree is dirty or the branch choice is unclear, it should halt rather than auto-stash, hard-reset, or push ahead dirty.

## HITL Judgment Gates

Being HITL-only doesn't mean skipping `decision-router` — approval and review decisions still flow through it. The router's job at these gates is to ask the user; it must never fall back to an autonomous fast-path, a deterministic approval, or a stand-in subagent's approval.

Route these gates through `decision-router` with `mode: "hitl"`, `run_dir: <task-dir>`, and bounded `ArtifactRefs`:

- Spec approval after Stage 3 writes `spec.md`: `spec.approved`
- Plan approval after Stage 4 writes `plan.md`: `plan.approved`
- Review decisions in Stage 8: `code-review.final`, then `code-review.check` only if changes were requested
- Blocking validation or feature-verification evidence in Stage 9: `feature.verification`

Clarifying-question caps from helper skills only bound how many ambiguity prompts get asked — they can never turn spec approval, plan approval, review, or a blocking verification gate into an automatic approval.

---

## Flow

The flow runs across twelve stages: Stage 0 is a cheap pre-flight check, Stages 1–10 execute in the current conversation context, and Stage 11 hands off.

### Stage 0 — Pre-flight

1. Read `.agentic/agentic-sdlc/doctor.json` if present. Apply the same TTL + fingerprint rule as `sdlc-pipeline` Phase 0 (default 7 days). If the file is missing OR `checked_at` is older than the TTL OR the fingerprint mismatches, run the minimum subset of doctor checks: confirm `superpowers:brainstorming` is resolvable (Skill discovery) and `git --version` works. Rewrite the cache file.
2. If superpowers can't be resolved, print:

   ```
   sdlc-task requires the superpowers plugin (>= 5.0.7).
   Install: /plugin marketplace add obra/superpowers && /plugin install superpowers
   ```

   and HALT.
3. Skip the heavy memory load entirely — do NOT read `.agents/memory/sdlc/`; that belongs to the heavy pipeline.
4. Run the branch guard contract: inspect current branch, configured base branch, `git status --porcelain`, upstream ahead/behind/diverged state, and target branch existence when applicable. Resolve any dirty working tree or branch ambiguity before continuing.
5. Confirm the current checkout is on a feature branch. Claude and Codex hosts MUST NOT create worktrees. If the current branch is the configured base branch, ask the user for a feature branch name and switch/create that branch only after the latest-base check passes.

### Stage 1 — Technical Research

Once pre-flight clears, make sure `technical-analysis.md` exists in the task directory — read and reuse it if it's already there (say, left over from an interrupted run or generated by hand), otherwise dispatch the `tech-analyst` agent to produce it.

1. If `mode === "sync"`, skip this stage entirely (sync mode does not re-research).
2. Create `<task-dir>` (`docs/superpowers/tasks/YYYY-MM-DD-<slug>/`) if it does not already exist.
3. **Check for existing research**: attempt to read `<task-dir>/technical-analysis.md`.
   - **File exists**: read its content, confirm it is non-empty and contains the expected sections (at minimum: "Codebase Findings" and "Risk Indicators"). If valid, skip to Stage 2 — the research is already done.
   - **File not found or empty/malformed**: proceed to step 4 to generate it.
4. Pull 2–4 domain keywords out of `task_description` as `feature_area` — enough to pin down the affected area (e.g. `auth oauth admin`, `datasource indexer sharepoint`).
5. Dispatch the `tech-analyst` agent with:
   - `task_context`: the user's `task_description` verbatim
   - `feature_area`: the extracted keywords
   - `run_dir`: `<task-dir>`
6. **Wait for tech-analyst to complete** before doing anything else — it's responsible for writing `<task-dir>/technical-analysis.md`, and Stage 2 must not start until that's done.
7. If the agent comes back with "Research Blocked — Ticket Content Not Resolved" (meaning `task_description` was just a ticket ID with no real requirements behind it), surface that blocker to the user and ask for the ticket description or acceptance criteria before moving on. Actionable requirements are a prerequisite, not optional.

### Stage 2 — Complexity Assessment

Once tech-analyst has finished and `technical-analysis.md` is confirmed on disk, dispatch the `complexity-assessor` agent and **wait for it to complete**.

1. If `mode === "sync"`, skip this stage entirely.
2. Check for existing assessment: attempt to read `<task-dir>/complexity-assessment.md`.
   - **File exists and non-empty**: read it and proceed to Stage 3.
   - **File not found**: dispatch and wait.
3. Dispatch the `complexity-assessor` agent with:
   - `task_description`: a one-sentence summary of `task_description`
   - `feature_area`: the extracted `feature_area` keywords
   - `run_dir`: `<task-dir>`
4. Wait for the agent to finish — it writes `<task-dir>/complexity-assessment.md`.
5. Read `<task-dir>/complexity-assessment.md` and share the routing verdict with the user. A `SPLIT REQUIRED` routing means presenting the splitting recommendation and halting — brainstorming doesn't start until the user hands back decomposed stories.

The complexity assessment keeps brainstorming honest about effort — whatever spec and plan come out of Stages 3–4 should line up with the assessed size.

### Stage 3 — Brainstorm and write spec

1. If `mode === "sync"`, skip to the **Sync-on-trigger** section below.
2. Invoke `superpowers:brainstorming` with the user's `task_description`, passing both `<task-dir>/technical-analysis.md` and `<task-dir>/complexity-assessment.md` as extra context so it's grounded in real codebase findings and sizing rather than guesswork.
3. Brainstorming runs its normal short-form flow — it already scales itself down for small tasks — and clarifying questions stay owned by brainstorming.
4. Once brainstorming produces a design, write it to `<task-dir>/spec.md`.
5. Call `decision-router` with `gate_id: "spec.approved"` and the spec as an ArtifactRef. On `request-changes`, apply the user's follow-ups through the affected brainstorming step and rewrite `spec.md`. On `abort`, stop.
6. Write/initialize `<task-dir>/.state.json` with `{schema: 1, slug, branch, phase: "main", started_at: <ISO>}`.
7. Should brainstorming abort, the skill aborts too and writes nothing — the user's `task_description` simply stays in the conversation for a later attempt.

### Stage 4 — Plan

1. Invoke `superpowers:writing-plans` with `<task-dir>/spec.md` as the spec input. When `<task-dir>/technical-analysis.md` exists, pass it alongside the spec so the planner can lean on codebase findings — existing implementations, testing patterns, integration points, risk indicators.
2. Every implementation task in the resulting plan MUST carry a `Test-first: yes/no — <failing test description>` line — the same contract `sdlc-pipeline` Phase 5 enforces, which keeps plans portable across entry points.
3. Write the plan to `<task-dir>/plan.md`.
4. Call `decision-router` with `gate_id: "plan.approved"` and the plan as an ArtifactRef. On `request-changes`, feed the user's follow-ups back into `superpowers:writing-plans` and rewrite `plan.md`. On `abort`, stop.

### Stage 5 — QA Checklist

If `.agentic/guides/testing/qa-strategy.md` does not exist, skip this stage and log: "QA knowledge foundation not found — skipping qa-planner. Run the `qa-foundation` skill to enable QA-guided development."

Otherwise:

Invoke `qa-planner` with `mode: "--checklist"`, `run_dir: <task-dir>`, and `merge_base`.

Store `checklist_path` (`<task-dir>/qa-checklist.md`) in local state. Pass it to Stage 6 so inline TDD can reference checklist scenarios.

Gate: `qa-checklist.approved` (called inside `qa-planner`; wait for resolution before entering Stage 6).

### Stage 6 — Implement inline

1. Invoke `superpowers:test-driven-development` in the current conversation. **Do not dispatch a subagent.** If `checklist_path` is available from Stage 5, read `qa-checklist.md` and align failing-test descriptions with checklist scenarios for affected files.
2. Create one `TodoWrite` item per plan task. Transition each to `in_progress` when starting and `completed` immediately after.
3. For each task: write the failing test, run it (RED visible in the transcript), implement the minimum needed to pass, run again (GREEN visible), refactor if needed.
4. Do NOT write `evidence/<task-id>.json` files. The transcript is the receipt.
5. Commit per task or per logical group, using the host repo's commit conventions. If the repo uses Conventional Commits or a ticket-id prefix, follow that; do not impose a new convention.
6. Commit messages should reference `<slug>` and the plan task id.

### Stage 7 — QA Test Review

If Stage 5 was skipped (qa-foundation not run), skip this stage.

Otherwise:

Invoke `qa-planner` with `mode: "--review-tests"`, `run_dir: <task-dir>`, and `merge_base`.

On `approve`: continue to Stage 8.
On `request-changes`: fix the high-severity findings inline in the current conversation. Re-invoke `qa-planner --review-tests` once after the fix. If still `request-changes` after the single retry, escalate to the user. Maximum 1 retry.

### Stage 8 — Code review (one round + one fix-up)

1. Call `decision-router` with `gate_id: "code-review.final"`. Pass ArtifactRefs (paths + 2 KB summaries + sha-256):

   ```json
   {
     "spec":         {"kind": "spec",         "path": "<task-dir>/spec.md",          "summary": "<2KB extract>", "signature": "<sha-256>"},
     "plan":         {"kind": "plan",         "path": "<task-dir>/plan.md",          "summary": "<2KB extract>", "signature": "<sha-256>"},
     "diff":         {"kind": "diff",         "path": "<git diff <base>...HEAD output>", "summary": "<diffstat + risk flags>", "signature": "<sha-256>"},
     "qa-checklist": {"kind": "qa-checklist", "path": "<task-dir>/qa-checklist.md", "summary": "<N blocking scenarios>", "signature": "<sha-256>"}
   }
   ```

   Omit `qa-checklist` if Stage 5 was skipped.

2. On `approve` → continue to Stage 9.
3. On `request-changes`: fix the findings inline in the current conversation. Preserve the original finding IDs for the follow-up check.
4. If a fix-up was made, call `decision-router` with `gate_id: "code-review.check"` and ArtifactRefs for the original findings, fix-up diff, and commands/evidence from the fix. If the second round still returns `request-changes`, escalate through that HITL verdict and do NOT run a third automated round.
5. On malformed JSON output from any helper, route the raw output through `decision-router` for a HITL decision.

No code-review subagent approves or rejects the task in HITL mode; the user verdict recorded by `decision-router` is authoritative.

### Stage 9 — Validate

1. Invoke the existing `qa-gates` skill with:
   - `branch`: the current branch
   - `merge_base`: `origin/main` if unset
   - `repo_path`: the repo root
   - `run_dir`: `<task-dir>` — passing the task directory as `run_dir` is what causes qa-gates to write `qa-report.md` and `gate-plan.json` under the task directory rather than a separate runs dir.

2. If `ui === true` AND the diff touches a user-visible surface (use the `ui_globs` cached in `gate-plan.json`), invoke `feature-verification` with the same `run_dir`. Otherwise skip feature-verification regardless of diff content.

3. On `qa-gates` returning `passed: false`: print the blocked-gate detail, route the blocking validation through `decision-router` with `gate_id: "feature.verification"` and the QA report/gate plan as ArtifactRefs, then re-invoke `qa-gates` after the user-selected fix path. Maximum 3 retries before escalating with the message `qa-gates blocked after 3 fix attempts; review needed.`

4. On `passed: true`: continue to Stage 10.

### Stage 10 — QA Health Update

If Stage 5 was skipped (qa-foundation not run), skip this stage.

If Stage 9 `qa-gates` returned `passed: false`, skip this stage (health update only runs on green builds).

Otherwise:

Invoke `qa-planner` with `mode: "--update"`, `run_dir: <task-dir>`, and `merge_base`.

No gate — always completes. Updates `.agentic/guides/testing/qa-health.md` with coverage changes from this task.

### Stage 11 — Handoff

1. Write/overwrite `<task-dir>/.state.json`:

   ```json
   {
     "schema": 1,
     "slug": "<slug>",
     "branch": "<current branch>",
     "phase": "maintenance",
     "started_at": "<ISO from Stage 1>",
     "completed_at": "<ISO>",
     "last_sync_commit": "<HEAD sha>"
   }
   ```

2. Print:

   ```
   Task <slug> ready on branch <branch>.
   Spec: <task-dir>/spec.md
   Plan: <task-dir>/plan.md
   QA report: <task-dir>/qa-report.md
   Invoke `mr-creator` (or your preferred PR tool) when ready.
   ```

---

## Phase-aware updates during the run

User redirections mid-flow update only the artifact for the current phase. The skill never silently edits `spec.md` when only `plan.md` is affected, and asks before editing `spec.md` from the plan phase.

| Current stage | User says "actually X" | Skill does |
|---|---|---|
| Stage 3 (brainstorm) | "I also want it to handle Y" | Edit `spec.md`; re-run the affected brainstorming step |
| Stage 4 (plan) | "Re-order the tasks" / "Add a task" | Edit `plan.md`; do not touch `spec.md` |
| Stage 4 with requirement implication | "Add validation Z" | Edit `plan.md` AND `spec.md` (confirm with the user before touching `spec.md`) |
| Stage 6 (implement) | "Change the validator to do Z" | Edit `plan.md` (current task body); mark already-completed tasks for redo only if their behavior is invalidated |
| Stage 8 (review) | Reviewer flagged a finding | Fix inline; no spec/plan edit unless the finding implies a behavior change |
| Stage 9 (validate) | qa-gates failed | Fix inline; no artifact edit |

---

## Sync-on-trigger after the run

Once Stage 11 has run, `<task-dir>/.state.json.phase === "maintenance"`. The skill behaves as follows on subsequent functional changes in the same (or later) conversation:

1. Implement the change inline as a normal TDD micro-task. Commit normally.
2. Do **NOT** touch `spec.md` or `plan.md`.
3. After every turn that produces a new commit, compare `HEAD` to `.state.json.last_sync_commit`. If they differ, print exactly one line at end of turn:

   ```
   spec/plan drifted from impl - invoke sdlc-task with mode: "sync" before PR
   ```

### When the user invokes this skill with `mode: "sync"`

1. Verify `<task-dir>/.state.json.phase === "maintenance"`. If not, refuse with:

   ```
   sync requires an existing task in maintenance mode; nothing to do.
   ```

   (Determine `<task-dir>` from the most recent `docs/superpowers/tasks/*` directory whose `.state.json.phase === "maintenance"`. If multiple match, ask the user via `AskUserQuestion` which slug to sync.)

2. Read the diff between `.state.json.last_sync_commit` and `HEAD`.
3. Read the current `spec.md` and `plan.md`.
4. Rewrite both artifacts to reflect the post-completion state. Preserve the original section structure. Do NOT append a change-log section inside the spec. Use `superpowers:writing-clearly-and-concisely` if available; otherwise edit inline with clear, concise prose.
5. Show the user a unified diff of the proposed artifact changes via `AskUserQuestion` with options `apply | reject | request-edit`.
6. On `apply`: write both files, update `.state.json.last_sync_commit = HEAD`, print `Artifacts synced through commit <sha>.`
7. On `reject`: discard the proposed changes; leave state unchanged.
8. On `request-edit`: take the user's instruction, regenerate the proposed artifacts, re-prompt.

**Idempotency:** Running sync mode twice in a row is a no-op the second time because `last_sync_commit === HEAD` after the first apply.

---

## Failure handling

| Failure | Behavior |
|---|---|
| Brainstorming aborts | Skill aborts; no files written |
| Plan writing aborts | Skill aborts; `spec.md` remains for re-entry on the same slug |
| TDD test refuses to fail | Stop the task; HITL prompt: "The test passed without implementation. Re-think the test or skip Test-first for this task?" |
| Code-review helper returns malformed JSON | `decision-router` HITL prompt with the raw output |
| `code-review.check` still requests changes | Escalate to user; do not auto-loop |
| qa-gates blocks on missing runner | Follow `qa-gates`' own ask-once-then-cache flow |
| User Ctrl-C mid-stage | `.state.json` retains the current phase; running the same `<slug>` again re-enters that phase from scratch |

---

## What this skill deliberately does NOT do

- No complexity assessment. The user chose this skill because they already know the task is small.
- No `meta.json` with phase slots. `.state.json` holds only what the sync mechanic needs.
- No full pipeline run ledger. Decision gates may still append `decisions.jsonl` and `events.jsonl` through `decision-router`; git commits + the conversation transcript remain the lightweight audit trail.
- No worktrees. Claude and Codex hosts always use feature branches in the current checkout.
- No memory load. The user has the context.
- No stand-in approval. HITL only; judgment gates route through `decision-router` and the user is driving the conversation.
- No per-task evidence files. The transcript is the receipt.
- No feature-verification by default. Opt-in via `--ui`.

---

## Artifact paths

```
docs/superpowers/tasks/YYYY-MM-DD-<slug>/
├── technical-analysis.md    ← from Stage 1 tech-analyst agent
├── complexity-assessment.md ← from Stage 2 complexity-assessor agent
├── spec.md                  ← from Stage 3, edited live, rewritten by sync mode
├── plan.md                  ← from Stage 4, edited live, rewritten by sync mode
├── qa-checklist.md          ← from Stage 5 qa-planner --checklist (if qa-foundation run)
├── qa-test-review.md        ← from Stage 7 qa-planner --review-tests (if qa-foundation run)
├── .state.json              ← phase + last_sync_commit, owned by this skill
├── qa-report.md             ← from Stage 9 qa-gates (run_dir = <task-dir>)
└── gate-plan.json           ← cached gate plan from qa-gates
```

If `--ui` was set and Stage 9 invoked `feature-verification`, that skill adds `feature-verification-plan.json` and `evidence/verification/*.json` under `<task-dir>`. None of those are created when `--ui` is off.

---

## Constraints

- Never re-implement behavior that already lives in `superpowers` or in the sister `agentic-sdlc` skills (`qa-gates`, `feature-verification`); call them.
- Never load `.agents/memory/sdlc/` (that is the heavy pipeline's job).
- Never create a git worktree.
- Never write a `meta.json` or per-task `evidence/*.json`. `.state.json` is the only state file owned directly by this skill; `decision-router` owns any `decisions.jsonl` or `events.jsonl` gate audit entries.
- All file IO via `Read` / `Write` / `Edit`; never shell out for file reads.
- Code-review decisions route through `decision-router` at most twice per run (initial + one fix-up check). Never a third automated round.
- If the user passes an external ticket id that matches risk keywords (`security`, `auth`, `migration`, `breaking`), print one-line nudge: `Heads-up: this task looks like it might need sdlc-start. Proceeding with sdlc-task because that's what you asked for.` Do not refuse.
