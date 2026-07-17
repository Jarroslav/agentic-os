# agentic-sdlc architecture: skills, agents, hooks, and how a run flows

> This is the structural contract for the package. Every skill, agent, and hook that ships here
> agrees on the primitive names, gate ids, artifact filenames, and paths defined below before it
> wires any behavior. Treat the ids and paths in the final section as load-bearing: they are the
> interface between components, not prose.

## What this reference pins down

Three things, and only these:

- **A closed set of primitive types.** Every moving part is exactly one of six kinds, and its kind
  determines what it is allowed to do.
- **Where the boundary sits.** One package holds all lifecycle behavior; the host project's own
  knowledge lives outside the package.
- **What is real versus planned.** Shipped capabilities are named; roadmap items are called out so
  contributors don't wire against them.

If a fact you need isn't here, it isn't a contract — decide it locally and don't invent a shared id.

## One package, nothing beside it

`plugins/agentic-sdlc` is the entire boundary. There is no companion factory package, and nothing in
here imports or depends on one. Consolidated SDLC behavior — intake, planning, implementation,
review, QA, verification, delivery — lives inside this single package.

Host-project knowledge does **not** live in the package. It is generated into and read from
`.agentic/guides/` in the target repository. That directory is where adapters, standards, and
project facts sit, so integrations stay data-driven rather than compiled in. The package ships
behavior; the repo supplies its own context.

## The six primitive types

Pick a primitive's type by its responsibility, then let the type cap its reach. The blast-radius tag
(R0 read-only → R3 external side-effects) is the ceiling for that kind.

| Type | Responsibility | Typical blast radius |
|------|----------------|---------------------|
| Entry-point skill | Parse user intent, then either invoke an orchestrator or inspect runtime state. Stays thin — no durable workflow of its own. | R0–R1 |
| Orchestrator / support skill | Own a durable, multi-phase workflow: write artifacts, drive gates, manage handoff. | R2 |
| Agent | Run in a separate context and return one bounded review or analysis result. | R0 |
| Gate | A judgment checkpoint, resolved by deterministic checks, user approval, or a stand-in agent. | — |
| Artifact | A file one phase writes and a later phase reads. | R1–R2 |
| Tool | A concrete IO or external action. | up to R3 |

> Routing rule of thumb: intent-parsing or state-inspection → entry-point skill; durable multi-phase
> work → orchestrator; a bounded second-opinion in its own context → agent. When two of these seem to
> fit, split the piece so each half is one clean type.

## The named inventory

### Entry-point skills

Thin front doors. They read what the user wants and dispatch; they hold no phase state themselves.

| Skill | Role |
|-------|------|
| `sdlc-start` | Interactive, human-in-the-loop full run. Delegates to `sdlc-pipeline`. |
| `sdlc-autonomous` | Hands-off full run. Delegates to `sdlc-pipeline`. |
| `sdlc-task` | Lightweight inline path for small, user-classified tasks — runs directly, no full orchestrator. |
| `sdlc-light` | Lightweight entry alongside `sdlc-task` for small work that bypasses the heavy pipeline. |
| `sdlc-status` | Inspect or resume runtime state of a run. |
| `sdlc-doctor` | Check the environment and setup for the package. |

### Orchestrator and support skills

Durable workflow lives here — these are the pieces that write artifacts and move gates.

| Skill | Role |
|-------|------|
| `sdlc-pipeline` | The canonical full-run orchestrator. Both `sdlc-start` and `sdlc-autonomous` delegate to it. |
| `decision-router` | Resolves every judgment gate; records each verdict to the audit ledgers. |
| `qa-gates` | Runs the host project's quality gates in sequence and returns a structured report. |
| `mr-creator` | Commits with ticket references, pushes, and opens the MR/PR. Adapter-driven. |
| `mr-watch` | Monitors an open MR/PR and handles what blocks the merge. |

### Agents

Each runs in its own context and returns a bounded, structured result — never free-form narration.

| Agent | Returns |
|-------|---------|
| `sizing-analyst` | A normalized routing score for how heavy the run should be. |
| `codebase-scout` | Scoped technical analysis of the change or codebase. |
| `lead-proxy` | A code-review verdict used to resolve `code-review.final`. |
| `story-proxy` | An approval stand-in for requirement/plan sign-off in autonomous mode. |
| `guide-sync` | Updated host-project guides after structural branch changes. |

### Gates

| Gate id | Fires when |
|---------|-----------|
| `plan.approved` | A plan is ready and needs sign-off before implementation. |
| `code-review.final` | Implementation is complete and needs a final review verdict. |
| `feature.verification` | A user-visible change needs functional confirmation. |

### Artifacts

`requirements.md`, `plan.md`, and `qa-report.md` are the phase-to-phase handoff files. Run scratch
and evidence land under `.agentic/` and `docs/superpowers/`; every gate verdict is appended to the
`decisions.jsonl` and `events.jsonl` ledgers.

### Tools

`git`, `glab`, `gh`, the ticket adapter, and browser verification. The MR/PR platform and the ticket
backend are never hardcoded — their adapters resolve from `.agentic/guides/`.

### Shared reference sets

`references/qa-authoring/` is the shared reference for QA authoring; this file
(`references/architecture.md`) is the shared reference for structure and vocabulary. `sdlc.html` is a
shipped static picture of the pipeline that `sdlc-pipeline` runs.

## Two roads in, one engine

There is exactly one full-run orchestrator, reached two ways:

- `sdlc-start` → interactive, prompts at each gate → `sdlc-pipeline`.
- `sdlc-autonomous` → unattended, resolves gates without prompting → `sdlc-pipeline`.

Small work skips the engine entirely. `sdlc-task` and `sdlc-light` carry the lightweight inline path
themselves: no complexity scoring, no per-task subagents, no evidence files — brainstorm-lite through
QA on the current branch. `sdlc-status` and `sdlc-doctor` touch no phase workflow; they read state
and report.

> The only behavioral difference between interactive and autonomous is *how gates resolve*. Same
> phases, same artifacts, same engine — the `decision-router` swaps human prompts for deterministic
> checks and stand-in agents.

## How a heavy run flows

1. **Intake.** The entry-point skill parses intent and hands off to `sdlc-pipeline`. The engine loads
   role memory once at the start so prior context carries in.
2. **Requirements.** Free-form text, a ticket reference (resolved through the adapter in
   `.agentic/guides/`), or a greenfield idea is normalized into `requirements.md`.
3. **Routing.** `sizing-analyst` produces a score. Light work goes straight to
   `superpowers:writing-plans`; heavier work runs `superpowers:brainstorming` first. The plan lands
   in `plan.md`.
4. **`plan.approved`.** The `decision-router` resolves the gate — user in interactive mode, a
   deterministic check or `story-proxy` in autonomous mode.
5. **Implementation.** Work proceeds test-first via `superpowers:test-driven-development`, fanning
   out through `superpowers:subagent-driven-development` where tasks are independent. Evidence is
   captured per task.
6. **`code-review.final`.** Model-heavy review is deferred until the implementation is fully done,
   then `lead-proxy` returns a verdict that resolves the gate.
7. **QA.** `qa-gates` runs the host runner's lint → build → tests in sequence and writes
   `qa-report.md`.
8. **`feature.verification`.** For user-visible surfaces, functional verification (including browser
   verification) confirms the change before delivery.
9. **Delivery (on request).** `mr-creator` commits, pushes, and opens the MR/PR; `mr-watch` then
   watches it. Autonomous mode never opens an MR/PR on its own.
10. **Harvest.** After structural branch changes, `guide-sync` is dispatched to refresh the
    guides under `.agentic/guides/`.

## Judgment gates and how they clear

A gate is resolved by exactly one of three means, and the mode picks which is allowed:

- **Deterministic check** — a cheap, repeatable test the router can run itself.
- **User approval** — a human answers the gate directly.
- **Stand-in agent** — a bounded agent verdict substitutes for the human when unattended.

Every resolution, with its prior context, is appended to `decisions.jsonl` and `events.jsonl`. Model
work is sized to the decision: economy for routine checks, standard for normal review, premium
reserved for the hard calls. Any R3 action — pushing, opening an MR/PR, other external side-effects —
stays behind a gate; it is never a silent step of a phase.

## Capabilities that stand on their own

These are not sub-phases of the orchestrator. They are directly invokable and split cleanly by
responsibility:

| Capability | Owns |
|------------|------|
| `mr-creator` | commit, push, MR/PR creation |
| `mr-watch` | monitoring CI, reviewer feedback, rebases, and conflicts on an open MR/PR |
| `guide-sync` | updating the guides after structural branch changes |
| `repo-guides` | generating the initial host-project guides into `.agentic/guides/` |
| `repo-audit-guides` | auditing repo docs, structure, and assistant setup before guides are planted |
| `role-memory` | per-role durable memory the pipeline loads once at the start of a run |

`repo-guides` writes `.agentic/guides/`; `guide-sync` keeps that same directory current.
Generation happens once; harvesting is incremental and event-triggered.

## Hooks and host wiring

Hooks are host-level configuration, not a pipeline primitive. They fire deterministically on
lifecycle events, carry no judgment, and never resolve a gate. Their job is to surface run notices
and enforce mechanical guardrails around the workflow — staying at R0–R1. Keep decision logic in
skills, agents, and the `decision-router`; keep hooks dumb and predictable.

## Shipped versus roadmap

- **No per-run HTML report.** A `report-builder` skill is a V2 roadmap item only. `sdlc.html` is a
  static, hand-shipped pipeline reference, not a generated per-run artifact.
- **No separate factory package.** Nothing here creates or depends on a second package.
- **No auto-MR in autonomous mode.** Unattended runs do their work but stop short of opening an
  MR/PR unless explicitly asked.

## Contract index (verbatim)

Preserve these exactly; they are the wiring interface.

```
Package boundary        plugins/agentic-sdlc
Host knowledge          .agentic/guides/
Run artifacts / ledgers .agentic/  docs/superpowers/  decisions.jsonl  events.jsonl

Entry-point skills      sdlc-start  sdlc-autonomous  sdlc-task  sdlc-light  sdlc-status  sdlc-doctor
Orchestrator / support  sdlc-pipeline  decision-router  qa-gates  mr-creator  mr-watch
Agents                  sizing-analyst  codebase-scout  lead-proxy
                        story-proxy  guide-sync
Knowledge skills        repo-guides (generates guides)  repo-audit-guides (audits)  role-memory
Gate ids                plan.approved  code-review.final  feature.verification
Artifacts               requirements.md  plan.md  qa-report.md
Tools                   git  glab  gh  ticket adapter  browser verification
Reference sets          references/qa-authoring/
Static asset            sdlc.html
Superpowers coupling    superpowers:brainstorming  superpowers:writing-plans
                        superpowers:test-driven-development  superpowers:subagent-driven-development
Blast-radius tags       R0 read-only  R1 run-artifact writes  R2 repo file writes
                        R3 external side-effects (always behind a gate)
Model tiers             economy  standard  premium
```
