# Changelog

Notable changes to the `agentic-sdlc` plugin, as distributed here. Format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this plugin
uses Semantic Versioning and its own release tag (`agentic-sdlc-v<X.Y.Z>`).

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
