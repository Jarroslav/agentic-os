# QA Foundation

Builds the QA knowledge foundation for AI-assisted development. Discovers test infrastructure in the current repo, asks about external test repos and QA tooling, and writes two persistent guides consumed by `qa-planner` on every feature run.

## Use It For

- Setting up QA knowledge before running `sdlc-start` or `sdlc-task` for the first time in a repo.
- Configuring integrations with external test case management systems (Jira/Zephyr, TestRail, Azure DevOps).
- Capturing links to external test repositories or QA documentation (Confluence, Google Docs, local paths).
- Refreshing QA guides after significant changes to the test infrastructure.

## How To Ask

Run once per repo before starting the pipeline:

- "Set up QA foundation."
- "QA init."
- "Run qa-foundation."

## What It Produces

Two files written to `.agentic/guides/testing/`:

| File | Purpose |
| --- | --- |
| `qa-strategy.md` | Test frameworks, directories, run commands, conventions, coverage targets, and external adapter config. |
| `qa-health.md` | Coverage snapshot, risky untested areas, known test debt, and recent test activity. |

Both files are read automatically by `qa-planner` on every feature run. Re-running this skill is safe — it overwrites both files.

## What It Needs

- A git repository with at least some test infrastructure (directories, config files, or CI gates).
- Optional: MCP server or CLI access to a test case management system (Jira, TestRail, ADO) if you want test case coverage data.
- Optional: MCP server access to Confluence or Google Docs if QA docs are stored there.
