# Knowledge Craft — Guide Authoring Rules

Shared authoring standard for guides generated or updated by `knowledge-foundation`
and `knowledge-harvester`. Load this file before writing any guide content.

## Content Style — Practices Over Code Dumps

Each pattern in a guide is expressed as:

1. A short rule statement (1–2 sentences).
2. A bad-vs-best practices contrast (table or paired bullets).
3. References to real cases: `file:line` pointers.

Inline code is the exception, not the default. Cap: ~5 lines per snippet,
max one snippet per pattern. Prefer linking to a `file:line` over pasting code.

### Bad vs best practice formatting

| Avoid | Prefer |
|---|---|
| Throwing generic `Error` | Specific typed error class — see `src/utils/errors.ts:12` |
| Logging raw secrets | `sanitizeLogArgs()` — see `src/utils/security.ts:45` |

## Structure

Each guide has:
- An H1 title
- One `##` section per pattern category
- `###` subsections for specific patterns within a category

Required sections per guide type are defined in the templates under
`references/templates/guides/`.

## Size Caps (hard, enforced in Phase 5 / Step 7)

| Artifact | Guidance | Hard Max |
|---|---|---|
| Each guide | Concise, evidence-backed, and as short as the useful content allows | 400 lines |
| Entrypoint file | Compact reference surface; no minimum line count | 300 lines |

There is no minimum line count. Do not pad artifacts to satisfy a perceived range.
Repeated reminders, duplicated guide prose, placeholder rows, and filler lines are
validation failures even when the line count is within the hard maximum.

If a guide exceeds 400 lines after writing: condense — convert prose to tables,
drop redundant examples, replace inline code with `file:line` references —
and re-render before completing.

## Placeholder Contract

- `[NAME]` — required; must be replaced with a real value from discovery.
- `[NAME?]` — optional; if no real value, **delete the entire row/section**
  containing the placeholder. Do not leave stub text like `(none)` or `N/A`.

Standard placeholders:

| Placeholder | Source |
|---|---|
| `[PROJECT_NAME]` | `package.json` name / `pyproject.toml` name / `pom.xml` artifactId / root folder name |
| `[LANGUAGE]` | manifest language field |
| `[FRAMEWORK]` | primary framework dependency |
| `[VERSION]` | dependency version |
| `[TEST_FRAMEWORK]` | test runner from devDependencies |
| `[BUILD_COMMAND]` | manifest build script |
| `[LINT_COMMAND]` | manifest lint script |
| `[TEST_COMMAND]` | manifest test script |
| `[file:lines]` | concrete codebase reference |
| `[code_example]` | only when the rule cannot be stated otherwise |

`[code_example]` placeholders are filled only when the surrounding rule cannot
be expressed without code. Otherwise drop the row using the `?` suffix mechanism.

## Evidence Rule

Every category in a guide MUST have at least one `file:line` reference.
Categories without evidence are dropped during the planning phase and never
reach generation.

## Quality Standards

- No TODOs, no vague sentences, no placeholder text.
- Every claim must be traceable to a file or observable pattern.
- Do not document implementation intent — document what the code actually does.
- Do not copy large code blocks into guides; use `file:line` references instead.
- Do not add synthetic reminder, operating reminder, review reminder, or foundation reminder lines.
- Do not repeat near-identical lines to increase line count.
- Do not add generic evidence-index padding when the guide already has concrete references near each rule.

## Validation Checklist

Run these checks after generating or updating any guide:

| Check | How |
|---|---|
| All referenced guide paths resolve | Read each path in the entrypoint table |
| All `file:line` refs resolve | Read the file, verify line ≤ length |
| No `[PLACEHOLDER]` / `[PLACEHOLDER?]` tokens remain | `grep` generated files |
| Each guide is concise and no more than 400 lines | `wc -l` |
| Entrypoint is concise, reference-only, and no more than 300 lines | `wc -l` |
| No reminder/filler padding exists | Search for `Review reminder`, `Foundation reminder`, `Operating reminder`, repeated near-identical lines, and placeholder rows |
| `project.md` follows the Project Context schema | Verify only Project Identity, Work Item Tracker, Ticket Adapter, Source Control And Review, and MR Adapter sections are present |
| Drift is in the right guide | Git conventions in git-workflow, exact commands in quality-gates, routing in entrypoint |
| Discovered commands match manifests | Re-read `package.json`/`Makefile`/etc. |
| Managed regions have matching markers | `grep` for `start`/`end` pairs |
