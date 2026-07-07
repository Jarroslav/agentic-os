# Bad Setup Examples

Bad setups are weak, stale, generic, or unsafe for later knowledge planting to consume without confirmation.

## Generic Documentation

Signals:

- `README.md` only contains a project title or install boilerplate.
- Docs say "run the tests" without commands.
- Architecture docs describe a different product or framework.
- Paths in docs do not exist.

Audit rating:

- Completeness: `weak`
- Specificity: `weak`
- Freshness: `weak`
- Planting recommendation: `replace` generic guidance with evidence-backed planted guidance, or `ask user` if repository evidence is insufficient

## Missing Assistant Setup

Signals:

- No `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.claude/`, `.codex/`, or `.agents/` surfaces exist.
- No assistant-facing rules identify quality gates, approval expectations, or project context.

Audit rating:

- Assistant compatibility: `missing`
- Agentic setup quality: `missing`
- Planting recommendation: `skip` entrypoint assessment and let later knowledge planting propose a target file

## Stale Entrypoint

Signals:

- Entrypoint references removed directories, old package names, obsolete commands, or unsupported tools.
- It imports or links guide files that no longer exist.
- It tells agents to use commands absent from manifests and CI.

Audit rating:

- Correctness: `weak`
- Freshness: `weak`
- Planting recommendation: `replace` stale managed-region content or `ask user` before replacing human-authored rules

## Parallel Agentic Sources

Signals:

- Multiple assistant entrypoints, command directories, skill directories, or subagent directories claim authority for the same workflow.
- Entrypoints import or reference competing assets without priority.
- Files with the same purpose exist in multiple locations with different commands or approval rules.

Audit rating:

- Agentic setup quality: `conflicting`
- Consistency: `conflicting`
- Planting recommendation: `ask user` or `halt` before generating more guidance

## Unsafe Workflow Instructions

Signals:

- Docs or assistant files tell agents to bypass approvals.
- Instructions require destructive git operations as a default.
- Instructions tell agents to ignore dirty working trees or overwrite user changes.
- Setup requires installing tools automatically without user approval.

Audit rating:

- Correctness: `conflicting`
- Planting readiness: `conflicting`
- Planting recommendation: `halt` until the user resolves the unsafe instruction
