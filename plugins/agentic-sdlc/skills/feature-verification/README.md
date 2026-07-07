# Feature Verification

Runs browser-based verification for user-visible feature changes using Playwright, Cypress, or a custom command. Captures screenshots and console errors as evidence that the feature actually works.

## Use It For

- Verifying that a UI change works correctly in a real browser session.
- Catching regressions that pass unit tests but fail for real users.
- Generating screenshot and console-error evidence for code review.
- Creating focused Playwright tests when existing coverage is missing.

## How To Ask

This skill is invoked automatically by `sdlc-pipeline` after `qa-gates` when a user-visible surface change is detected. It can also be called directly:

- "Run feature verification on the login form changes."
- "Verify that the dashboard update works in the browser."

## What It Needs

- Playwright (`@playwright/test`) or Cypress installed in the host project, or a custom `feature_verification.command` in `.agentic/agentic-sdlc/config.json`.
- A running dev server (the skill inspects `package.json` scripts for `dev`, `start`, or `preview`).
- `gate_plan` and `qa_report` from a prior `qa-gates` run.
