# Changelog

Notable changes to the `agentic-qe` plugin. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this plugin uses
Semantic Versioning and its own release tag (`agentic-qe-v<X.Y.Z>`).

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
