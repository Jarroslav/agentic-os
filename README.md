# agentic-os

[![CI](https://github.com/Jarroslav/agentic-os/actions/workflows/ci.yml/badge.svg)](https://github.com/Jarroslav/agentic-os/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-5A2EBB)](https://github.com/Jarroslav/agentic-os)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**A portable, governed multi-agent architecture you install into any repo — new or mature — in one interview.**

`agentic-os` packages a battle-tested agentic SDLC layer as a Claude Code plugin.
One command interviews you (role, autonomy level, stack) and scaffolds a coherent
system into your project: canonical agent contracts, enforcement hooks (blind
pre-commit review, write-scope guard, instruction-quality spawn gate), a
human-in-the-loop escalation ladder, and — where it fits your stack — generated
stack-specific agents. It is **stack-universal**: six curated profiles
(Next.js, Django, Spring, Rails, Go, Playwright) are recognized instantly,
and anything else — a NestJS backend, a schemaless Mongo service, or no code
stack at all — gets real, evidence-grounded persistence and API agents via
live repo discovery instead of a degraded stub (proven live against both a
migration-managed and a schemaless non-curated backend — see
`tests/universal/README.md`). Frontend/UI generation on a non-curated stack
uses the same discovery mechanism but is earlier in its own verification
cycle. It is also role-agnostic
(developer, QA, BA/PO, architect, delivery).

This repo is a Claude Code **marketplace** hosting two plugins:

- **`agentic-os`** — the product: the `/agentic-init`, `/agentic-doctor`, and
  `/agentic-upgrade` skills plus the template library, generators, and role
  presets they scaffold from.
- **`agentic-sdlc`** — the SDLC pipeline and the **decision-router** that
  resolves every judgment gate (ask the human in HITL mode; deterministic →
  fast-path → stand-in subagent → escalate in autonomous mode) with a full
  `decisions.jsonl` audit trail.

## Prerequisites

- **Claude Code** (the CLI or IDE extension) — this is a Claude Code plugin.
- **`python3`** on your PATH — every enforcement hook is a Python script.
- **git** — the target repo must be a git repository (`/agentic-init` offers to
  `git init` if it isn't).
- Optional: **`gh`** (GitHub CLI) if you want the GitHub ticket/MR adapters.

## Install

From this marketplace:

```
/plugin marketplace add Jarroslav/agentic-os
/plugin install agentic-os@agentic-os
/plugin install agentic-sdlc@agentic-os
```

Or try it straight from a local clone, no publish needed:

```
git clone https://github.com/Jarroslav/agentic-os
# in Claude Code:
/plugin marketplace add /absolute/path/to/agentic-os
/plugin install agentic-os@agentic-os
/plugin install agentic-sdlc@agentic-os
```

**Restart the session** so the plugins load (Claude Code activates plugins at
session start). Then, in the repo you want to equip:

```
/agentic-init            # full interview
/agentic-init --defaults # accept every detected default, no questions
```

The interview has six screens, each pre-filled from stack discovery (a cheap
marker check confirmed against the repo for one of six curated stacks, or a
full inspection otherwise). It **never commits** — it scaffolds files, shows
you a settings diff before merging, and leaves the working tree for you to
review and commit. Then:

```
/agentic-doctor          # verify the install (writes .agentic/agentic-os/doctor.json)
/agentic-upgrade         # reconcile scaffolded files after a plugin update
```

## Try it in two minutes (throwaway repo)

Nothing here touches a real project — build a disposable repo and watch the
whole install cycle end-to-end:

```bash
mkdir /tmp/try-agentic && cd /tmp/try-agentic && git init
printf '{"name":"try","dependencies":{"next":"15.0.0"}}' > package.json
```

Open Claude Code in that directory (after the marketplace/plugin install
steps above and a session restart), then run:

```
/agentic-init --defaults
```

What happens, in order:

1. **Preflight** — detects this is a git repo, then runs stack discovery: a
   cheap marker check spots the `next` dependency and matches the
   `nextjs-supabase` profile, then a subagent confirms that match against the
   real repo (a non-matching repo gets a full from-scratch inspection
   instead, not a dead-end fallback).
2. **Interview** — with `--defaults`, all six screens (role preset, HITL dial,
   autonomy matrix, gates, stack confirm, ticket/MR adapter) are accepted at
   their detected defaults instead of prompted.
3. **Dependency check** — verifies every non-optional dependency
   (`agentic-sdlc`, `superpowers`) is registered; prints a pending-restart
   notice for any that aren't.
4. **Scaffold** — writes `.agentic/agents/`, `.agentic/guides/`,
   `.claude/hooks/`, `.githooks/pre-commit`; always writes `CLAUDE.md` as a
   marker-delimited block, and writes `AGENTS.md` whole on a fresh repo like
   this one (it only becomes a marker-delimited block when the file already
   exists). Nothing is committed — it's your working tree to review.
5. **Generate** — spawns per-slot subagents for the generated set (the union
   across every selected role preset): writer contracts, any applicable
   read-only gate like `migration-validator`, and stack guides — each
   independently audited against the instruction-quality rubric before
   being armed in the scorecard.

Then:

```
/agentic-doctor
```

runs all 7 checks (file manifest vs. install journal, hook compilation,
canned-event dry-runs of each installed hook, a 3-part HITL smoke test,
settings registration, git hook + dependencies, and scorecard
coverage/thresholds) and writes the result to
`.agentic/agentic-os/doctor.json`.

```bash
git status         # inspect exactly what was scaffolded; nothing was committed
```

## Role presets

Presets are **additive** — install several and their template sets union
(strictest HITL wins).

| Preset | What it installs | Default HITL / orchestration |
|---|---|---|
| **developer** | generated stack writer agents (schema/api/component), read-only gates, blind pre-commit review, staged pipeline orchestrator | gated-autonomous / pipeline |
| **qa** | dispatcher routing; test-case generation / automation / sync agents with real-ID + existing-coverage gates; failure triage + flaky protocol; adapter-driven work-item creation (tests are recommend-only) | strict / dispatcher |
| **ba-po** | story & requirements intake via agentic-sdlc, ticket adapter — no code-writing agents | gated-autonomous / dispatcher |
| **architect** | full governance scaffolding (AGENTS/PATTERNS/registry), instruction-auditor + scorecard spawn gate, generated architecture guides | gated-autonomous / pipeline |
| **pm-delivery** | ticket/MR adapters, PR pipeline gate, MR-babysitting glue, status conventions | gated-autonomous / dispatcher |

## The HITL dial

The install sets how much agents may do before a human must weigh in:

- **`strict`** — every step is user-invoked; agents recommend, they don't act
  (e.g. QA: agents author tests but never run them). Dispatcher orchestration.
- **`gated-autonomous`** — pipelines run, but judgment gates and the
  `escalate_on` risk flags (default: security, breaking-change, migration,
  spend) stop them for a human decision.
- **`autonomous`** — the agentic-sdlc decision-router resolves gates with
  deterministic checks, fast-paths, and stand-in reviewers, escalating to you
  only on low confidence, a matching risk flag, or malformed agent output.

Underneath, three mechanisms make HITL real, not advisory:

1. **Policy files** (`.agentic/guides/policy/`) — the autonomy matrix, size
   ceiling, env write boundaries, secret deny-lists, and the escalation ladder.
2. **Resolver conventions** — every agent ends its output with
   `## Summary / ## Why / ## Blocking / ## Non-blocking / ## Escalate to human`,
   parsed fail-closed by a Stop/SubagentStop hook: a non-empty `Blocking` stops
   the parent (no silent retry); a non-empty `Escalate to human` forces an
   `AskUserQuestion`.
3. **Hard gates** — exit-2 hooks: blind pre-commit review (sha256 stamp of the
   staged diff), write-scope guard, instruction-quality spawn gate, human-gated
   command blocks.

## What gets scaffolded

Into your target repo (harness-neutral canonical contracts, thin Claude
pointers):

```
.agentic/agents/            canonical agent contracts (single source of truth)
.agentic/guides/            policy/, standards/, agent-registry.md, project.md
.agentic/agentic-sdlc/      config.json (decision-router wiring)
.claude/hooks/             the enforcement hooks
.claude/agents/, commands/ thin pointers + orchestration commands
.githooks/pre-commit       the review gate's git-level twin
CLAUDE.md / AGENTS.md      a managed block (your content outside it is untouched)
docs/audits/               the instruction-quality scorecard
```

Mature repos are handled non-destructively: managed marker blocks, deep-merged
settings (shown as a diff first), skip-by-default name collisions, chained
(never replaced) git hooks.

## Using it, by role

After install, what you reach for depends on the preset(s) you chose:

- **developer** — describe a feature; the pipeline orchestrator runs the staged
  flow (generated schema/api/component agents → read-only gates → blind
  pre-commit review). Every `git commit` is blocked until the staged diff is
  reviewed. `/agentic-doctor` confirms the fleet is spawnable.
- **qa** — `/dispatch` routes each request to one owning agent (strict HITL, one
  step at a time). Generate test-case drafts from a story, automate approved
  work-item IDs (with real-ID + existing-coverage gates), triage a red test
  against the flaky protocol. Agents author tests but never run them — they hand
  you the exact command.
- **ba-po** — draft stories and requirements through the agentic-sdlc intake
  skills, wired to your ticket adapter.
- **architect** — the governance layer: `AGENTS.md`/`PATTERNS.md`/agent-registry,
  the instruction-auditor + scorecard spawn gate, generated architecture guides.
- **pm-delivery** — ticket/MR adapters, the PR pipeline gate, MR-babysitting.

Everything obeys the HITL dial you set: an agent that hits a `## Blocking` item
stops and surfaces it; an `## Escalate to human` item forces a question before
anything proceeds.

## Testing & development

The two gates that CI also runs:

```bash
bash tests/run-matrix.sh             # T1–T7 acceptance (includes the two t0 suites)
```

The matrix **executes the installer's deterministic phases** against fresh and
mature fixture repos (it is the skill-executability proof, not a mock) — see
[`tests/README.md`](tests/README.md). The live agent-generation loop (stack
writer agents produced against a real repo, then independently audited against
the instruction-quality rubric) has been validated end to end at 100% pass.

## Contributing

`main` is protected — **all changes go through a reviewed, CI-passing pull
request; no direct pushes.** See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the
branch → PR flow and [`docs/GITHUB-SETUP.md`](docs/GITHUB-SETUP.md) for exactly
how the protection is configured (and how to publish a fork with the same rules
via `scripts/setup-github.sh`).

## Docs

- Upgrade flow & version notes: [`plugins/agentic-os/docs/UPGRADING.md`](plugins/agentic-os/docs/UPGRADING.md)
- GitHub protection & publish: [`docs/GITHUB-SETUP.md`](docs/GITHUB-SETUP.md)
- Preset composition rules: [`plugins/agentic-os/presets/README.md`](plugins/agentic-os/presets/README.md)

License: Apache-2.0.
