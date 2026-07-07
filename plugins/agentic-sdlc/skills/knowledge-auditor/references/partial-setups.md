# Partial Setup Examples

Partial setups contain useful source material, but later knowledge planting should ask whether existing docs remain the source of truth or should be incorporated into factory-owned guidance.

## Docs Exist But Commands Are Incomplete

Signals:

- `README.md` explains setup but omits lint, type-check, or test commands.
- CI contains quality gates not documented for agents.
- `package.json` or `Makefile` has scripts but docs mention only a subset.

Audit rating:

- Completeness: `partial`
- Correctness: `partial` until command sources are reconciled
- Planting recommendation: `merge` manifest-backed commands into planted guidance after approval

## Entrypoint Exists But Does Not Delegate

Signals:

- `AGENTS.md` or `CLAUDE.md` contains useful project rules.
- The file is long or mixes permanent rules with detailed procedures.
- It does not reference existing docs, commands, skills, or subagents.

Audit rating:

- Assistant compatibility: `partial`
- Agentic setup quality: `partial` or `missing`
- Planting recommendation: `preserve` critical rules, then `merge` guide references through a gated entrypoint update later

## Skills Or Subagents Exist But Coverage Is Thin

Signals:

- A small number of skills, commands, or subagents exist.
- Required quality gates, branch rules, approval expectations, or ownership boundaries are absent.
- Agentic assets have limited evidence or no file references.

Audit rating:

- Skill and subagent quality: `partial`
- Completeness: `partial`
- Planting recommendation: `merge` missing agentic guidance; `ask user` for project settings that cannot be inferred

## Managed Regions Are Present But Stale

Signals:

- Managed-region markers exist.
- Referenced guide paths have moved or no longer resolve.
- Entrypoint mentions commands that differ from current manifests.

Audit rating:

- Freshness: `partial` or `weak`, depending on how much resolves
- Consistency: `partial`
- Planting recommendation: `merge` or `replace` stale managed-region content only after showing a diff in a later foundation run

## Mixed Assistant Surfaces

Signals:

- Both `AGENTS.md` and `CLAUDE.md` exist and mostly agree.
- `.claude/` or `.codex/` exists but is not clearly referenced.
- Host-specific instructions are present but not separated by host.

Audit rating:

- Assistant compatibility: `partial`
- Consistency: `partial`
- Planting recommendation: `ask user` which assistant surfaces are authoritative before updating entrypoints
