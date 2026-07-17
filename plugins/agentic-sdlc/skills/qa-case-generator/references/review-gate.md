# Phase 6 — User Review Gate

The mandatory human checkpoint between generation (Phase 5) and sync (Phase 7). No case leaves the run for an external test-management system until a person signs off here.

> The gate has no autonomous fast-path. There is no auto-approve, no confidence-based bypass, no timeout-defaults-to-yes. A human verdict is required to advance. Sync is the only step that reaches outside the repo (blast radius R3), so it stays behind this gate every time.

Dispatched by `phase-implementations.md` as the Phase 6 entry. On approval, hands control forward to `phase-7-test-management-sync.md`.

---

## Inputs

You arrive here with Phase 5 output already on disk:

| Input | Location |
|---|---|
| Generated cases | `docs/superpowers/qa-tasks/<date>-<slug>/manual/test_cases.md` |
| Run metadata | `meta.json` (same run directory) |

Read both before presenting anything. The summary is derived from the cases file; the counters you mutate live in `meta.json`.

---

## Step 1 — Build the summary

Compute counts from the cases file, then print exactly this block. Field placeholders are filled from the run; every literal line and label is fixed.

```
📋 Test Case Summary for <TICKET_ID>
Total: <count> test cases
- P1: <p1_count>, P2: <p2_count>, P3: <p3_count>
- UI: <ui_count>, API: <api_count>
Location: docs/superpowers/qa-tasks/<date>-<slug>/manual/test_cases.md
Sample P1 Test: <title>
Sample P2 Test: <title>
Sample P3 Test: <title>
```

What the reviewer needs to judge scope at a glance:

- **Ticket id** — what this batch belongs to.
- **Total count** — volume sanity check.
- **Priority split** — one line for P1/P2/P3.
- **Type split** — one line for UI/API.
- **Artifact path** — where the full detail lives if they want to open it.
- **One sample title per tier** — a spot-check of P1, P2, and P3 titles so quality is visible without reading the file.

---

## Step 2 — Collect the verdict

Prompt with the `AskUserQuestion` tool. Offer exactly three options, labelled:

**Approve** / **Rework** / **Abandon**

| Verdict | Meaning | Next action |
|---|---|---|
| Approve | Cases are good to sync | Advance to Phase 7 |
| Rework | Cases need adjustment | Enter the rework loop (Step 3) |
| Abandon | Stop, keep nothing synced | Persist as draft, exit |

### Approve

Emit the completion block with `Status: approved`, then load `phase-7-test-management-sync.md` and continue. (If no test-management adapter is configured, Phase 7 is skipped entirely — approval still stands; there is simply nothing to sync.)

### Abandon

The work is not discarded — the artifacts stay on disk as a draft. Mark the run so downstream tooling knows sync was deliberately declined:

- In `meta.json`, set `"sync_status": "abandoned"`.
- Emit the completion block with `Status: abandoned`.
- Exit the pipeline. Do not proceed to Phase 7.

---

## Step 3 — Rework loop

Rework is a bounded feedback cycle, not a restart. Each iteration regenerates against the parsed intent, re-presents the summary, and asks again.

### Parse feedback by keyword intent

Read the reviewer's free-text feedback and map it to an adjustment:

| Feedback contains | Intent |
|---|---|
| `more` / `add` / `increase` | raise coverage |
| `less` / `reduce` / `remove` | lower coverage |
| `format` / `Gherkin` | change output format |
| `focus on` | shift content emphasis |

Feedback may carry more than one intent; apply all that match.

### Regenerate and re-present

Each rework iteration:

1. Regenerate the cases using the adjusted parameters (same generation logic as Phase 5).
2. Increment `regeneration_count` in `meta.json`.
3. Rebuild and reprint the summary block (Step 1).
4. Re-prompt for a verdict (Step 2).

The loop closes only when the reviewer picks **Approve** or **Abandon**.

### Cap

Past 3 rework cycles, warn the reviewer that repeated churn usually signals the acceptance criteria themselves are ambiguous or unstable — the generator can only be as sharp as its inputs. This is a warning, not a stop: do **not** hard-halt. The reviewer may keep iterating, approve, or abandon.

> When cases won't converge, the fix is upstream. Sharpen the ticket's acceptance criteria and re-run from Phase 2, rather than grinding the generator.

---

## Completion block

On exit (approve or abandon), print this machine-scannable block:

```
✅ Phase 6: User Review
   - Status: <approved|abandoned>
   - Rework cycles: <count>
```

`<count>` is the value of `regeneration_count` at exit. `Status` is only ever `approved` or `abandoned` — rework is transient and never a terminal state.

---

## Metadata touched

| Field in `meta.json` | When |
|---|---|
| `regeneration_count` | Incremented once per rework iteration |
| `sync_status` | Set to `abandoned` on the abandon verdict |

Reading the cases file is read-only (R0). Counter and status writes to `meta.json` are run-artifact writes (R1). The external sync those writes gate lives in Phase 7 (R3).

---

## Halt conditions

| Condition | Behaviour |
|---|---|
| Reviewer cancels | Halt the pipeline |
| Abandon verdict | Mark `sync_status: abandoned`, exit |
| Approve verdict | Advance to Phase 7 |

---

## Handoff

- **Upstream:** Phase 5 produced the cases and `meta.json` you review here.
- **Downstream:** on approval, `phase-7-test-management-sync.md` takes over. Nothing reaches an external backend before that handoff.
