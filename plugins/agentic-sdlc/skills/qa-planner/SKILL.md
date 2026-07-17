---
name: qa-planner
description: >-
  Plans and reviews QA on a per-feature basis, in three modes that sdlc-pipeline
  invokes directly: --checklist (Phase 6) turns requirements and QA knowledge into
  qa-checklist.md before implementation starts; --review-tests (Phase 8) reviews
  the tests that were written for quality and completeness; --update (Phase 11)
  refreshes qa-health.md once qa-gates has passed. Not meant to be invoked directly
  by a user.
version: 0.1.0
license: Apache-2.0
---

# qa-planner

A per-feature QA skill that owns the whole span from checklist generation through the health
update.

**Prerequisites:** `.agentic/guides/testing/qa-strategy.md` and `.agentic/guides/testing/qa-health.md`
must already exist. If either is missing, halt with:
```
[QA GUIDE MISSING] .agentic/guides/testing/qa-strategy.md not found.
Run the `qa-foundation` skill to generate the QA knowledge foundation first.
```

`references/qa-artifacts.md` has the exact format for `qa-checklist.md`
and `qa-test-review.md`.

---

## Mode: `--checklist` (Phase 6)

### Inputs

- `run_dir` — absolute path to the current run directory
- `merge_base` — defaults to `origin/main`

### Step 1 — Read context

Read in order:
1. `<run_dir>/requirements.md` — required; halt if missing
2. `<run_dir>/design.md` — optional; skip if absent
3. `.agentic/guides/testing/qa-strategy.md`
4. `.agentic/guides/testing/qa-health.md`

### Step 2 — Extract feature scope

From `requirements.md`, pull out:
- **Affected modules**: file paths, packages, or domain areas mentioned
- **User-facing surfaces**: UI components, API endpoints, CLI commands
- **Risk flags**: auth, payment, data migration, security, breaking change
- **Feature keywords**: 3–6 short terms (class names, endpoint names, feature domain words) to search existing tests with

### Step 3 — Scan existing coverage

**3a — Test case adapter (Jira / external)**

Read `qa-strategy.md → External Sources → Test Case Management → Adapter`.

If an adapter is configured (i.e. not "not configured"):
- Query it for test cases linked to the affected modules/features, using the feature keywords from Step 2
- Cap results at 30; pull out: test case ID, title, type (manual/automated), status
- Bucket each as: `covered` (automated test exists and passes), `gap` (exists but failing/outdated), `manual` (manual test case)

If it's not configured, or unreachable: mark all external test case coverage as "unknown" and carry on without blocking.

**3b — External harness scan**

Read `qa-strategy.md → Integration Tests` and `→ End-to-End Tests`.

If an external harness path is documented:
- For each affected module and feature keyword from Step 2, grep the harness directory for test files mentioning those terms
- Record findings: `{module: "<name>", existing_harness_tests: ["<path>::<test_name>", ...]}`
- A hit counts as `covered` for that module; no hit counts as `gap`

If no harness path is documented: skip this — no harness scenarios get generated.

### Step 4 — Map gaps

**4a — Internal gaps (qa-health.md)**

For each entry in `qa-health.md → Risky Untested Areas`:
- Check whether it overlaps with the affected modules from Step 2
- Any overlapping entry becomes a candidate for a high-risk scenario in "Automated — this run"

**4b — Harness coverage areas**

Only run this sub-step if Step 3b turned up a harness path.

Read `qa-strategy.md → Integration Tests` and `→ End-to-End Tests` for coverage areas (e.g. `e2e/`, `integration/`, or named feature subdirectories):
- For each affected module/domain, work out whether it falls under a harness coverage area (by path convention, marker, or description)
- If yes and Step 3b found no existing harness test for that module → it's a candidate for an "Automated — harness backlog" scenario
- If yes and Step 3b did find an existing harness test → mark it `covered` in the backlog section

### Step 5 — Generate qa-checklist.md

Write `<run_dir>/qa-checklist.md`, following the format in `references/qa-artifacts.md`.

**Section: Automated — this run** (always present)

Include:
- At least 1 scenario per user-facing surface identified in Step 2
- At least 1 scenario per risk flag identified in Step 2
- Every overlapping gap from Step 4a, as a high-risk scenario
- A `Suggested test-first description` that names the function/endpoint, the input, and the expected outcome

**Section: Automated — harness backlog** (only if a harness is documented in qa-strategy.md)

Include:
- One scenario per affected module/domain that falls under a harness coverage area (Step 4b)
- `Existing coverage` set to `covered (<test>)` if Step 3b found a test, `gap` if the domain matched but no test turned up, `unknown` if the harness isn't scannable
- `Where to add`: the exact harness file path or subdirectory where the test belongs

Leave this section out entirely if no harness is documented.

**Section: Manual — backlog** (only if a test case adapter is configured in qa-strategy.md)

Include:
- Existing manual test cases from Step 3a that are outdated or gap-status
- New manual scenarios for user-facing surfaces with no automated coverage
- `Where to add`: the exact system and project (e.g. "Jira: create test case in <project-key>, label: Manual")

Leave this section out entirely if no test case adapter is configured.

### Step 6 — Self-review

Before calling decision-router, check:
- [ ] Every acceptance criterion in `requirements.md` maps to at least one scenario in "Automated — this run"
- [ ] Every high-risk overlapping gap from Step 4a shows up with `Blocking: yes` (in "Automated — this run")
- [ ] No scenario in "Automated — this run" is missing a "Suggested test-first description"
- [ ] Every "harness backlog" and "manual backlog" scenario has a non-empty "Where to add" value

Patch any gaps inline before moving on.

### Step 7 — Gate

Call `decision-router` with:
- `gate_id: "qa-checklist.approved"`
- `artifacts: [{kind: "qa-checklist", path: "<run_dir>/qa-checklist.md", summary: "<N blocking scenarios, M harness backlog, K manual backlog>", signature: "<sha-256>"}]`

HITL: present the checklist and wait for user approval.
Autonomous: auto-approve when no high-risk `Blocking: yes` gaps are left unaddressed; escalate otherwise.

**Note:** Scenarios under "Automated — harness backlog" and "Manual — backlog" are informational only — coverage status there never triggers gate escalation.

**Output:** `<run_dir>/qa-checklist.md`

---

## Mode: `--review-tests` (Phase 8)

### Inputs

- `run_dir` — absolute path
- `merge_base` — defaults to `origin/main`

### Step 1 — Read context

1. `<run_dir>/qa-checklist.md` — required
2. `.agentic/guides/testing/qa-strategy.md`
3. Run `git diff --name-only <merge_base>...HEAD`
4. Filter to test files: paths under directories listed in `qa-strategy.md → Test Frameworks` table, plus files matching `*.test.*`, `*_test.*`, `test_*.*`, `*.spec.*`
5. Read each changed test file

### Step 2 — Map scenarios to tests

Evaluate only the scenarios in the **"Automated — this run"** section of `qa-checklist.md` (`Blocking: yes`); leave "harness backlog" and "manual backlog" scenarios out of this entirely.

For each blocking scenario, search the changed test files for a test that addresses it (keyword match against the scenario description). Mark each scenario as: covered / partially-covered / missing.

### Step 3 — Review test quality

For each test found, check:

| Check | Pass condition |
|---|---|
| Assertion quality | Asserts on a specific value, not just truthy / no-throw |
| Test name | Describes scenario outcome, not implementation detail |
| Independence | No imports from other test files; no shared mutable state |
| Pattern adherence | Follows naming and structure patterns in `qa-strategy.md → Conventions` |

### Step 4 — Write qa-test-review.md

Write `<run_dir>/qa-test-review.md`, following the format in `references/qa-artifacts.md`.

Status is `PASSED` only when all high/medium-risk blocking scenarios are covered and there are no high-severity quality findings.

### Step 5 — Gate

Call `decision-router` with:
- `gate_id: "qa-tests.approved"`
- `artifacts: [{kind: "qa-test-review", path: "<run_dir>/qa-test-review.md", summary: "<status, covered N/total blocking, H high M medium issues>", signature: "<sha-256>"}]`

On approve: hand back to the pipeline.
On `request-changes`: the pipeline dispatches a fix-up implementation task aimed at the high-severity findings; `--review-tests` then re-runs once after the fix. One retry maximum.

**Output:** `<run_dir>/qa-test-review.md`

---

## Mode: `--update` (Phase 11)

### Inputs

- `run_dir` — absolute path
- `merge_base` — defaults to `origin/main`

### Step 1 — Find changed test files

Run: `git diff --name-only <merge_base>...HEAD`

Filter down to test files using the same pattern as `--review-tests` Step 1.

### Step 2 — Map new tests to modules

For each new or modified test file, work out which source module(s) it covers (via import analysis or the path convention in `qa-strategy.md`).

### Step 3 — Update qa-health.md

Read `.agentic/guides/testing/qa-health.md` and apply:
- Any gap in "Risky Untested Areas" now covered by new tests: drop it from the gap list, add it to Coverage Summary with the new coverage %
- Source files touched in this run with no new tests: add to Risky Untested Areas
- "Last assessed": bump to today's date

Write the updated file, leaving sections this run didn't touch untouched.

**Output:** updated `.agentic/guides/testing/qa-health.md`
