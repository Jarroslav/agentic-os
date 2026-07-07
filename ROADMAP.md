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
- Five role presets (developer, qa, ba-po, architect, pm-delivery), additive
  composition, strictest-HITL-wins union semantics.
- The HITL escalation ladder, decision-router, write-scope enforcement,
  blind pre-commit review, and the instruction-quality audit/scorecard gate
  — see `docs/PRINCIPLES.md` for what each does and why.
- `/agentic-doctor` (7-check install verification) and `/agentic-upgrade`
  (three-way journal/current/newrender reconciliation, including the
  agent-registry hybrid-file special case).

## In progress / next

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
- **`UPGRADING.md` version notes are behind `plugin.json`.** The plugin is at
  `0.3.0`; the documented version history stops at `0.1.0`. Needs the
  maintainer's own account of what changed in each bump, not a
  mechanically-reconstructed changelog.
- **No release tags exist yet.** `UPGRADING.md` documents an
  upgrade-diff-recovery path that depends on marketplace tags
  (`git show v<OLD>:<path>`); until a tagging policy is adopted, that
  recovery path always falls back to a plain current→new diff. See
  `docs/positioning-review.md` § 4 and § 10.

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
