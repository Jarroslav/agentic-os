# Good Setup Examples

Good setups are specific, current, internally consistent, and easy for later knowledge planting to preserve.

## Complete Documentation Setup

Signals:

- `README.md` explains the product, local setup, common workflows, and links to deeper docs.
- `CONTRIBUTING.md` or `docs/development.md` gives exact install, test, lint, review, and release commands.
- `docs/architecture.md` or ADRs describe module boundaries and important decisions.
- Commands in docs match `package.json`, `Makefile`, `pyproject.toml`, CI, or equivalent manifests.
- Documentation points to current directories and active package names.

Audit rating:

- Completeness: `strong`
- Correctness: `strong`
- Freshness: `strong` if paths and commands resolve
- Planting recommendation: `preserve` as source of truth, or `incorporate` if foundation should own the future guidance

## Complete Assistant Entrypoint Setup

Signals:

- Root `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md` exists for the detected host.
- Entrypoint is concise and delegates detailed practices to guide files.
- Entrypoint names critical rules, quality gates, and approval expectations without duplicating long docs.
- Tool-specific directories such as `.claude/`, `.codex/`, or `.agents/` contain commands, skills, or settings that are referenced or clearly scoped.
- No unsupported slash commands or host-specific commands are presented as universal.

Audit rating:

- Assistant compatibility: `strong`
- Consistency: `strong`
- Planting recommendation: `preserve` existing entrypoint policy and `merge` future managed-region updates only after approval

## Healthy Managed Regions

Signals:

- Assistant entrypoints contain clear managed-region start and end markers.
- Generated content inside managed regions is clearly separated from human-authored rules.
- Human-authored content outside managed regions remains separate.
- Referenced files or commands resolve.

Audit rating:

- Agentic setup quality: `strong`
- Planting recommendation: `preserve` managed regions and update them only through the foundation entrypoint merge gate

## Strong Skill and Subagent Evidence

Signals:

- Skills have concise frontmatter and trigger descriptions.
- Skill bodies use progressive disclosure into references for detailed material.
- Subagents have bounded ownership, clear inputs, and explicit verification expectations.
- Commands, skills, and subagents cite repository files or manifests as evidence.
- Important skills or subagents have evals, pressure scenarios, or representative prompts.

Audit rating:

- Completeness: `strong`
- Skill and subagent quality: `strong`
- Planting recommendation: `preserve` or `merge` small updates

## Consistent Command Setup

Signals:

- `npm test`, `make test`, `pytest`, or equivalent commands are documented consistently across entrypoints, docs, and CI.
- Lint, format, type-check, and test commands appear in a stable order.
- Assistant instructions do not tell agents to skip required gates.

Audit rating:

- Correctness: `strong`
- Consistency: `strong`
- Planting recommendation: `preserve`
