# qa-gates

Runs your project's quality gates in order (lint, build, unit tests, optional UI tests) and returns a structured pass/fail report naming the gate that blocks merge-readiness. Tool-agnostic: the runner is detected from the project manifest, not hardcoded.

## Use It For

- Pre-review checks on a feature branch before it goes up for merge.
- Per-branch lint / build / test reporting in one pass.
- Blocking-gate detection — surface the exact gate that fails.
- Feeding a structured verdict into pipeline automation (retry/escalation lives in the caller, not here).

Gate sequence:

| # | Gate | Required |
|---|------------|----------|
| 1 | lint | yes |
| 2 | build | yes |
| 3 | unit tests | yes |
| 4 | UI tests | optional |

> Gates run in order. The UI-test gate is conditional — it runs only when configured. This skill reports results only; it does not generate missing browser/UI coverage (that is feature-verification's concern) and does not define retry/escalation logic.

## How To Ask

Direct invocation — trigger with:

- "Run QA gates."
- "Check lint and tests on this branch."

Automatic invocation — the orchestrators call this skill for you:

- `sdlc-pipeline` at **Phase 8** (consumes the QA report for automated retry/escalation).
- `sdlc-task` at **Stage 5**.

## What It Needs

- A host project with a package manifest so the runner can be detected. Recognized runners: `npm`, `pnpm`, `yarn`, `cargo`, `poetry`, `uv`, `go`.
- Optional override: `.agentic/guides/quality-gates.md`. If present, its commands take precedence over the auto-detected defaults; otherwise gate commands are derived from the detected package manager / build tool.

> Not tied to any single build tool or CI platform. Supply project-specific gate commands in the override file when the detected defaults don't match your setup.
