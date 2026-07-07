---
name: qa-foundation
description: >-
  Establishes the QA knowledge base an AI-assisted workflow needs. It surveys the
  current repo for test files, coverage reports, CI gates, and any existing QA
  docs, then asks about external test-case management (Jira/Zephyr, TestRail,
  ADO) and where QA documentation lives (Confluence, Google Docs, local paths).
  Output: qa-strategy.md and qa-health.md under .agentic/guides/testing/.
  Triggers: "qa init", "qa foundation", "set up qa", or /sdlc:qa-init.
version: 0.1.0
license: Apache-2.0
---

# qa-foundation

Builds the QA knowledge foundation. Discovers test infrastructure,
configures external QA source adapters, and writes two persistent guides
consumed by `qa-planner` on every feature run.

## Phase 1 — Discover current repo (read-only)

Scan the current working directory. Do not write anything in this phase.

### Discovery signals

| Signal type | Paths / patterns |
|---|---|
| Test directories | `tests/`, `__tests__/`, `spec/`, `e2e/`, `cypress/`, `playwright/` |
| Coverage reports | `coverage/`, `.nyc_output/`, `htmlcov/`, `coverage.xml`, `lcov.info` |
| Test config | `jest.config.{js,ts,mjs,cjs}`, `pytest.ini`, `setup.cfg`, `playwright.config.{ts,js}`, `.nycrc`, `vitest.config.{ts,js}` |
| CI test gates | `.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile` — extract steps matching: test, coverage, e2e, playwright, cypress, pytest, jest, vitest |
| Local QA docs | Files matching `*test-plan*`, `*test_plan*`, `*strategy*`, `*test-cases*`, `*testcases*` anywhere in repo |

For each signal found, record: absolute path, type, framework detected.

### Coverage extraction

If a coverage report exists, extract:
- Overall line/branch coverage %
- Per-module breakdown (Istanbul/NYC JSON, pytest-cov XML, lcov)
- Modules with 0% coverage

If no coverage report: note "no coverage data — qualitative assessment only".

### Phase 1 output (in memory)

Produce a discovery summary and present it to the user:

```
DISCOVERY SUMMARY — current repo
=================================
Test frameworks: [list]
Test directories: [list]
Coverage: [% or "none"]
Zero-coverage modules: [list or "unknown — no report"]
CI test gates: [list of commands]
Local QA docs found: [list of paths or "none"]
```

## Phase 2 — Configure external sources

Show the Phase 1 discovery summary. Ask the following questions **one at a time**:

### Q1 — External test repositories

> "We found [summary]. Are there test suites in separate local repositories cloned on this machine? Provide absolute path(s) separated by commas, or `none`."

Save as `external_test_repos: []`.

### Q2 — Test case management

> "Where are your test cases managed?"
> Options: Jira/Zephyr | TestRail | Azure DevOps (ADO) | none

If not none:
> "What MCP server, skill, or CLI command provides read access to it? (e.g. `mcp__jira__jira_search` for Jira, or `not configured` if no integration exists yet)"

Save as `test_case_adapter: {system, access}`.

### Q3 — QA documentation

> "Where is your QA documentation stored? (test strategy, test plans, test design docs)"
> Options: Confluence | Google Docs | local file path | within this repo (already scanned) | none

If Confluence or Google Docs:
> "What MCP server or skill provides read access to it?"
Save as `qa_docs_adapter: {system, access}`.

If local file path:
> "Provide the absolute path(s) to the QA documentation directory or files."
Save as `qa_docs_paths: []`.

## Phase 3 — Scan external sources

For each path in `external_test_repos` and `qa_docs_paths`:
- Apply the same discovery signals from Phase 1
- Merge findings into the discovery summary, labelling each with its source path

If `test_case_adapter.access` is configured and not "not configured":
- Fetch up to 20 test case summaries to understand coverage areas
- Note which modules/features have test cases

If `qa_docs_adapter.access` is configured:
- Fetch QA strategy/plan document summaries
- Extract: test types, coverage targets, known gaps

## Phase 4 — User approval (HARD GATE)

Present the combined discovery summary:

```
COMBINED QA DISCOVERY
=====================
[Phase 1: current repo findings]

[Phase 3: external repo findings, if any]

[Test case adapter: system + sample count, if configured]

[QA docs: titles/summaries, if configured]

Configured adapters:
  Test case management: [system | none]
  QA documentation:     [system | none]
  External test repos:  [paths | none]
```

Ask: "Does this look correct? Reply `yes` to generate the QA guides, or describe any corrections."

**Do not write any files until the user approves.**

On corrections: apply them and show updated summary. Repeat until approved.

## Phase 5 — Generate artifacts

Write both files. Overwrite if they exist (re-run is safe).

### `.agentic/guides/testing/qa-strategy.md`

```markdown
# QA Strategy

**Last assessed**: <ISO date>

## Test Frameworks

| Framework | Type | Config file | Test directories |
|---|---|---|---|
| <framework> | unit/integration/e2e | <config path> | <dirs> |

## Test Types in Use

### Unit Tests
- **Location**: <paths>
- **Pattern**: <file naming pattern, e.g. `*.test.ts`, `test_*.py`>
- **Run command**: <exact command from CI or package.json>
- **Example**: `<repo-relative path>:<line number>`

### Integration Tests
- **Location**: <paths or "none detected">
- **Pattern**: <pattern or "n/a">
- **Run command**: <command or "n/a">

### End-to-End Tests
- **Location**: <paths or "none detected">
- **Tool**: <playwright | cypress | other | "none detected">
- **Run command**: <command or "n/a">

## Coverage Targets

- **Line coverage target**: <% from config or "not configured">
- **Branch coverage target**: <% from config or "not configured">
- **Coverage command**: <exact command or "not configured">

## Conventions

- **Test file naming**: <detected pattern>
- **Test file location**: co-located with source | in tests/ directory | other
- **Test style**: <describe/it | test() | class-based>

## Anti-Patterns (observed in this codebase)

| Bad | Better | Why |
|---|---|---|
| <example from codebase> | <better version> | <reason> |

## External Sources

### Test Case Management
- **System**: <Jira/Zephyr | TestRail | ADO | none>
- **Adapter**: <MCP/skill/command | not configured>

### QA Documentation
- **System**: <Confluence | Google Docs | local path | within repo | none>
- **Adapter**: <MCP/skill/command | not configured>
- **Paths**: <paths or "n/a">

### External Test Repositories
<list of absolute paths, or "none">
```

### `.agentic/guides/testing/qa-health.md`

```markdown
# QA Health

**Last assessed**: <ISO date>
**Coverage**: <overall % | qualitative: low / medium / high>

## Coverage Summary

| Module / area | Coverage | Notes |
|---|---|---|
| <module> | <% or unknown> | <note> |

## Risky Untested Areas

Modules with zero or low coverage that carry business logic:

| Path | Coverage | Risk reason |
|---|---|---|
| <path> | 0% | <e.g. "auth logic, no unit tests"> |

## Known Test Debt

<Gaps extracted from QA docs/test plans, or "none documented">

## Recent Test Activity

<5 most recently modified test files from `git log --diff-filter=AM -- '*test*' '*spec*' -n 5 --name-only --pretty=''`>
```

## Handoff

After writing both files, print:

```
---
✅ qa-foundation complete.

Generated:
  .agentic/guides/testing/qa-strategy.md
  .agentic/guides/testing/qa-health.md

These guides are consumed automatically by qa-planner on every feature run.

Recommended next step:
  /sdlc:start or /sdlc:story
```
