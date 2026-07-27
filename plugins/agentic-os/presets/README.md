# Role presets

A preset (`roles/<name>.json`) is a **shopping list of IDs, never content**:

```json
{
  "name": "...",
  "description": "...",
  "templates": ["<template IDs from templates/VARIABLES.md>"],
  "generated": ["<gen/* slots produced by generators/agent-generator.md>"],
  "default_hitl": "strict | gated-autonomous | autonomous",
  "default_orchestration": "pipeline | dispatcher",
  "sdlc_skills": ["<skill dirs under plugins/agentic-sdlc/skills/>"]
}
```

Seven presets ship: `developer`, `qa`, `ba-po`, `architect`, `pm-delivery`,
`devops`, `portfolio` (see the README's
[Role presets](../../../README.md#role-presets) table for what each targets).

## How presets compose

Presets are **additive**. Each one lists everything its role needs, including
the shared baseline — the same ID may appear in several presets, always as the
identical string (no per-preset variants; validated by
`validate-presets.sh`). Content lives once in `templates/` (or is generated);
a preset can therefore never fork an asset.

## How the installer resolves a multi-preset install

`/agentic-init` takes the selected presets and:

1. **Requires an explicit selection** — the installer never silently chooses a
   role. The user passes `/agentic-init --presets ba-po` or selects one or more
   roles in Screen 1.
2. **Unions the sets** — `templates`, `generated`, and `sdlc_skills`
   are set-unioned; each resulting ID is scaffolded/generated exactly once.
3. **Strictest HITL wins** — `default_hitl` resolves by
   `strict > gated-autonomous > autonomous`; the interview shows the result
   pre-filled and the human can still override it.
4. **Orchestration** — every style in the union installs (a dev+qa team gets
   both `commands/pipeline-orchestrator` and `commands/dispatch`). The
   *default* style pre-filled in the interview comes from the first preset
   the user listed; `strict` HITL forces the `dispatcher` default.
5. **Generated slots** run only where the discovered stack-fact record says
   the capability applies (e.g. `gen/i18n-agent` is skipped when no i18n
   library is detected, `gen/migration-validator` is skipped when persistence
   isn't migration-managed) — see `skills/agentic-init/SKILL.md` § Phase 5
   step 1. A repo with no applicable capability at all just produces
   `generated: []`, same as a code-free role preset.

## Layering for a team

Pick one preset per role present on the team and pass them all:
`/agentic-init --presets developer,qa`. Because composition is a pure union
of IDs, adding a preset later is safe and idempotent — a re-run scaffolds
only the IDs not already journaled, and never rewrites user-owned files (see
the mature-repo handling described in the README's
[What gets scaffolded](../../../README.md#what-gets-scaffolded) section and
`skills/agentic-init/SKILL.md` Phase 4). `{{ROLE_PRESETS_ACTIVE}}` records
the installed set in the scaffolded governance docs.

Role changes are additive in the current lifecycle. Removing a role is not
automatic because its files may have been edited by the user; removal requires
an explicit future migration flow.

## Validation

`bash presets/validate-presets.sh` — checks every preset is valid JSON, has
the full key set, and references only template/gen IDs registered in
`templates/VARIABLES.md`. Run it after any preset edit. CI covers the same
ground (plus union-safety, orphan detection, and `sdlc_skills` resolution)
via `tests/lib/check-presets.py`, run as T3 of `tests/run-matrix.sh`.

<!-- ci probe: verifying the changelog gate fires. not for merge. -->
