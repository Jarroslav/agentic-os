# QA Gates

Runs the project's quality gates — lint, build, unit tests, and optionally UI tests — in sequence and returns a structured pass/fail report. Vendor-neutral: auto-detects npm, pnpm, yarn, cargo, poetry, uv, or go.

## Use It For

- Running all quality checks before submitting code for review.
- Getting a structured lint/build/test report for a feature branch.
- Detecting which gate is blocking a branch from being merge-ready.
- Feeding QA results into `sdlc-pipeline` for automated retry or escalation.

## How To Ask

This skill is invoked automatically by `sdlc-pipeline` at Phase 8 and by `sdlc-task` at Stage 5. It can also be called directly:

- "Run QA gates."
- "Check lint and tests on this branch."

## What It Needs

- A project with a supported package manager or build tool.
- Optionally, `.agentic/guides/quality-gates.md` for project-specific gate commands — when present, its commands take precedence over auto-detected defaults.
