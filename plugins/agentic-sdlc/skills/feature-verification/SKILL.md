---
name: feature-verification
description: |-
  Required functional proof for anything user-visible, run right after qa-gates. When a change touches UI or another externally visible surface, it reuses e2e coverage that already exists, or generates a focused Playwright check when none does; either way it captures screenshots, console output, and network errors, and writes verification-evidence.json per feature.
version: 0.2.0
license: Apache-2.0
authors:
  - agentic-os
---

# feature-verification

This is the contract that bridges "lint+build+unit pass" and "the feature actually works for the user" — those two are not the same claim, and this skill exists to stop one from being mistaken for the other.

## Why this skill exists

`qa-gates` is purely mechanical — it runs whatever test scripts the host project defines and reports pass or fail. A unit test that only asserts against internals, though, proves nothing about whether the feature behaves correctly in an actual browser. Plugin v0.2 shipped exactly this regression: autonomous mode marked a UI feature "ready" purely because lint/build/unit came back green while the UI gate itself sat SKIPPED. This skill exists specifically to close off that class of bug.

## Inputs

- `gate_plan` — from qa-gates Phase 7 output (`<run_dir>/gate-plan.json`)
- `qa_report` — from qa-gates Phase 7 output (`<run_dir>/qa-report.md`)
- `branch` — current feature branch
- `merge_base` — defaults to `origin/main`
- `repo_path` — absolute path to the current checkout
- `run_dir` — absolute path of the run state directory

## Step 1 — Detect user-visible surface changes

Run `git diff --name-only <merge_base>...HEAD`. Any file in that diff counts as a user-visible surface change if it matches:

- The `gate_plan.ui_globs` already configured
- A new entry-point file: `*.html`, `index.tsx`, `index.jsx`, `App.tsx`, `pages/**`, `app/**`, `routes/**`
- A manifest entry that changes what assets ship (for instance, a new entry under `package.json.exports` for a UI library)

If the diff shows **no** surface change → write `verification-evidence.json` as `{"applies": false, "reason": "no user-visible surface in diff"}`, return `{required: false, verified: true}`, and stop there.

If a surface change **is** present → move on to Step 2.

## Step 2 — Resolve the verification tool

Inspect the host project and pick the first signal that matches:

| Signal | Tool |
|--------|------|
| `playwright.config.{ts,js,mjs,cjs}` exists | `playwright` |
| `package.json` has `@playwright/test` dep | `playwright` |
| `cypress.config.{ts,js,mjs,cjs}` exists | `cypress` |
| `package.json` has `cypress` dep | `cypress` |
| Storybook test runner configured | `storybook-test` |
| `.agentic/agentic-sdlc/config.json` has `feature_verification.command` set | `custom` (use that command) |
| (none of the above) | `unconfigured` |

Whichever tool this resolves to, cache it at `<run_dir>/feature-verification-plan.json`.

## Step 3 — Build the verification plan

Once the tool is resolved, work out the command and the target URL to use:

| Tool | Command template | Target |
|------|------------------|--------|
| `playwright` | `npx playwright test` (or per-test pattern derived from changed files) | uses `playwright.config` baseURL |
| `cypress` | `npx cypress run --spec <pattern>` | uses `cypress.config` baseUrl |
| `storybook-test` | `npx test-storybook` | runs against Storybook static build |
| `custom` | from config | as configured |
| `unconfigured` | n/a | n/a |

For every changed UI file, look for the corresponding test file (`<file>.spec.ts`, `<file>.test.tsx`, `tests/<feature>.e2e.ts`). When nothing matches, build a dynamic verification plan instead:

1. Work out the route or story from the framework's own conventions (`app/`, `pages/`, `routes/`, Storybook stories, router config).
2. Work out the user-visible behavior from the requirements, the plan task, whichever selectors/text changed, and the component's props.
3. When Playwright is already configured, prefer dropping a focused test into the host project's existing e2e test directory rather than somewhere new.
4. When there's no e2e directory but Playwright is still available, create `<run_dir>/dynamic-tests/<feature-id>.spec.ts` and run it against a generated Playwright config pointed at the host app.
5. When the app's start command isn't known, check the common script names (`dev`, `start`, `preview`) and `.agentic/agentic-sdlc/config.json`. If it's still not known after that, return `BLOCKED` naming the missing command.

A dynamic test has to verify the behavior that actually changed, not merely that the page loads — it needs at least one interaction or state assertion drawn from the acceptance criteria.

## Step 4 — Run the verification

When the tool resolved to `unconfigured` but the UI did change, attempt the dynamic Playwright path — but only if the project is Node-based and config allows installing dependencies. When that dynamic setup isn't possible either, **HALT** with status `BLOCKED` and write `verification-evidence.json`:

```json
{
  "schema": 1,
  "applies": true,
  "result": "BLOCKED",
  "reason": "UI surface changed but no browser verification tool is configured",
  "remediation": "Install Playwright (npm i -D @playwright/test && npx playwright install) or set feature_verification.command in .agentic/agentic-sdlc/config.json"
}
```

When a tool is configured, run whichever verification command is already there or was just generated, and capture:

- the exit code
- stdout/stderr (last 50 lines)
- console errors emitted by the browser session (both Playwright and Cypress include these in their reports)
- network failures (any HTTP 4xx/5xx among the monitored requests)
- a screenshot of the verified state, saved to `<run_dir>/evidence/screenshots/<feature>.png`

## Step 5 — Per-feature evidence write

For every feature that got verified — one per derived test file, per generated dynamic test, or per covered group of changed files — write `<run_dir>/evidence/verification/<feature-id>.json`:

```json
{
  "schema": 1,
  "feature_id": "<derived id, e.g. login-form>",
  "applies": true,
  "tool": "playwright | cypress | storybook-test | custom",
  "coverage_source": "existing-test | generated-test | manual-command",
  "test_command": "npx playwright test login.spec.ts",
  "generated_test_path": "<run_dir>/dynamic-tests/login-form.spec.ts",
  "app_url": "http://localhost:3000/login",
  "browser_steps": [
    "navigate to /login",
    "fill #email with valid@example.com",
    "fill #password with Hunter2",
    "click button[type=submit]",
    "expect URL to match /dashboard"
  ],
  "assertions": [
    "redirected to /dashboard",
    "no console errors",
    "no failed network requests"
  ],
  "screenshot_path": "evidence/screenshots/login-form.png",
  "console_errors": [],
  "network_failures": [],
  "result": "PASS | FAIL | INCONCLUSIVE",
  "captured_at": "<ISO>",
  "duration_ms": 4231
}
```

Result rules:

- Every assertion met, plus zero console errors and zero network failures → `PASS`
- Any assertion failed, or the exit code was non-zero → `FAIL`
- The verification ran, but a coverage gap remains — the test file is empty, or it only checks that the page loads, or the generated route couldn't reach the feature at all → `INCONCLUSIVE`

## Step 6 — Aggregate report

Append a "Feature Verification" section to `<run_dir>/qa-report.md`:

```markdown
## Feature Verification

**Tool**: playwright
**Required**: yes (UI surface changed)
**Status**: PASSED | BLOCKED | FAILED

| Feature | Result | Test command | Console errors | Network failures |
|---------|--------|--------------|----------------|------------------|
| login-form | PASS | npx playwright test login.spec.ts | 0 | 0 |
| dashboard-widgets | PASS | npx playwright test dynamic-tests/dashboard-widgets.spec.ts | 0 | 0 |
```

Return this back to the caller:

```json
{
  "required": true,
  "verified": false,
  "tool": "playwright",
  "results": [
    {"feature_id": "login-form", "result": "PASS"},
    {"feature_id": "dashboard-widgets", "result": "INCONCLUSIVE"}
  ],
  "blocking": true
}
```

Set `blocking: true` whenever any per-feature `result` comes back FAIL, INCONCLUSIVE, or BLOCKED.

## Constraints

- Never claim `verified: true` unless a `verification-evidence.json` file backs it up with `result: "PASS"` for every changed user-visible surface.
- Never run a verification command from outside the host project root.
- Console errors are never optional — a single console error anywhere in the verified session is a hard fail, full stop.
- A screenshot is mandatory for every PASS — it's the receipt a human can actually check.
- Treat generated tests as verification artifacts first and foremost. Only keep them in the project proper once they're stable, idiomatic, and worth having as permanent regression coverage; otherwise they belong under `<run_dir>/dynamic-tests/`.
- On non-UI projects — meaning Step 1 found no surface change — this skill exits cleanly and does nothing further.
