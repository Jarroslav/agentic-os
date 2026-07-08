# Changelog

Notable changes to the `agentic-os` plugin, as distributed here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this distribution uses
Semantic Versioning. The plugin version lives in
[`.claude-plugin/plugin.json`](.claude-plugin/plugin.json).

## [Unreleased]

Fixes to the 0.3.0 codebase, not yet version-bumped. All are correctness fixes
found by an end-to-end install audit against a non-curated stack.

### Fixed

- **Template rendering escapes interview answers.** A value containing quotes,
  backslashes, or newlines (e.g. `alembic revision -m "<msg>"`) used to render a
  syntactically broken — or worse, a compiles-clean-then-crashes — hook.
  `/agentic-doctor` now imports each managed hook, not just `py_compile`s it.
- **PreToolUse block gates fail closed.** A malformed `{"tool_input": null}` event
  crashed the four block gates (exit 1 = non-blocking on PreToolUse), letting the
  guarded action — including an unreviewed commit — through. They now block on any
  input they cannot evaluate.
- **`quality-gates.md` is rendered from the detected gate commands** instead of
  shipping an empty registry plus a placeholder example.
- **`PATTERNS.md` indexes only guides that were installed** (the qa-only rows are
  conditional on the preset), and **generated stack guides are registered** in it,
  regenerated from the install journal on upgrade.
- **Screen-3 autonomy answers are recorded** in `ai-policy.md` (a tighten-only
  per-repository override block) instead of being collected and discarded.

## [0.3.0] — initial public release

First public version.

### Added

- **Six-screen installer** (`/agentic-init`): role presets, HITL dial, autonomy
  matrix, gates, stack confirm, ticket/MR adapter. `--defaults` accepts every
  detected default.
- **Five role presets** (developer, QA, BA/PO, architect, delivery), additive —
  install several and their template sets union (strictest HITL wins).
- **The HITL enforcement pillar**: policy files (autonomy matrix + escalation
  ladder), the output-contract parser, and hard exit-2 PreToolUse gates
  (blind pre-commit review, write-scope guard, guarded write paths, human-gated
  commands, instruction-quality spawn gate).
- **Evidence-grounded stack discovery**: six curated profiles (Next.js/Supabase,
  Django, Spring, Rails, Go, Playwright) recognized instantly; anything else gets
  a full from-scratch inspection, not a degraded stub.
- **Generated, audited agent contracts** and stack guides for the detected stack,
  each graded against the instruction-quality rubric before being armed.
- **`/agentic-doctor`** verification pass and **`/agentic-upgrade`** three-way
  reconciliation (see [`docs/UPGRADING.md`](docs/UPGRADING.md)).

No upgrade path from a prior version — this is the first release.
