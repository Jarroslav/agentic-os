# qa-e2e-generator

Turns one work-item ticket into runnable end-to-end automation — UI and/or API — matched to your project's established test conventions, then hands the scripts off as a merge request. A seven-agent pipeline handles validation, context gathering, planning, generation, self-healing execution, review, and handoff. On-demand and per-ticket; not a phase of `sdlc-autonomous` or `sdlc-standard`.

## Use It For

- Generating executable UI tests (Playwright, Cypress, Selenium) and API tests (pytest+requests, jest+supertest, and similar) from a ticket that already has acceptance criteria.
- Automating manual cases first: if `manual/test_cases.md` exists for the same ticket, those scenarios are auto-detected and covered before any AC-derived scenario is invented.
- Test-pyramid-aware coverage on an existing framework — living in this repo or an external test repo, either is accepted.
- Producing a reviewed, committed branch (e.g. `qa/proj-456-e2e-tests`) with page objects, an execution report, and an MR ready for review.

Not for: manual test-case authoring (use `qa-case-generator`), unit tests (use the TDD workflow), standing up an automation framework from scratch, or execution analytics/reporting.

## How To Ask

Invoke the skill with a ticket id:

```
/qa-e2e-generator PROJ-123
```

The run walks phases 0–11: pre-flight, environment validation, AC quality check, context gathering, complexity assessment (size + routing, e.g. `M`/`standard`), suite planning, workspace setup, script generation, execution-with-fixes, code review, your review, handoff.

> Two gates require your explicit approval: the coverage plan during planning, and the commit/MR at handoff. Everything else runs unattended.

Context is mined only from pre-approved paths for that ticket — body, comments, subtasks, attached `spec.md`/`plan.md`, linked MR diffs, commits naming the ticket id, and existing E2E files. The skill never scans the whole codebase. It halts if AC confidence is below 50%.

## What It Needs

Hard prerequisites — the skill refuses without them:

| Requirement | Where | If missing |
| --- | --- | --- |
| Documented test framework | `.agentic/guides/testing/qa-strategy.md` | run `qa-foundation` (framework may be external) |
| QA strategy docs | `.agentic/guides/testing/` | run `qa-foundation` to create the doc root |
| Work-item adapter | `.agentic/guides/project.md`, `## Ticket Adapter` section | configure it, or run `/repo-guides` |
| Working `bash` + `jq` | PATH | on Windows use Git Bash or WSL; install `jq` separately if absent |
| Clear acceptance criteria | the ticket | improve the AC and re-run (confidence < 50% halts) |

Adapters are declarative — examples include the GitHub CLI (`gh`), GitLab CLI (`glab`), and Jira MCP. If the ticket system is unreachable, check the adapter's credentials and permissions.

Outputs land in two places:

- **Test scripts** go to the configured `test_repo.root`, never the docs workspace.
- **Planning and audit artifacts** go to `docs/superpowers/qa-tasks/<date>-<slug>/e2e/`: `test-plan.md`, `e2e-technical-analysis.md`, `context-manifest.json`, `complexity-assessment.json`, `execution-results.json`, `meta.json`, `events.jsonl`.

Optional enhancer: a globally installed `playwright-cli` skill supplies page-object authoring guidance to the generator; without it, the generator falls back to the `e2e_conventions` section of `qa-strategy.md`.

Smoke-check the toolchain with `scripts/qa-e2e-smoke-test.sh` — a healthy setup prints `SMOKE TEST PASSED`. Per-subagent prompt templates live in `references/subagents/`; the roster is `ac-check`, `context`, `plan`, `generate`, `validate`, and `mr`.
