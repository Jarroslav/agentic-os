# Changelog

Notable changes to the `agentic-qe` plugin. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this plugin uses
Semantic Versioning and its own release tag (`agentic-qe-v<X.Y.Z>`).

## [Unreleased]

### Fixed

- **`qe-blueprints` no longer collides with a governed repo.** It wrote full
  agent contracts to `.claude/agents/<name>.md` — a path `agentic-os` owns as
  journaled *thin pointers* to canonical contracts — and wrote repo-root
  `CLAUDE.md`, which `agentic-os` manages as a marker-delimited block replaced
  wholesale on upgrade. Both were silent corruption of an install this plugin
  did not know was there.

  Step 2 now detects `.agentic/agentic-os/install.json` and routes accordingly:
  contracts to the canonical agents dir (resolved from `journal.adoption` when
  the repo adopted an existing fleet, never hardcoded), `.claude/agents/` left
  to the installer's pointer synthesis, and the context file appended strictly
  outside the managed markers. Ungoverned repos are unaffected — the standalone
  path is unchanged, and `/agentic-init` is still never required.

- **A refused write is now reported, not routed around.** `guarded_write_paths.py`
  is fail-closed (exit 2), so a governed repo guarding `.claude/agents` or
  `CLAUDE.md` could stop the scaffolder mid-run with no documented behaviour.
  Step 5 now names the refused path and the rule that produced it, and forbids
  retrying, relocating to evade the guard, or summarizing files that were never
  written.

### Added

- **`write_scope` in generated contracts, in governed repos only.** The
  frontmatter allowlist banned every key beyond `name/description/tools/model`
  on the grounds that the runtime ignores them — correct in general, and wrong
  for this one key in a governed repo, where `write_scope_guard.py` parses it
  and enforces it at the tool call. The value comes from the blueprint role
  table's existing **Writes** column, so this is a rename rather than a new
  decision. Without it a write-capable QE agent was the one unbounded agent in
  an otherwise scope-enforced repo. Still omitted when ungoverned, where
  nothing reads it.

- A note in `eval-harness` distinguishing the `eval/` specs it generates into
  *your* repo from the `evals/` contract dir this marketplace's own CI requires
  of the skills it *ships*. Different scope and different owner; they only meet
  if you point the skill at the marketplace repo itself.

## [0.1.1]

### Changed

- Both skill descriptions (`qe-blueprints`, `eval-harness`) now carry an
  explicit `Not for:` routing clause per the agentic-os 0.4.0 contract
  standard (CI-enforced for new skills).

## [0.1.0] — initial public release

### Added

- Initial release of the `agentic-qe` plugin: a tool-agnostic catalog of
  Quality Engineering AI blueprints plus the skills to act on them, written
  in the agentic-os design language (blast-radius role tags R0–R3, human
  review gates before any R2/R3 step, model tiers economy/standard/premium,
  explicit grounding rules).
- **`qe-blueprints`** skill — 28 QE blueprints organized by STLC stage
  (`catalog/{analyze,design,build,execute,operate,report}/`), supported by
  `method/` (untrusted-content defense, agent topologies, context economy,
  tool access, design checklists), `platforms/` (Claude Code / Cursor /
  GitHub Copilot guides, connector catalog, unattended automation, model
  tiers), and `templates/` (scaffold building blocks). The skill interviews
  the user, matches intent to a blueprint, and scaffolds a ready-to-fill
  agent framework via `scripts/scaffold.{sh,ps1}`.
- **`eval-harness`** skill — generates a two-layer evaluation framework
  (deterministic contract checks + LLM-judge behavioral cases) for a repo of
  skills and agents, in TypeScript or Python, with a provider abstraction.
