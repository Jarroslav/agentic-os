# Roadmap

This tracks what's shipped, what's next, and what's explicitly deferred.
Item-level detail lives closer to the code (`tests/universal/README.md` for
universal-stack-support coverage, `plugins/agentic-sdlc/README.md`'s own
Roadmap section for SDLC-pipeline-specific items); this file is the
top-level index.

## Shipped

- Six curated stack profiles (Next.js/Supabase, Django, Spring, Rails, Go,
  Playwright TAF) with instant, high-confidence matching.
- Universal stack support: evidence-grounded repository discovery for any
  stack, not just the six curated ones — proven live against non-curated
  fixtures spanning both persistence paradigms (migration-managed,
  model-defined-no-migration) and both UI paradigms (component-framework,
  template-engine). See `tests/universal/README.md` for the full evidence
  trail.
- Seven role presets (developer, qa, ba-po, architect, pm-delivery, devops,
  portfolio), additive composition, strictest-HITL-wins union semantics.
- The HITL escalation ladder, decision-router, write-scope enforcement,
  blind pre-commit review, and the instruction-quality audit/scorecard gate
  — see `docs/PRINCIPLES.md` for what each does and why.
- `/agentic-doctor` (8-check install verification) and `/agentic-upgrade`
  (three-way journal/current/newrender reconciliation, including the
  agent-registry hybrid-file special case).
- Per-plugin release tags (`agentic-<plugin>-v<X.Y.Z>` per `CONTRIBUTING.md`
  § Releasing) are live — activating the clean template-only upgrade diff
  documented in `plugins/agentic-os/docs/UPGRADING.md`.
- **`agentic-qe`** — a third, standalone plugin: a tool-agnostic catalog of 28
  Quality Engineering AI blueprints organized by STLC stage, the `qe-blueprints`
  scaffolder (blueprint → ready-to-fill agent framework for Claude Code,
  Cursor, or GitHub Copilot), and the `eval-harness` eval-framework generator.
  Independent of the governance flow — no `/agentic-init` required.
- **`mcp/`** — a read-only stdio MCP server (Phase 2a) exposing the same
  agentic-os/agentic-sdlc/agentic-qe methodology to any MCP-capable host, not
  just Claude Code or Cursor: five tools (`search_methodology`,
  `get_document`, `list_presets`, `list_qe_blueprints`, `list_sdlc_phases`),
  31 skill resources plus a `file/` template and canonical URI aliases, and
  six workflow prompts. Not yet published to npm — see `mcp/README.md`.
- **`mcp/` Phase 2b** — `plan_install` and `run_doctor`, taking the tool
  surface to 7 of the documented 8-tool cap. `run_doctor` audits an
  agentic-os install in a caller-named target repo through the server's
  second filesystem reader (`mcp/src/target.ts`), gated by root containment
  rather than the bundle reader's build-time index; the server still never
  writes and never executes — the three doctor checks that need Python
  come back as commands for the host to run. See `SECURITY.md` for the
  full two-reader access-control writeup and its one accepted (and
  disclosed) risk.

## In progress / next

- **Codex packaging for the `agentic-os` and `agentic-qe` plugins.** Only
  `agentic-sdlc` ships a `.codex-plugin/` manifest today, so on Codex you get
  the SDLC pipeline but not the governance installer or the QE blueprints; the
  README scopes its claims accordingly.

- **`i18n` capability on a non-curated fixture.** Persistence, server-writes,
  and both UI paradigms all have live non-curated proof; `i18n`/
  `gen/i18n-agent` generation has not yet been run end-to-end against a
  non-curated fixture. Tracked in `tests/universal/README.md` § "What's
  proven vs. still open."
- **Zero-capability install path end-to-end.** A `pm-delivery`/`qa`-only role
  preset (`generated: []`) has deterministic coverage
  (`tests/lib/check-presets.py`) but has never been driven through a live
  `/agentic-init` run to confirm the discovery-front-end path degrades
  cleanly with nothing to generate.
- **MCP server Phase 3** — npm publish of `agentic-os-mcp`, a `.mcpb` bundle,
  a `server.json`, and an MCP Registry listing (plus the one-click install
  badges the README's install snippets are already shaped for). Phase 2b
  (`plan_install`, `run_doctor`) shipped — see Shipped above.

- **Known issue: `agentic-doctor`'s Check 5 parenthetical is incomplete.**
  `plugins/agentic-os/skills/agentic-doctor/SKILL.md`'s Check 5 lists the
  hooks `.claude/settings.json` should wire as a parenthetical — PreToolUse
  Bash/Write/Edit, PostToolUse Write/Edit, SubagentStart, Stop/SubagentStop,
  SessionStart, PreCompact — but that list omits four hooks the real
  fragment (`plugins/agentic-os/templates/hooks/settings-fragment.json.tmpl`)
  actually wires: `prompt_scan_guard.py` (the prompt-injection scanner,
  UserPromptSubmit), `lint_on_save.py`, `context_monitor.py` (both
  PostToolUse), and `session_learnings_notice.py` (Stop). Anyone implementing
  Check 5 from the parenthetical alone under-checks those four — a
  `settings.json` that dropped the prompt-injection scanner would pass. The
  MCP port of this check (`mcp/src/doctor.ts`'s `EXPECTED_WIRING`) was
  written against the fragment directly rather than the parenthetical, so it
  does not have this gap; the plugin's own `/agentic-doctor` skill still
  does. `plugins/` is out of scope for the branch that found this
  (`mcp/phase-2b`); fixing SKILL.md's Check 5 parenthetical to match the
  fragment is a small, self-contained follow-up.

## Deferred, by design

- **Paradigm fragments** for generated agent contracts (pre-written,
  paradigm-specific rule blocks the installer could append). The seam exists
  in the generator prompts, but zero fragments have been written — every
  non-curated fixture run so far has shown the paradigm-neutral exemplar
  skeleton alone is sufficient (no vocabulary transplant observed). Per
  YAGNI, this stays unbuilt until a real fixture or install surfaces a
  transplant the neutral skeleton misses. See `tests/universal/README.md` §
  "Decision: paradigm fragments not added."
- **`agentic-sdlc` v2 items** (adaptive mode switching mid-flow, `sdlc-status`
  support for `sdlc-task` runs, native PR integration, cross-run memory
  promotion) — see `plugins/agentic-sdlc/README.md` § Roadmap for the current
  list; not duplicated here to avoid the two files drifting out of sync.
