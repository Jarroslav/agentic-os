---
name: babysit-mr
description: >-
  Keeps watch over an open MR or PR and clears whatever is blocking its merge on
  its own: failing CI, requested changes, merge conflicts. Polls roughly every
  180s, applies fixes, and pushes — until it merges, closes, or the user calls
  it off. Use whenever an MR or PR needs unattended monitoring — trigger on "watch
  the MR", "babysit this PR", "monitor MR !123", "keep an eye on the merge
  request", or when a prior skill just opened one and should hand off here.
  Adapter-driven, no source-control platform hardcoded. Reach for this any time
  the user wants hands-off MR/PR management.
version: 1.0.0
authors:
  - agentic-os
---

# MR Babysitter

Sit on an open MR or PR in a repeating loop, fixing CI failures, working through reviewer
comments, and clearing merge conflicts, until it either merges or gets closed.

## Input

Accept any of:
- Full MR or PR URL (any VCS platform)
- Short form reference (e.g. `!123` for GitLab-style, `#123` for GitHub-style)
- Bare number when context makes the repo clear: `123`

Extract the project path and MR or PR ID from whatever was given.

## Adapter Resolution

1. Read `.agentic/guides/project.md` → `## MR Adapter` section. Use the declared adapter and instructions if status is `configured`.
2. If not configured, try to work out the adapter from the MR or PR URL or `git remote get-url origin`.
3. If it's still unclear, ask the user what tool manages MRs and PRs for this project.

Load `references/mr-adapters.md` for the adapter contract.

## Prerequisites

Confirm the resolved adapter is authenticated and reachable. If it isn't installed or isn't
authenticated, tell the user what needs installing or configuring and exit.

## Main Loop

Keep looping until something terminal happens. Between iterations: `sleep 180`.

Safety limit: once **10 iterations** have passed with nothing resolved, pause and check with the
user whether to keep going — an MR or PR that's still stuck at that point likely needs a human.

### Step 1 — Check MR or PR State

Call the adapter's **state** operation to get the current state. Terminal conditions:

| State | Action |
|-------|--------|
| `merged` | Print success summary, exit |
| `closed` | Print closure notice, exit |
| User says "stop" / "cancel" | Exit immediately |

### Step 2 — Check CI/CD Pipeline

Call the adapter's **ci-status** operation and branch on what comes back:

- `running` / `pending` — continue to Step 3 (do not skip — rebase must still run)
- `failed` → go to **CI Failure Handling**
- `passed` or no pipeline → continue to Step 3

### Step 3 — Check Unresolved Discussions

Keep `last_seen_discussion_ids` across iterations so old threads aren't processed twice.

Call the adapter's **discussions** operation to list unresolved, non-system comments.

For each newly-unresolved comment:
- **Code change requested** → implement it (see **Comment Handling**)
- **Question** → post a reply answering it using the adapter's **comment** operation
- **Informational / bot** → skip

### Step 4 — Check Rebase / Merge Conflicts

**Run this step every time**, even when the pipeline is still running or pending.

Call the adapter's **state** operation (or a dedicated merge-status field where one exists) to
detect:
- Branch behind target → **Rebase Handling**
- Merge conflicts present → **Conflict Handling**

### Step 5 — Wait

`sleep 90`, then loop back to Step 1.

---

## CI Failure Handling

### 1. Fetch failure details

Start with MR or PR comments via the adapter's **discussions** operation — CI bots usually drop
failure summaries there. If that's not enough to go on, use the adapter's **ci-status** operation
to pull the job/run log (where supported).

### 2. Classify and fix

| Type | Action |
|------|--------|
| Lint / style / type errors | Fix the offending lines |
| Failing unit tests | Fix the code (not the test, unless the test is clearly wrong) |
| Build / compile errors | Fix missing imports, compilation errors |
| Transient / flaky (no code change needed) | Post a retrigger comment via the adapter's **comment** operation |
| Unknown | Report to user, pause loop |

For code fixes: keep the change minimal, don't refactor surrounding code while you're in there.

Get the ticket prefix from `git log --oneline -5`, then:
```bash
git add <changed_files>
git commit -m "<TICKET_ID>: Fix <lint|test|build> failure in CI"
git push
```

After retriggering, give the pipeline ~20s to start, then resume from Step 1.

If the **same job fails twice in a row** despite an attempted fix, stop and hand it back to the user.

---

## Comment Handling

For each unresolved reviewer comment that asks for a code change:

1. Read the full thread to get the context.
2. Make the requested change.
3. Reply to the thread using the adapter's **comment** or reply operation:
   `"Done — addressed in the latest commit."`
4. Bundle every comment fix from the current iteration into a single commit:

```bash
git add .
git commit -m "<TICKET_ID>: Address reviewer feedback"
git push
```

---

## Rebase Handling

Call the adapter's **target-branch** operation to get the target branch name. Then:

```bash
git fetch origin "<TARGET_BRANCH>"
git rebase "origin/<TARGET_BRANCH>"
```

Push with `git push --force-with-lease` (never plain `--force`). If the rebase turns up conflicts,
drop into **Conflict Handling**. Once the push succeeds, wait ~10s and resume from Step 1.

---

## Conflict Handling

Call the adapter's **target-branch** operation to get the target branch, then:

```bash
git fetch origin "<TARGET_BRANCH>"
git rebase "origin/<TARGET_BRANCH>"
```

Work out the conflict resolution from context. Stage the resolved files and run
`git rebase --continue`.

Push with `git push --force-with-lease` (never plain `--force`).

If the conflicts are too tangled to resolve automatically (both sides changed overlapping logic
in the same function), stop and list the conflicting files for the user.

---

## Loop State

Carry these across iterations:
- `last_pipeline_id` — skip re-diagnosing the same failed pipeline
- `last_seen_discussion_ids` — skip already-processed comments
- `iteration_count` — enforce the 10-iteration safety limit
- `consecutive_same_failure_count` — detect stuck CI loops

---

## Summary Report

Once the loop ends, always print:

```
MR or PR <ID> — <merged | closed | stopped by user>

Iterations: <N>
Actions taken:
  - CI failures fixed: <count> (<types>)
  - Reviewer comments addressed: <count>
  - Rebases performed: <count>
  - Merge conflicts resolved: <yes | no>

Final URL: <MR or PR URL>
```

## Write Run Journal

After printing the Summary Report, read `.agentic/runs/<branch>.json` where
`<branch>` is the current branch. Create the file if it doesn't already exist.

Append or update its entry:

```json
{
  "step": "07",
  "agent_skill": "babysit-mr",
  "primitive": "skill",
  "started_at": "<ISO8601 start time>",
  "completed_at": "<ISO8601 now>",
  "status": "completed",
  "outcome": "MR or PR <ID> <merged | closed | stopped>. Iterations: <N>. CI fixes: <N>. Reviewer comments addressed: <N>.",
  "artifacts": ["<MR or PR URL>"],
  "next_step": "knowledge-enrichment"
}
```

Write the file before presenting the handoff prompt.

## Handoff

```
---
✅ babysit-mr complete.

**Outcome**: MR or PR <ID> <merged | closed | stopped after N iterations>.

**Recommended next step**: dispatch `knowledge-enrichment` — update .agentic/guides/ if structural changes were introduced

How would you like to proceed?
- **yes / proceed** → I'll dispatch `knowledge-enrichment` now
- **no / skip** → stop here, I'll wait for your instruction
- **other** → tell me what to do instead
```
