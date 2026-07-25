# feature-verification

Functional proof for user-visible changes. Once the quality gates go green, this skill drives the feature in a real browser and records evidence — screenshots plus console errors — showing it works. It catches regressions that pass unit tests yet break for actual users.

## Use It For

- Proving a user-visible change renders and behaves after `qa-gates` passes.
- Reusing existing e2e coverage (Playwright or Cypress) to exercise the changed surface.
- Generating a focused Playwright check when no coverage exists yet.
- Capturing screenshot + console-error evidence for code review.

> Not a unit-test runner and no substitute for one — it exists to catch what unit tests miss. Backend-only changes with no user-visible surface stay out of scope.

## How To Ask

Usually you don't. `sdlc-pipeline` auto-invokes this skill right after the `qa-gates` stage whenever a change touches a user-visible surface.

To run it by hand, name the feature or surface in plain language:

- "Verify the checkout button on the cart page still works."
- "Run feature verification for the new settings panel."

## What It Needs

| Requirement | Detail |
| --- | --- |
| Predecessor run | `gate_plan` and `qa_report` from a `qa-gates` run |
| Browser driver | `@playwright/test` or Cypress installed in the host project, otherwise a custom command |
| Custom driver key | `feature_verification.command` in `.agentic/agentic-sdlc/config.json` |
| Dev server | A `dev`, `start`, or `preview` script in `package.json` to launch against |

> The skill inspects `package.json` scripts to start a dev server but does not provision one itself. With no driver installed and no custom command configured, verification cannot run.
