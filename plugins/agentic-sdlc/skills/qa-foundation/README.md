# QA Foundation

One-time-per-repo QA knowledge bootstrap. Scans the repo for test infrastructure, elicits your external test/QA integrations, and writes two persistent guides that `qa-planner` reads on every feature run.

## Use It For

- Standing up the QA knowledge base before the first `sdlc-start` or `sdlc-task` run in a repo.
- Discovering in-repo test infrastructure: test directories, config files, CI gates, coverage reports.
- Wiring an adapter to a test-case management backend — Jira/Zephyr, TestRail, or Azure DevOps (ADO).
- Capturing links to external test repositories and QA documentation (Confluence, Google Docs, local paths).
- Refreshing the QA baseline after a major change to the test infrastructure.

> Run once per repo. Re-runs are idempotent-by-overwrite — both output files are safely rewritten.

## How To Ask

Trigger phrases:

- "Set up QA foundation."
- "QA init."
- "Run qa-foundation."

You'll be prompted for external test repos, your test-case management system, and where QA docs live. Every external integration is optional — skip any you don't have.

## What It Needs

| Requirement | Notes |
| --- | --- |
| A git repo | Required. |
| Some test infrastructure | Required — at least one of: test directories, config files, or CI gates. |
| Test-case coverage data | Optional. Available only if an MCP/CLI integration to a test management system is present. |
| QA-doc ingestion | Optional. Confluence / Google Docs pull-in needs MCP access to those systems; local paths work without it. |

Outputs are written to `.agentic/guides/testing/`:

| File | Content |
| --- | --- |
| `qa-strategy.md` | Test frameworks, directories, run commands, conventions, coverage targets, external adapter config. |
| `qa-health.md` | Coverage snapshot, risky untested areas, known test debt, recent test activity. |

Both files are read automatically by `qa-planner` on every feature run, feeding its checklist, test-review, and health-update modes.

> Non-goals: does not run tests or quality gates (a separate gates skill does that), and does not plan or review per-feature tests (that's `qa-planner`).
