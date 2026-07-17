---
name: sdlc-autonomous
description: Start an autonomous ("factory mode") SDLC run from a task description, external work-item reference, story path, or greenfield idea, on hosts that support skills but not custom slash commands. Trigger on "run autonomously", "factory mode", "ship this without asking", or a request for the legacy `sdlc:autonomous` command. Parses free-form intent into a structured payload and hands off to sdlc-pipeline — carries no orchestration logic of its own.
version: 0.1.0
license: Apache-2.0
discoverable: false
author: agentic-os
---

# sdlc-autonomous

Skill-based entry point for autonomous-mode SDLC runs, for hosts (for example Codex) that
expose skills but not custom slash commands. Everything this skill does is intent
normalization and delegation — it holds zero workflow, QA, review, or git logic itself. All
phase execution lives in `sdlc-pipeline`; all gate resolution lives in `decision-router`.

Treat this skill as a thin adapter in front of the legacy `sdlc:autonomous` command, mirroring
whatever human-in-the-loop entry point exists alongside it in the same skill family.

## When to invoke

- The user says "run autonomously", "factory mode", or "ship this without asking".
- The user asks for the legacy `sdlc:autonomous` command on a host that has no slash-command
  support.

## What this skill does not do

- Does not implement any SDLC phase, QA check, code review, or test logic.
- Does not create branches, commits, or open an MR/PR — autonomous mode never auto-merges and
  never opens an MR/PR by itself; the delegated pipeline halts after its branch-ready phase
  and hand-off to an MR/PR tool is a separate, manual step.
- Does not resolve judgment gates directly — every gate routes through `decision-router`.
- Does not generate missing guide files, bypass the branch-guard, or auto-stash / hard-reset /
  force-push a dirty working tree absent explicit project policy allowing it.

## Inputs

| Field | Type | Default | Notes |
|---|---|---|---|
| `raw_input` | string | — | Task text, work-item reference, story path, or greenfield idea |
| `mode_flag` | string/enum | none | Only `--greenfield` is recognized |
| `escalate_on` | string[] | `["security", "breaking-change"]` | CSV or list-style input |

Recognized CLI-style flags inside `raw_input`: `--greenfield`, `--escalate-on`.

## Operating steps

1. **Parse `--greenfield`.** If the input contains `--greenfield "<text>"`, set
   `mode_flag = "--greenfield"` and capture `<text>` as `raw_input`.
2. **Parse `--escalate-on`.** If the input contains `--escalate-on <comma-list>`, split the list
   on commas into the `escalate_on` array. If absent, use the default
   `["security", "breaking-change"]`.
3. **Capture the remainder.** Whatever text is left unconsumed by the two flags becomes
   `raw_input` (verbatim, if no `--greenfield` flag was present).
4. **Delegate.** Invoke the `sdlc-pipeline` skill with `mode: "autonomous"` plus the three
   parsed fields — see payload shape below. Do not run any pipeline phase yourself.
5. **Gate resolution.** Every judgment gate inside the delegated pipeline resolves through
   `decision-router`, in this priority order: deterministic checks first, fast-path approvals
   second, a stand-in subagent invocation only as the last resort.
6. **Escalation.** The user is interrupted only when: routing confidence is low, or a detected
   in-flight risk flag intersects the run's `escalate_on` set.
7. **Precondition gate — `repo-guides`.** If required guide files under `.agentic/guides/` are
   absent, the pipeline halts immediately and the user is redirected to run the `repo-guides`
   skill first. This skill never generates guides itself.
8. **Branch-guard gate.** Must clear before any implementation-capable phase. Checks, in order:
   current branch; configured base branch; `git status --porcelain`; upstream tracking state;
   target-branch existence; dirty-state resolution; latest-base sync.
9. **Dirty-tree rule (autonomous mode).** A dirty working tree halts the run unless project
   policy explicitly allows auto-stash. Hard-reset or force-push-forward on a dirty tree is
   disallowed regardless of any other setting.
10. **Audit.** Every routed decision is appended to `<run_dir>/decisions.jsonl` for the run,
    regardless of outcome.

## Delegation payload

Field names and literal values below are exact — do not rename or restructure when calling
`sdlc-pipeline`:

```json
{
  "mode": "autonomous",
  "raw_input": "<as captured>",
  "mode_flag": "<--greenfield or none>",
  "escalate_on": ["security", "breaking-change"]
}
```

## Outputs

- A running (or halted-at-gate) `sdlc-pipeline` invocation in `mode: "autonomous"`.
- An audit trail at `<run_dir>/decisions.jsonl` covering every routed decision for the run.
- On success, a branch left at Phase 12 (branch-ready stop point) with no MR/PR opened.
  Hand the result to `mr-creator` (or an equivalent PR tool) as a separate, explicit step.
- On a precondition failure, a redirect instructing the user to run `repo-guides` before
  retrying.

## References

This skill carries no `references/` tree of its own — it has no workflow logic to document.
All reference material for phase behavior, gate checklists, and escalation rules lives in the
skills it delegates to:

- `sdlc-pipeline` — phase execution, including the Phase 12 branch-ready stop point.
- `decision-router` — gate priority order, escalation-rule evaluation, and the
  `decisions.jsonl` / `events.jsonl` audit ledger format.
- `repo-guides` — populates `.agentic/guides/`, the prerequisite this skill checks for.
- `mr-creator` — the manual follow-on step for opening an MR/PR once Phase 12 is reached.
