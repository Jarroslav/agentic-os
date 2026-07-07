# Generation — Phase 3 Reference

Render approved guides from templates. Honor placeholder contract, content style, size caps, and existing-content rules.

## Authoring rules

Load `references/knowledge-craft.md` before writing any guide content. All
generated content must conform to the rules in that file — content style,
structure, size caps, placeholder contract, evidence rule, and quality standards.

## Existing-content handling

- **No existing guide at target path** → render fresh from template.
- **Existing guide present** → preserve user content, refresh only outdated bits (commands, broken `file:line` refs, framework version in headers).
- **Outdated guide that no longer matches code** → flagged in Phase 2 with `update` action; never silently overwritten.

## Single-repo flow (main session)

For each approved guide:
1. Read template from `references/templates/guides/<category>/<file>.md.template`.
2. Resolve placeholders from Phase 1 discovery + extracted `file:line` references.
3. Apply content-style rule (drop heavy code, keep practices + references).
4. Write to `.agentic/guides/<category>/<file>.md`.
5. Verify the hard size cap and generated-content quality gates.
6. If useful content is shorter than historical targets, stop; do not add padding.

`project.md` is not rendered from general guide templates. It must follow the
Project Context schema in `SKILL.md` Step A. If project settings discovery finds
git conventions, command details, task routing, package ownership, or validation
reporting policy, write that content to the appropriate guide instead of
`project.md`: git workflow, quality gates, entrypoint regions, architecture, or
tool guides.

## Monorepo flow (parallel subagents)

Dispatch one subagent per module, all in **one message** (parallel).

- Use `superpowers:dispatching-parallel-agents` if available.
- Otherwise call the Agent tool directly with `subagent_type: "general-purpose"`, one call per module, in the same message.

Each subagent receives:
- Module path (absolute or repo-relative).
- Approved guide list for that module (categories + target files).
- Per-module discovered stack values.
- Path to `references/templates/guides/` to read templates from.
- Path to `references/generation.md` (this file) for the rules.

Each subagent returns a structured summary:
```
{
  module: <path>,
  written: [list of file paths],
  line_counts: { <path>: <int> },
  placeholders_resolved: [list],
  placeholders_dropped: [list],
  warnings: [list]
}
```

Main session aggregates the summaries and forwards to Phase 5 validation.

## Failure modes

- Subagent returns malformed/missing output → main session re-dispatches **only that module** with the same input.
- Subagent reports a guide over the size cap → main session asks user to drop or condense before continuing to Phase 4.
- Subagent returns reminder/filler padding or repeated near-identical lines → reject the guide and re-render without padding before continuing.
- Subagent writes project drift into `project.md` → move the drift to the owning guide before continuing.
