# SDLC Pipeline

The full agentic-sdlc orchestrator. Runs all phases — requirements intake, branch setup, complexity scoring, spec, plan, TDD implementation, code review, QA gates, feature verification, and handoff — in either HITL or autonomous mode.

## Use It For

- Orchestrating the complete development lifecycle for a ticket or feature.
- Running all SDLC phases with proper gate approvals and audit logging.
- Delegating implementation tasks to subagents with TDD evidence requirements.
- Resuming an interrupted pipeline run from the last completed phase.

## How To Ask

This skill is invoked automatically by `sdlc-start` and `sdlc-autonomous`. Use those entry points rather than calling `sdlc-pipeline` directly.

## What It Needs

- `.agentic/guides/` files from `knowledge-foundation` (project.md, git-workflow.md, quality-gates.md).
- superpowers plugin >= 5.0.7.
- A feature branch in the current checkout (never a git worktree).
