# Planting Advice

Map every audit finding to exactly one action from a fixed seven-value vocabulary. You recommend; you never write. A later foundation step executes writes under its own approval gates — your job ends at a specific, defensible recommendation.

> Rationale: the audit is R0 (read-only). Keeping the write authority in a separate, gated step means a bad recommendation costs a review cycle, not a corrupted repo.

## Output contract

Emit recommendations inside the report section headed exactly:

`## Foundation Readiness And Next Steps`

Use this table shape, columns verbatim:

`| Area | Finding | Action | Later foundation implication |`

Constraints:

- The Action cell holds one token from `preserve|incorporate|replace|merge|skip|ask user|halt` — nothing else, no combinations except where the mapping below explicitly allows two candidates (pick one; if you cannot, that itself is `ask user`).
- Name the concrete files in Finding (`AGENTS.md`, `CLAUDE.md`, specific docs) — never "the documentation".
- Never state or imply that a file was changed. No edits happened; none will happen in this phase.
- No grading, scoring, or rubric sections anywhere in the report.

## Action vocabulary

| Action | Recommend when | What foundation does later |
|---|---|---|
| `preserve` | Existing docs are strong, current, and compatible with the plugin | Docs stay the authoritative source agents read directly; no rewrite |
| `incorporate` | Docs carry real knowledge worth reusing as raw material | Ingests the knowledge into factory-owned guidance; the original's fate (authoritative / legacy / tool-specific) is decided separately |
| `replace` | Guidance is stale, generic, wrongly generated, or contradicted by repo evidence | Proposes a replacement via a gated diff or guide update |
| `merge` | Existing content and generated output already target the same authority surface or a compatible managed-region/guide destination | Combines the two after approval |
| `skip` | Area is absent, irrelevant, or out of scope | Generates nothing unless the user asks |
| `ask user` | Evidence is ambiguous, authority is unclear, or the choice shapes future writes | Blocks on a concrete question before touching the area |
| `halt` | Unsafe, destructive, or approval-bypassing conditions; broken managed-region markers | No planting at all until the condition is resolved |

## Finding-to-action map

| Finding | Action | Why |
|---|---|---|
| Strong README plus architecture docs, still accurate and authoritative | `preserve` | Rewriting good docs adds risk and zero value |
| Strong assistant entrypoint whose content sits outside managed regions | `preserve` | Human-authored policy stays intact; the plugin only owns managed regions |
| Rich docs that should feed generated guidance | `incorporate` | Knowledge flows into the approved factory-owned destination — not in-place edits |
| Existing skills, commands, or subagents with minor gaps | `incorporate` or `ask user` | Never silently convert host assets to factory ownership |
| Thin docs, but manifests and CI are clear | `incorporate` | Repo evidence can back generated guidance even when prose is missing |
| Generic docs lacking any project detail | `replace` | Boilerplate misleads agents; propose grounded replacement later |
| Stale generated content inside managed regions | `replace` | Refresh belongs in a gated diff, not a live edit |
| No assistant entrypoint (`AGENTS.md`, `CLAUDE.md`) exists | `skip` | Auditor never picks or creates the target; foundation raises `ask user` later |
| Multiple assistant entrypoints that mostly agree | `ask user` | Ask which surfaces are actually active before writing to any |
| Duplicate assistant/agentic sources both claiming authority | `ask user` or `halt` | Source of truth must be resolved before any planting |
| Pre-existing agents, skills, commands, prompts, or Copilot instructions competing with the plugin's workflow ownership | `ask user` or `halt` | Ownership conflicts are a user decision, not an auditor default |
| Test commands in docs conflict with what CI runs | `ask user` | Wrong gates produce false confidence in every later phase |
| Malformed managed-region markers | `halt` | An automated entrypoint merge could corrupt surrounding content |
| Approval-bypass or destructive defaults discovered | `halt` | No planting on top of an unsafe baseline |

## The in-place guardrail

Never recommend editing a useful existing doc in place when foundation will own the resulting guidance. An existing doc has exactly two legitimate roles:

1. It stays authoritative → `preserve`.
2. It serves as an ingested source → `incorporate`.

In-place `merge` or update is valid only when the content already **is** the approved authority surface, or a compatible managed target (a managed region inside an entrypoint, or an established guide destination).

> Rationale: "improve the doc in place" blurs ownership. Six months later nobody knows whether a human or the factory wrote a paragraph, and every regeneration becomes a merge-conflict negotiation.

## Quality bar

A recommendation is usable when it names the artifacts and, for `ask user`, states the exact question.

Good:

- "`CLAUDE.md` and `AGENTS.md` both define test commands and both read as current — `ask user`: which entrypoint do active agents load, and should the other become legacy?"
- "`docs/architecture.md` is accurate and referenced from CI — `preserve`."
- "`docs/setup.md` explains the local toolchain well — `incorporate` into factory-owned guidance; do not edit it in place."

Bad:

- "Docs need improvement." (No file, no action, nothing executable.)
- "Update `CLAUDE.md` to add missing sections." (In-place edit of content the factory intends to own; also claims a write the auditor must not make.)
- "Merged the two entrypoints." (Past-tense write claim — the audit changes nothing.)

## Out of scope

- Performing any file change, doc update, or write of any kind.
- Choosing or creating an assistant entrypoint when none exists.
- Defining managed-region marker syntax, gated-diff mechanics, or the foundation write process.
- Adding grading or scoring rubrics to audit output.
