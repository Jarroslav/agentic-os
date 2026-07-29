# Changelog

Notable changes to the `agentic-sdlc` plugin, as distributed here. Format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this plugin
uses Semantic Versioning and its own release tag (`agentic-sdlc-v<X.Y.Z>`).

## [Unreleased]

### Changed

- **The five QA skills now name their methodology owner.** `qa-foundation`,
  `qa-planner`, `qa-case-generator`, `qa-e2e-generator` and `test-heal` each
  restated method the `agentic-qe` blueprint catalog also defines —
  `qa-case-generator` against `design/test-cases.md`, `test-heal` against
  `execute/flaky-debugging.md`, and so on — with no cross-reference in either
  direction. Two sets of practices for one job is the divergence the no-forking
  rule exists to prevent, and it is how two agents end up following different
  guidance for the same task.

  Each skill now cites the blueprint that owns its method and states precedence
  plainly: the skill executes, the blueprint is the authority, and where they
  disagree the blueprint wins and the skill is what gets corrected.
  **No skill's runtime behaviour changes** — these are executable pipeline steps
  and they still run exactly as before. The catalog is the source of truth for
  *method*, not a replacement for the code that does the work.

## [0.4.1]

### Added

- **The required contract blocks on all five agents** — `codebase-scout`,
  `guide-sync`, `lead-proxy`, `sizing-analyst`, and `story-proxy` now each
  carry a `Not for:` routing clause, a `## Decision rules` DO/DON'T table, a
  `## Stop and ask when` block, and an escalate-never-decide list. The 0.4.0
  retrofit covered all 26 skills but no agent; `tests/lib/check-agent-contract.py`
  in agentic-os now enforces the same blocks here.
- **`## Escalate, never decide` as an accepted spelling of the escalation
  block** — `lead-proxy` and `story-proxy` are contractually forbidden from
  escalating (decision-router owns every human contact, triggered by their
  `confidence` field). Their stop-and-ask blocks emit an immediate
  low-confidence verdict rather than prompting a user, so the contract no
  longer has to contradict itself to satisfy the rubric.

### Fixed

- **`story-proxy.md` frontmatter was unparseable YAML.** Its bare unquoted
  `description` contained `<example>Context:`, which a strict YAML reader takes
  as a nested mapping — the agent would fail to load in any host that parses
  frontmatter properly. Now a folded block scalar.

### Changed

- **`lead-proxy.md` heading levels normalized** from `#` to `##` for top-level
  sections (gate subsections demoted to `###`), matching every other agent
  contract in both plugins.

## [0.4.0]

### Changed

- **Every skill description now carries a literal `Not for:` routing clause**
  — all 26 skills, each clause accurate to that skill's adjacent-but-wrong
  routing targets (e.g. requirements-intake vs planning; qa-case-generator vs
  qa-e2e-generator; sdlc-task vs sdlc-start/sdlc-autonomous/sdlc-light).
  Existing prose negatives were converted to the literal form without losing
  meaning. This pays down the recurring D2 "routing negative space" partial
  from the blind role-grading waves, and the CI grandfather list is gone:
  `check-skill-contract.py` now enforces the clause on every skill, hard.

## [0.3.0]

### Added

- **Inlined-rule drift check in `guide-sync`.** After applying approved guide
  edits, the agent now greps agent contracts and command pointers for
  `agentic-os:rules` provenance markers (spec: the agentic-os
  `working-with-agents.md` § Rule provenance markers), and reports — never
  edits — every marked digest whose source guide changed in the run, plus any
  dangling `source` path, under a new `Inlined-rule drift` list in its report.
  Fixing a drifted contract remains an `/agentic-upgrade` regeneration or a
  human edit.

## [0.2.0]

### Changed

- **`sdlc.html` rebuilt from `references/architecture.md`.** The page was stale
  in ways that were invisible until clicked: its inventory cited seven files that
  do not exist (five `commands/*.md`, `agents/knowledge-enrichment.md`, and
  `skills/repo-guides/references/knowledge-craft.md`), so the source viewer was
  broken for most nodes, and its version badge disagreed with the manifest. It is
  now generated from the architecture contract and the tree, covers the twelve
  phase skills that were previously missing, and every path it points at is
  checked by `tests/lib/check-html-refs.py`. The six diagrams are laid out from
  node and edge lists rather than hand-placed coordinates, and the two rival CSS
  token vocabularies are now one — together roughly 1,800 fewer lines.
- **Complexity calibration examples replaced.** The previous set contained a band
  mismatch (an example scoring 13/36 → `S` filed under the M band and claiming an
  M outcome). The new examples are drawn from this repo's own work, sum correctly,
  land in their own bands, and include two deliberate sizing misses with notes on
  why — a wrong prediction recorded honestly calibrates better than a tidy one.
- **The complexity red-flag and band tables have one home.** `sizing-analyst`
  restated both in different words from the guide; it now reads the guide's copy,
  which removes a drift risk rather than a duplication nuisance.
- **QA artifact formats tightened.** `qa-checklist.md` and `qa-test-review.md`
  have clearer section names and column sets (blocking versus deferred is now the
  section, not a redundant column), and `qa-planner` was updated with them.
- **Report formats clarified** across `qa-gates` (the gate-plan runner list is no
  longer a pipe-delimited string inside a JSON value; `SKIPPED` rows now require a
  reason), `codebase-scout`, `repo-audit-guides` and `repo-guides` (one audit
  report spine instead of the same one restated across six files).
- **Vocabulary made consistent.** Leftover "factory" phrasing is gone;
  `references/architecture.md` says "the package" and now everything else does too.
- `evals/plugin-eval-benchmark.json` no longer describes a runner this repo does
  not ship — it declares the check and leaves the harness to supply its own
  sandbox and workspace settings.

## [0.1.0] — initial public release

First public version.

### Added

- **Four SDLC entry points**: `sdlc-start` (human-in-the-loop), `sdlc-autonomous`
  (factory mode), `sdlc-task` (lightweight, user-classified XS/S/M work, with
  `mode: "sync"` post-completion reconciliation), and `sdlc-light` (simple,
  clear tasks — research grounds a plan directly, with a targeted clarity
  check standing in for complexity assessment and brainstorming).
- **`sdlc-pipeline`** — the 13-phase orchestrator behind the entry points:
  requirements intake → complexity scoring → brainstorming → spec → plan →
  QA checklist → TDD implementation with per-task evidence → QA test review →
  multi-lens code review → QA gates → feature verification → QA health update
  → handoff. Phase-set routing by work type (`story | bug | hotfix | spike |
  epic`), loop caps with `halt`/`escalate` semantics, and append-only
  event/decision ledgers per run.
- **`decision-router`** — the single helper behind every judgment gate. HITL
  mode always prompts the user; autonomous mode applies deterministic checks
  and fast-paths before falling back to stand-in subagents
  (story-proxy, lead-proxy), with an escalation rule and a
  full audit trail in `decisions.jsonl`. Synthesizes a canonical safe-fail
  verdict when the code-review orchestrator cannot produce one.
- **Multi-lens code review**: `code-review-orchestrator` (blind adversarial,
  edge-case tracer, and spec-acceptance lenses as parallel subagents, with the
  canonical lens definitions in its own `references/`, plus standards/security
  adjudication and triage), and `code-review` (standalone user-facing review
  outside a managed run).
- **QA suite**: `qa-foundation` (repo QA knowledge bootstrap), `qa-planner`
  (per-feature checklist / test review / health update), `qa-gates`
  (vendor-neutral lint → build → tests gate runner), `feature-verification`
  (functional verification with evidence files), `test-heal` (repairs
  test-fault failures only, never application code), `qa-case-generator` and
  `qa-e2e-generator` (ticket-driven manual/API case and E2E script
  generation).
- **Delivery skills**: `mr-creator` (adapter-driven commits/push/MR),
  `mr-watch` (autonomous MR watching: CI failures, review comments, merge
  conflicts), `release-manager` (release validation by cross-referencing
  commits against tracked tickets).
- **Knowledge skills**: `repo-guides` (project/ticket-adapter/guide
  setup, including the ticket-flow mapping), `guide-sync` (post-merge
  guide sync), `repo-audit-guides` (docs/assistant-setup audit),
  `product-owner` (story drafting with negative-acceptance-criteria rule),
  `requirements-intake`, `complexity-scoring`, `sdlc-status`, `sdlc-doctor`,
  and per-role persistent `role-memory`.
- **Hooks**: `ticket-sync` (Stop/SubagentStop, async — syncs the external
  work-item to run progress through the project's declared adapter; pure bash,
  fails safe, ships with its own stub-adapter test suite) and
  `sdlc-stage-guard` (PostToolUse(Skill), informational-only stage/next-step
  nudges for active runs, with a full transition test suite), both
  cross-platform via the `hooks/run-hook.cmd` polyglot wrapper.
- **Run-artifact JSON Schemas + zero-dependency validator**
  (`references/schemas/`, `scripts/validate-run-artifact.py`): validate after
  write, validate before gate — malformed artifacts become deterministic fix
  instructions.
- **Model-tier routing** (`economy | standard | premium`,
  `references/model-routing.md`): every dispatch resolves a tier mapped via
  host config; all shipped defaults are `"inherit"` and no concrete model ID
  ships in the plugin.
- **References**: gate catalog, lifecycle artifacts, phase routing,
  parallelism safety, mode routing, diff materialization, tokenomics (the
  agent-loop cost model), and the interactive pipeline map
  ([`sdlc.html`](sdlc.html)).

No upgrade path from a prior version — this is the first release.
