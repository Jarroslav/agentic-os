# Mode Routing

agentic-sdlc supports three user-facing run modes plus manual lifecycle skills.
Mode selection controls who resolves gates, not which artifacts exist.

## Modes

| Mode | Entry-Point Skill | Gate Resolution | Use When |
|---|---|---|---|
| HITL | `sdlc-start` | user decisions through `decision-router` | production work, ambiguous requirements, regulated changes |
| Autonomous | `sdlc-autonomous` | deterministic checks and stand-in agents, with escalation | well-scoped tasks where low-touch execution is acceptable |
| Task | `sdlc-task` | inline workflow with one code-review round | user-classified XS/S/M tasks |

## Preconditions

Full runs require these knowledge-foundation outputs:

- `.agentic/guides/project.md`
- `.agentic/guides/standards/git-workflow.md`
- `.agentic/guides/quality-gates.md`

If any are missing, `sdlc-start` and `sdlc-autonomous` halt and instruct the user
to run the `knowledge-foundation` skill.

`sdlc-task` stays lightweight and does not enforce the same precondition until
it reaches guide-dependent behavior.

All implementation-capable modes must pass a branch guard before editing files.
The guard inspects the current branch, configured base branch, `git status --porcelain`,
upstream ahead/behind/diverged state, and target branch existence. HITL modes
surface explicit dirty-state choices: stash, commit first, hard reset with
explicit confirmation, proceed with the existing dirty state after warning, or
abort.

When allowed by project policy, full runs refresh the latest target branch before
creating or reusing a feature branch: fetch the remote base, switch to the
configured base branch, fast-forward only, and halt if the base update is
unclean. Existing target branches require inspection for unique commits and
local changes before continuing, recreating, reconciling, or aborting.
Autonomous mode halts on dirty state unless policy explicitly permits auto-stash;
it must not hard reset or proceed dirty without policy.

## Manual Lifecycle Capabilities

| Capability | Routing |
|---|---|
| `knowledge-foundation` | builds `.agentic/guides/`; run in its required subagent context |
| `product-owner` | drafts/refines a story and uses the configured ticket adapter only when present |
| `mr-creator` | commits, pushes, and creates an MR/PR; manual only |
| `babysit-mr` | monitors CI, reviewer feedback, rebases, and conflicts |
| `knowledge-harvester` | dispatched after structural branch changes |
| `report-builder` | generates or refreshes static HTML reports |

Autonomous mode stops at branch-ready and recommends `mr-creator`; it does not
open, watch, or merge MR/PRs automatically.
