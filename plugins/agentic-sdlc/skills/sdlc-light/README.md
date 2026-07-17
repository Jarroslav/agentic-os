# SDLC Light (Lightest)

The lightest entry point into `agentic-sdlc`. Skips complexity assessment and brainstorming entirely — research grounds a direct plan, no `spec.md` is written, but the QA checklist / test review / health-update touchpoints and the code-review gate still run.

## Use It For

- A simple, clear task where you already know what to build and don't need a spec — just research-grounded planning.
- Skipping the sizing-analyst round-trip and brainstorming ceremony that `sdlc-task` still runs.
- Straightforward one-file changes, small validators, or focused fixes with an obvious implementation path.

## How To Ask

Examples:

- "sdlc-light: add a loading spinner to the header."
- "Quick task, no spec needed — use sdlc-light for this."
- "Light SDLC for a straightforward fix."
- "Use sdlc-light with mode: sync to reconcile the plan after maintenance changes."

## What It Needs

- superpowers plugin >= 5.0.7.
- A feature branch (the skill will help create one if you are on the base branch).
- `.agentic/guides/testing/qa-strategy.md` (from `qa-foundation`) to enable the QA checklist / test review / health-update stages — the flow proceeds without it, just skipping those three stages.
