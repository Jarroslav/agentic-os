# Entrypoint Merge — Phase 4 Reference

Wire guide imports + critical rules + task classifier + commands into the project's AI entrypoint file using marker-delimited managed regions. Idempotent across re-runs. Preserves user content outside the markers. All decisions must follow the Phase 1 audit and the approved Phase 2 merge plan.

## Audit-grounded merge posture

Before preparing a diff, read the Phase 1 audit and approved Phase 2 entrypoint merge plan.

Map audit recommendations to entrypoint behavior:

| Audit recommendation | Entrypoint behavior |
|---|---|
| `preserve` | Keep existing entrypoint content intact; update only approved managed regions. |
| `replace` | Replace stale or incorrect managed-region bodies after showing a diff and receiving file-specific approval. |
| `merge` | Append or refresh managed regions while preserving useful existing human-authored sections. |
| `skip` | Do not modify that target or region during this run. |
| `ask user` | Stop before rendering the diff and ask the unresolved question. |
| `halt` | Stop the run; do not write the entrypoint file. |

If audit ratings are `weak`, `missing`, or `conflicting` for commands, assistant authority, managed-region integrity, or guide source of truth, do not generate confident entrypoint content from that evidence. Ask the user, skip the affected region, or halt according to the audit recommendation.

## Target file resolution

`AGENTS.md` is the canonical generated entrypoint for agentic-sdlc guidance.
When both `AGENTS.md` and `CLAUDE.md` are applicable, wire the full managed
guide imports, task classifier, critical rules, and command references into
`AGENTS.md`; render `CLAUDE.md` as a minimal Claude Code shim that imports
`AGENTS.md`.

| Phase 1 signal | Target file |
|---|---|
| `.claude/` | `CLAUDE.md` shim plus `AGENTS.md` primary entrypoint |
| `AGENTS.md` exists or `.codex/` | `AGENTS.md` |
| `.gemini/` or `GEMINI.md` | `GEMINI.md` |
| Multiple signals | One target per signal — produce one diff per file, gated independently |
| None | Ask user; default to `AGENTS.md` |

## Managed regions (delimiters)

```
<!-- agentic-init:guide-imports start -->
... auto-generated guide imports table ...
<!-- agentic-init:guide-imports end -->

<!-- agentic-init:task-classifier start -->
... auto-generated task classifier ...
<!-- agentic-init:task-classifier end -->

<!-- agentic-init:critical-rules start -->
... "Check guides first" + Testing/Git/Shell rules ...
<!-- agentic-init:critical-rules end -->

<!-- agentic-init:commands start -->
... discovered build/lint/test commands ...
<!-- agentic-init:commands end -->
```

Outside these markers: **never touch by default.** User-authored sections, custom rules, troubleshooting notes — preserved verbatim. Any change outside managed regions requires separate explicit user approval that names the exact file and non-managed content to change.

Exception: when the approved plan selects `AGENTS.md` as the primary entrypoint
and `CLAUDE.md` only as an inclusion shim, replacing legacy generated Claude
guidance outside managed regions is allowed after showing a file-specific diff
and receiving explicit approval for `CLAUDE.md`.

Managed-region discipline:

- Existing managed regions may be updated by default only when the Phase 2 merge plan approved that region.
- Missing managed regions may be appended only after the per-file diff is approved.
- Malformed managed-region markers require `halt`; do not repair them silently.
- Duplicate managed regions require `ask user` unless one duplicate can be proven stale generated content from audit evidence.
- Human-authored content inside a managed region is not overwritten without the user choosing overwrite, append, or skip.

## Entrypoint scope rule

Entrypoint files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) are routing and import
surfaces, not standards manuals. Managed regions must point agents to the right
guide and next action, but must not duplicate exact project standards or domain
values that belong in guides.

Do not encode these exact values in entrypoint managed regions:

- Work-item or ticket prefixes, example ticket keys, tracker project keys, branch patterns, commit-message formats, MR/PR target branches, merge strategy details, or adapter-specific workflow details.
- Exact build, lint, test, deploy, setup, or verification commands when a generated guide such as `.agentic/guides/quality-gates.md`, `.agentic/guides/project.md`, or `.agentic/guides/standards/git-workflow.md` exists to hold them.
- Detailed architecture, logging, security, testing, database, or integration standards that can be referenced by guide path.
- Repeated operating reminders, padding, or copied guide prose.

Use references instead: state the trigger and the guide path to load. Exact
values remain in the generated guides, where they can be audited and updated
without bloating the entrypoint.

## Region bodies

### `guide-imports`

Markdown table:

```markdown
| Category | Guide Path | Purpose |
|---|---|---|
| Architecture | .agentic/guides/architecture/architecture.md | <one-line purpose extracted from guide H1 description> |
| ... |
```

For monorepo root entrypoint, list modules instead:

```markdown
| Module | Entrypoint | Guides |
|---|---|---|
| apps/web | apps/web/CLAUDE.md | apps/web/.agentic/guides/ |
| ... |
```

### `task-classifier`

Markdown table mapping intent → P0/P1 guides. Include only categories that have generated guides. Schema:

```markdown
| Category | User Intent | Example Requests | P0 Guide | P1 Guide |
```

### `critical-rules`

Mandatory rules (always present):

```markdown
| Rule | Trigger | Action |
|---|---|---|
| Check Guides First | ANY task | Match request → category → load P0 guide BEFORE searching codebase |
| Testing | "write tests" / "run tests" | ONLY then |
| Git Operations | "commit" / "push" / "PR" | ONLY then; load `.agentic/guides/standards/git-workflow.md` |
| Shell | ANY shell command | bash/Linux syntax only |
```

Append project-specific operational rules discovered in Phase 1 only as
references to generated guides. Do not include exact values such as ticket
prefixes, branch formats, command strings, target branches, environment names,
or adapter instructions in the entrypoint. Put those values in
`.agentic/guides/project.md`, `.agentic/guides/standards/git-workflow.md`,
`.agentic/guides/quality-gates.md`, or the relevant category guide.

### `commands`

Reference-only markdown table of command needs and guide paths. Source of truth
for exact commands is `.agentic/guides/quality-gates.md` plus the underlying
manifests (`package.json`, `Makefile`, `pyproject.toml`, `Cargo.toml`, etc.).
Never invent commands and do not duplicate exact command strings in
`AGENTS.md`/`GEMINI.md`/`CLAUDE.md` when a generated command guide exists.

Schema:

```markdown
| Need | Source Guide | Source Evidence | Notes |
|---|---|---|---|
| Lint / format | `.agentic/guides/quality-gates.md` | `Makefile`, manifest, or CI file | Load guide before running. |
```

## Cross-file imports per tool

- `CLAUDE.md` supports `@<path>` imports. In single-repo projects where
  `AGENTS.md` is generated, `CLAUDE.md` should contain only a short purpose line
  plus a managed `@AGENTS.md` import.
- For monorepos, root `CLAUDE.md` may import `AGENTS.md`; module-specific Claude
  shims may import their nearest module `AGENTS.md` only when module entrypoints
  are generated.
- `AGENTS.md` and `GEMINI.md` have no native import directive at time of writing — root file uses a plain markdown link table to module files. Note this in the `guide-imports` region header so users know what to expect.

## Merge algorithm

1. Read existing entrypoint file (if any).
2. Confirm the Phase 2 merge plan approved this target file. If not approved, skip it.
3. Detect file presence and size. If `AGENTS.md` is empty or missing, render the full managed entrypoint body from `references/templates/AGENTS.md.template`. If `CLAUDE.md` is empty, missing, or selected as a secondary target while `AGENTS.md` is primary, render `references/templates/CLAUDE.md.template` only. If `GEMINI.md` is empty or missing, render a full reference-style body from `references/templates/AGENTS.md.template` with the title adjusted.
4. For each managed region:
   - Locate `start`/`end` markers via regex match.
   - If both markers present and content matches the auto-generated body byte-for-byte → no change.
   - If markers present and content differs → diff and queue for replacement.
   - If markers missing → queue an append at the end of the file under a new heading.
   - If only one marker is present → halt; managed-region integrity is unsafe.
   - If the audit or plan says `preserve` or `skip` for the region → leave unchanged.
   - If the audit or plan says `ask user` → ask before adding the region to the diff.
   - If the audit or plan says `halt` → stop the run.
5. Build a unified diff of all queued changes per file.
6. **Gate:** show diff to user, require approval before writing.
7. Write changes; preserve heading hierarchy and front-matter.

## User edits inside a managed region

If the inner body of a managed region differs from the previously generated body but matches the user's customization (heuristic: extra lines outside the auto-generated table format), prompt:

- **Overwrite** — replace with new auto-generated body.
- **Append below as comment** — keep user version, append new auto body inside the same region as `<!-- agentic-init:auto-update -->` block.
- **Skip region** — leave the region unchanged for this run.

## Multi-target gating

When Phase 1 detected multiple AI-tool targets (e.g., `.claude/` and `AGENTS.md`):
- Produce one diff per target file.
- Ask user once per file (one approval per file, not one bulk approval).
- Targets are independent — user may approve one and skip another.

## No-overwrite invariants

- Never delete a managed region whose markers are present (always either replace body or skip).
- Never write outside the managed regions when merging unless the user separately and explicitly approved that exact non-managed change.
- Never leave duplicated generated guide tables, task classifiers, command tables,
  or stale guide references in `CLAUDE.md` when `AGENTS.md` is the approved
  primary entrypoint and the user approved the Claude shim diff.
- Never write the entrypoint file at all if user did not approve the diff.
- Never encode commands, guide paths, or assistant rules from weak, missing, or conflicting evidence without user confirmation.
- Never encode exact project/domain standards in the entrypoint when a generated guide can hold them; route to the guide instead.
