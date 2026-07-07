# Planning — Phase 2 Reference

Build a guide-generation, incorporation, and merge plan from Phase 1 audit output and present it to the user. **Do not write any files until the audit is complete and the user explicitly approves the presented incorporation and merge plan.**

## Driver: superpowers:brainstorming if available

If the host AI tool exposes `superpowers:brainstorming` (visible in available skills), invoke it via the Skill tool to drive the conversation. Otherwise present the plan inline using the structure below.

**Never auto-install superpowers.** If brainstorming is missing, fall back to inline plan + native subagent capability.

## Plan content

Required sections in the plan output:

1. **Detected shape** — single or monorepo, with brief evidence (e.g. "pnpm-workspace.yaml at root").
2. **Modules table** (monorepo only) — `path | language | framework | build | test`.
3. **Audit summary** — `Documentation Map`, `Documentation Analysis`, `Assistant Setup Analysis`, `Agentic Infrastructure Analysis`, `Conflict And Overlap Analysis`, and `Foundation Readiness And Next Steps` actions that drive the plan.
4. **Entrypoint target(s)** — list of files that will be created or merged into, with the audit recommendation for each target.
5. **Output dirs** — `.agentic/guides/` for single, `<module>/.agentic/guides/` per module for monorepo.
6. **Incorporation map** — required when the audit recommends `incorporate`; list the existing documentation source, the factory-owned destination, and any decision needed about whether the original documentation remains authoritative.
7. **Per-scope guide list** — for each scope, a table of categories:

| Category | Action | Proposed guide files | Audit recommendation | Evidence |
|---|---|---|---|---|
| Architecture | create / incorporate / update / preserve / replace / merge / skip / ask user / halt | `.agentic/guides/architecture/architecture.md` | `incorporate` | `src/foo.ts:12, docs/arch.md:8` |

Action rules map audit recommendations to foundation behavior:

| Audit recommendation | Plan action | Required foundation behavior |
|---|---|---|
| `preserve` | `preserve` or narrowly scoped `update` | Keep strong human-authored guidance as the source of truth; do not rewrite it unless the plan names the managed section or guide subsection to update. |
| `incorporate` | `incorporate` | Ingest useful existing documentation into the approved factory-owned destination; list the source-to-destination mapping and ask whether the original documentation remains authoritative, is superseded for AI guidance, or stays host-specific. |
| `replace` | `replace` | Propose replacement for stale generated content or incorrect guidance; require an approved diff before replacing guide or managed-region content. |
| `merge` | `merge` | Combine useful existing guidance only when it is already the same authority surface or an approved compatible managed region/guide target; list what will be retained and what will be added. |
| `skip` | `skip` | Exclude the area from generation or wiring and record the reason. |
| `ask user` | `ask user` | Stop before writes and ask a concrete question; re-render the plan after the answer. |
| `halt` | `halt` | Stop the run; do not proceed to Phase 3 or Phase 4 until the blocker is resolved. |

If the audit marks existing documentation as useful but not the long-term factory-owned output, use `incorporate`, not `merge`. Never plan "update in place" as the primary action when the intended result is factory-owned guidance.

Legacy create/update mapping is allowed only after applying audit recommendations:

- `create` — no existing guide at target path and audit evidence is `partial` or `missing` with concrete repository evidence.
- `update` — existing guide present; only managed sections will be refreshed.
- `skip` — no codebase evidence; record reason ("no API routes detected").

Weak, missing, or conflicting evidence rules:

- If a category rating is `weak`, ask the user for authoritative context or skip the category. Do not generate confident guidance from weak docs alone.
- If a category rating is `missing`, generate only from concrete repository evidence; otherwise skip.
- If a category rating is `conflicting`, ask the user to choose the authoritative source or halt if the conflict affects approval, safety, managed regions, guide source of truth, or quality gates.
- If audit evidence confidence is `low`, treat it as `ask user` unless the category is skipped.
- If guide evidence lacks a concrete `file:line` reference, skip that guide category or ask for evidence before approval.

8. **Entrypoint merge plan** — per target file, list managed regions to add, replace, merge, preserve, skip, ask user, or halt. Changes outside managed regions require a separate explicit approval line.
9. **Subagent dispatch plan** (monorepo only) — list of subagents that will run in parallel, one per module, with the exact module path and approved guide list each will receive.

## Approval gate

Ask the user one of:
- **Approve** → proceed to Phase 3.
- **Customize** → user edits scope (drop a category, change output path, force-skip a module). Re-render plan, ask again.
- **Cancel** → halt; no writes.

Do not proceed to Phase 3 without an explicit approval keyword from the user (e.g. "approve", "yes", "go").

If the audit produced any `ask user` or `halt` recommendation, resolve it before asking for final approval. If the user approves while unresolved `ask user` items remain, treat the approval as incomplete and ask the pending questions first.

## Plan format example (single repo)

```
## Project shape: single repo
Entrypoint target: CLAUDE.md (.claude/ detected)
Output dir: .agentic/guides/
Audit summary: existing README is partial; CLAUDE.md has no managed regions; no conflicts detected.

| Category | Action | Files | Audit recommendation | Evidence |
|---|---|---|---|---|
| Architecture | merge | .agentic/guides/architecture/architecture.md | `merge` | src/cli/index.ts:1, README.md:12 |
| API          | skip  | — | `skip` | no routes detected |
| Testing      | create | .agentic/guides/testing/testing-patterns.md | `merge` | vitest.config.ts:1, src/foo/__tests__/ |
| Development  | update | .agentic/guides/development/development-practices.md | `replace` stale managed block | src/utils/errors.ts:1 |

Incorporation:
| Existing documentation | Factory destination | Decision needed |
|---|---|---|
| Existing architecture/testing docs | Factory-owned architecture/testing guides | Ask whether the original docs remain authoritative or become references |

Entrypoint merge:
| Target | Managed regions | Outside managed regions |
|---|---|---|
| CLAUDE.md | add guide-imports, task-classifier, critical-rules, commands | preserve existing content |

Subagents: none (single repo runs in main session)

Approve / Customize / Cancel?
```

## Plan format example (monorepo)

```
## Project shape: monorepo (pnpm-workspace.yaml)
Modules: 3
| Path        | Language   | Framework | Build  | Test    |
|-------------|------------|-----------|--------|---------|
| apps/web    | TypeScript | Next.js   | next   | vitest  |
| apps/api    | TypeScript | Fastify   | tsup   | vitest  |
| packages/ui | TypeScript | React     | tsup   | vitest  |

Entrypoint targets: CLAUDE.md (root) + apps/web/CLAUDE.md + apps/api/CLAUDE.md + packages/ui/CLAUDE.md
Audit summary: AGENTS.md and CLAUDE.md agree on test commands; apps/api docs are partial; no duplicate guide trees.

Per-scope guide plans:
- apps/web:    merge architecture, api, testing, development
- apps/api:    ask user about data ownership, then merge architecture, api, testing, development, security
- packages/ui: create development, testing from concrete package evidence
- root:        guide-imports table only (no root-level guides)

Subagents (parallel): 3 — one per module, each writes <module>/.agentic/guides/.

Approve / Customize / Cancel?
```
