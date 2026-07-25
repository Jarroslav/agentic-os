# Changelog

Notable changes to the `agentic-os` plugin, as distributed here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this distribution uses
Semantic Versioning. The plugin version lives in
[`.claude-plugin/plugin.json`](.claude-plugin/plugin.json).

## [0.1.0] — initial public release

First public version.

### Added

- **Six-screen installer** (`/agentic-init`): role presets, HITL dial, autonomy
  matrix, gates, stack confirm, ticket/MR adapter. `--defaults` accepts every
  detected default. Local hook/session state (`.claude/.review-stamp`,
  `.claude/checkpoints/`, `.agentic/state/`) is gitignored at install.
- **Seven role presets** (developer, QA, BA/PO, architect, devops, PM/delivery,
  portfolio), additive — install several and their template sets union
  (strictest HITL wins).
- **The HITL enforcement pillar**: policy files (autonomy matrix + escalation
  ladder), the output-contract parser, and hard exit-2 PreToolUse gates
  (blind pre-commit review, write-scope guard, guarded write paths, human-gated
  commands, instruction-quality spawn gate). Block gates fail closed on input
  they cannot evaluate.
- **Evidence-grounded stack discovery**: six curated profiles (Next.js/Supabase,
  Django, Spring, Rails, Go, Playwright) recognized instantly; anything else gets
  a full from-scratch inspection, not a degraded stub.
- **Generated, audited agent contracts** and stack guides for the detected stack,
  each graded against the instruction-quality rubric before being armed.
- **Advisory + safety hooks**, installed per preset:
  - *Prompt-scan guard* (UserPromptSubmit) — catches secrets pasted into
    prompts before they are sent, using generic shape classes only (private-key
    blocks, JWTs, credential assignments, basic-auth URLs, Luhn-valid card
    numbers, high-entropy tokens near credential keywords) plus warn-only email
    PII; modes `warn`/`block`/`audit`, masked audit trail, fails open.
  - *Context-monitor* (PostToolUse, advisory-only) — announces context usage
    at 65%/75% thresholds ahead of the PreCompact checkpoint hook.
  - *Lint-on-save* (PostToolUse Write/Edit) — fix-then-recheck on each saved
    source file; remaining errors surface in the same turn. Fails open on
    missing, broken, or unconfigured linters.
  - *Session-learnings notice* (Stop, advisory-only) — detects correction
    signals in the transcript and nudges capturing the lesson into the durable
    memory store.
- **SDLC host config** (`sdlc/config.json.tmpl`): `context_boundaries`
  (plan→implementation fresh-session notice) and `model_tiers`
  (`economy`/`standard`/`premium`, all defaulting to `"inherit"` — concrete
  model IDs are user-supplied values only; the repo's neutrality scan enforces
  that none ships).
- **`/agentic-doctor`** verification pass (imports each managed hook, not just
  `py_compile`) and **`/agentic-upgrade`** three-way reconciliation
  (see [`docs/UPGRADING.md`](docs/UPGRADING.md)).

No upgrade path from a prior version — this is the first release.
