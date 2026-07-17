# Wiring AI Entrypoint Files Without Clobbering Existing Content

Reference for phase 4 of the repo-guides flow. You are injecting generated
guidance — guide-import tables, a task classifier, mandatory rules, and command
references — into a project's AI-assistant entrypoint through marker-delimited managed
regions. Every write is a repo-file write (blast radius **R2**) and is gated behind an
explicit per-file diff approval. You never generate guide bodies here; you only wire
references to guides that earlier phases already produced.

> Entrypoints are routing surfaces, not standards manuals. A region names the trigger
> and the guide path — never the exact values (ticket prefixes, branch patterns, commit
> formats, target branches, command strings, environment names, adapter details).
> Concrete values live in the generated guides under `.agentic/guides/`.

## Inputs you must have

You cannot run this phase from scratch. It consumes two upstream products:

| Input | Produced by | What you read from it |
| --- | --- | --- |
| Per-target recommendations + evidence ratings | Phase 1 repository / assistant-setup audit | Which files exist, detection signals, `preserve`/`replace`/`merge`/`skip`/`ask user`/`halt` per target, and ratings for commands, assistant authority, managed-region integrity, and guide source-of-truth |
| Approved entrypoint merge plan | Phase 2 (user-approved) | Which target files and which regions you are cleared to touch |

If the plan does not name a target or a region, you have no mandate for it — skip it.

## Entrypoint targets and how to resolve them

Three canonical targets exist: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`.

- `AGENTS.md` is the canonical generated entrypoint.
- When Claude Code is also present, `CLAUDE.md` becomes a thin **shim** that only imports
  `AGENTS.md`. The shim body is exactly one purpose line plus a managed `@AGENTS.md`
  import — nothing else.
- `GEMINI.md` renders from the `AGENTS.md` template with the title adjusted.

Resolve the target set from phase 1 detection signals:

| Phase 1 signal | Resolves to |
| --- | --- |
| `.claude/` | `CLAUDE.md` shim + `AGENTS.md` primary |
| `AGENTS.md` already exists, or `.codex/` present | `AGENTS.md` |
| `.gemini/` present, or `GEMINI.md` exists | `GEMINI.md` |
| Multiple of the above | Each resolved file gets its **own** independently gated diff |
| No signal at all | Ask the user; default to `AGENTS.md` |

> `CLAUDE.md` supports `@<path>` imports; `AGENTS.md` and `GEMINI.md` do not. In those
> two files, root-level references link to module files with a plain markdown table, and
> the guide-imports region header states this limitation so a later reader does not try
> to add `@`-imports there.

## The four managed regions

Everything inside a region's markers is yours to render. Everything outside them is
human-authored and untouchable by default — see the shim exception below. Markers are an
integration contract; reproduce them byte-for-byte:

```
<!-- agentic-init:guide-imports start -->   … <!-- agentic-init:guide-imports end -->
<!-- agentic-init:task-classifier start --> … <!-- agentic-init:task-classifier end -->
<!-- agentic-init:critical-rules start -->  … <!-- agentic-init:critical-rules end -->
<!-- agentic-init:commands start -->        … <!-- agentic-init:commands end -->
```

Auto-update comment block marker (used only in the human-edit path below):

```
<!-- agentic-init:auto-update -->
```

### Region table schemas

Render each region body as a markdown table with these exact headers:

| Region | Header row |
| --- | --- |
| guide-imports | `| Category | Guide Path | Purpose |` |
| guide-imports (monorepo) | `| Module | Entrypoint | Guides |` |
| task-classifier | `| Category | User Intent | Example Requests | P0 Guide | P1 Guide |` |
| critical-rules | `| Rule | Trigger | Action |` |
| commands | `| Need | Source Guide | Source Evidence | Notes |` |

Content constraints:

- **guide-imports** — the `Purpose` column is a one-line extract from each guide's H1
  description. Do not paraphrase standards into it.
- **task-classifier** — include only categories that actually have a generated guide.
  Never list a `P0 Guide` / `P1 Guide` path that does not exist on disk.
- **critical-rules** — see the mandatory catalog below.
- **commands** — never invent commands, and never duplicate an exact command string in
  any entrypoint when a generated command guide exists. Point at the guide instead.

## Mandatory critical-rules rows

Always emit these four rows in the critical-rules region:

| Rule | Trigger | Action |
| --- | --- | --- |
| Check Guides First | ANY task | Match the request to a category and load its P0 guide before searching the codebase |
| Testing | Test-writing or test-running requests | Consult the testing guide first, and only then write or run tests |
| Git Operations | Commit, push, or PR requests | Load `.agentic/guides/standards/git-workflow.md` first, and only then perform the operation |
| Shell | ANY shell command | Use bash / Linux syntax only |

Project-specific rules discovered in phase 1 enter this region **only as guide-path
references** — never as inline values. Their concrete content belongs in
`.agentic/guides/project.md`, `.agentic/guides/standards/git-workflow.md`,
`.agentic/guides/quality-gates.md`, or the matching category guide.

## Commands region

Source command evidence from manifest files — `package.json`, `Makefile`,
`pyproject.toml`, `Cargo.toml` — plus any CI file. Cite the evidence; route the reader to
the guide; do not paste the command.

| Need | Source Guide | Source Evidence | Notes |
| --- | --- | --- | --- |
| Lint / format | `.agentic/guides/quality-gates.md` | `Makefile`, manifest, or CI file | Load the guide before running; do not inline the command string |

## Region state machine

Evaluate each region independently against the freshly generated body:

| Existing state | Action |
| --- | --- |
| Both markers present, body byte-for-byte identical | No-op — queue nothing |
| Both markers present, body differs | Queue a replacement of the region body |
| No markers present | Queue an append under a new heading at end-of-file |
| Exactly one marker present | **Halt** — integrity is unsafe |
| Malformed markers | **Halt** — never silently repair them |
| Duplicate regions | Ask the user, unless audit evidence proves one copy is stale generated content |

Two hard rules layered on top:

- An **existing** region updates by default only if the phase 2 plan approved that
  region.
- A **missing** region appends only after its per-file diff is approved.

> The byte-for-byte identity check is what makes re-runs idempotent. If nothing about the
> generated body changed, the region is left exactly as-is and never appears in a diff.

## Merge algorithm

Run this order per target file:

1. Read the existing file.
2. Confirm the phase 2 plan approved this target — otherwise skip it.
3. If the file is empty or missing, template-render it from
   `references/templates/AGENTS.md.template` or `references/templates/CLAUDE.md.template`
   (`GEMINI.md` reuses the AGENTS template with an adjusted title).
4. Apply per-region state handling from the table above.
5. Build one unified diff for this file.
6. Present the diff at the user-approval gate.
7. Write only after approval.

Preserve heading hierarchy and front-matter through every step. A write never reorders or
strips headings outside the regions it owns.

## Audit-recommendation mapping

Translate each phase 1 recommendation into behavior:

| Recommendation | Behavior |
| --- | --- |
| `preserve` | Keep existing content; update only approved regions |
| `replace` | Swap stale region bodies, after a diff and per-file approval |
| `merge` | Append or refresh regions; keep useful human-authored sections |
| `skip` | Leave the target or region alone this run |
| `ask user` | Pause before diffing and pose the open question |
| `halt` | Abort; write nothing |

When phase 1 rates the evidence `weak`, `missing`, or `conflicting` for commands,
assistant authority, managed-region integrity, or guide source-of-truth, do **not**
synthesize confident content. Follow the audit: ask, skip, or halt.

## Human edits inside a region

If the region carries both markers but the body shows edits beyond the generated table
format (heuristic: extra lines the generator would not have produced), do not overwrite
blindly. Prompt with three options:

- **Overwrite** — replace the region body with the freshly generated table.
- **Append-below-as-comment** — keep the human body in place and stash the generated body
  inside the region as an auto-update comment block delimited by `<!-- agentic-init:auto-update -->`.
- **Skip region** — leave it untouched this run.

## Shim and monorepo handling

**Shim exception.** When the plan designates `AGENTS.md` primary and `CLAUDE.md` a shim,
legacy generated Claude content *outside* markers may be replaced — but only after a
file-specific diff and explicit approval for that one file. Once the shim diff is
approved, the shim must not retain duplicated generated tables, a duplicated classifier,
or stale guide references; its body collapses to the one purpose line plus the managed
`@AGENTS.md` import.

**Monorepo.** The root guide-imports region uses the monorepo schema
`| Module | Entrypoint | Guides |` and lists modules (module path, module entrypoint,
module guides dir) instead of guides. Module-level Claude shims import their nearest
module `AGENTS.md` — but only if that module's entrypoint was actually generated.

## Multi-target gating

One diff per target file. One approval per file. Never a bulk approval spanning files.
Targets are independently approvable — the user may accept `AGENTS.md` and decline
`GEMINI.md` in the same run.

## No-overwrite invariants

Hold these on every path:

- Never delete a region while its markers are present — replace or skip only.
- Never write outside a region without that exact file-and-content-specific approval.
- Never write at all without a diff approval; no unattended writes.
- Never leave duplicated generated tables, classifiers, or stale guide refs in the Claude
  shim once its diff is approved.
- Never encode content built on `weak`, `missing`, or `conflicting` evidence without
  confirmation.
- Never inline a standard, command string, or domain value that a guide can hold.
- Never silently repair or auto-complete broken or half-present markers.

## What this phase is not

- Not a generator of guide content — it only wires references to already-generated guides.
- Not an author of project standards, command strings, or domain values.
- Not a bulk writer — every file write is diff-gated, one file at a time.
