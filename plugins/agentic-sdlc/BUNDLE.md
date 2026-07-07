---
name: agentic-sdlc
description: Skill-driven SDLC pipeline for coding agents — carries a task from requirements through spec, plan, TDD, code review, QA, and a branch-ready handoff, with deterministic checks resolved before any model call. Three oversight levels (HITL, autonomous, lightweight task) on one shared toolkit.
authors:
  - agentic-os
---


## Summary

**Move fast without dropping the process discipline that keeps shipping safe.**

agentic-sdlc turns a coding agent (Claude Code, Codex CLI) into a teammate that follows a process instead of freelancing. Give it a loose requirement, a ticket, or a bare idea and it hands back a branch that's ready for review — spec, plan, a test that failed and then passed, a completed code review, and a clean QA report all included.

Coding agents on their own tend to skip the parts that make software maintainable: no spec, no explicit plan, tests as an afterthought, work that satisfies the linter but not the browser. agentic-sdlc is the reusable, tool-agnostic pipeline that fills that gap.

---

## What it does

- **Takes the work all the way from idea to branch-ready.** Requirements → spec → plan → TDD → review → QA → functional verification, in one continuous flow.
- **Three modes, one toolkit.** Pick the level of human oversight that fits the task:
  - **HITL** (`sdlc-start`) — production, brownfield, regulated work. Human approves every gate.
  - **Autonomous** (`sdlc-autonomous`) — greenfield POCs, well-scoped tickets, batch runs. Stand-in subagents resolve gates; the run only stops on low confidence or risk flags.
  - **Lightweight task** (`sdlc-task`) — XS/S/M tasks. Inline TDD, single review round, minimum ceremony.
- **Deterministic before model.** Cheap structural checks resolve gates first. Stand-in subagents (PO, tech lead, code reviewer) run only when needed — saving tokens and time.
- **TDD by structure.** Every task ships with recorded evidence: failing test → fix → passing test. No "looks fine" reviews.
- **Resumable runs.** Each phase writes deterministic artifacts. Crash, Ctrl-C, closed laptop — pick up where it left off.
- **Vendor-neutral.** Runs against npm / pnpm / yarn / cargo / poetry / uv / go. Works in any repo with a package manager.
- **No surprise merges.** All three modes stop at "branch ready". A human (or your PR tool of choice) opens the pull request.

---

## Why it's worth adopting

- **Same shape, every run.** `requirements.md`, `design.md`, `plan.md`, evidence files, a QA report — a reviewer always knows where to look.
- **Scales down as well as up.** The lightweight flow ships a one-file change in minutes; the full pipeline keeps a complete audit trail for regulated or high-risk changes.
- **One workflow, not a pile of prompts.** Reusable skills stand in for ad-hoc prompting, and the same workflow runs unchanged on Claude Code or Codex CLI.
- **UI changes get proven, not assumed.** User-visible work is checked with Playwright, Cypress, or Storybook — screenshots, console errors, and network failures captured automatically.
- **Gets smarter over time.** Memory and the knowledge-harvester skill turn recurring lessons into curated guides, so later runs benefit from earlier ones.

---

## Getting started

**Prerequisite:** install [`superpowers`](https://github.com/obra/superpowers) ≥ 5.0.7.

### Install

```text
/plugin marketplace add obra/superpowers
/plugin install superpowers
/plugin marketplace add https://github.com/Jarroslav/agentic-os.git
/plugin install agentic-sdlc@agentic-os
```

Same commands work in Claude Code and Codex CLI.

### Verify

```text
Use the sdlc-doctor skill
```

### First run

```text
# 1. Bootstrap project knowledge (once per repo)
Use the knowledge-foundation skill

# 2. Pick a mode
Use the sdlc-start skill for "add SAML SSO provider"            # HITL
Use the sdlc-autonomous skill for PROJ-12345                 # Autonomous
Use the sdlc-task skill for "add email validator to signup"     # Lightweight

# 3. When the branch is ready
Use the mr-creator skill
```

That's it. Detailed install guide and configuration options live in the [repo](https://github.com/Jarroslav/agentic-os.git).

---

## Components

### Entry-point skills

| Skill | What it does |
|-------|---------------|
| `sdlc-start` | HITL run — you approve every gate. |
| `sdlc-autonomous` | Autonomous run — stand-ins resolve gates with escalation safety nets. |
| `sdlc-task` | Lightweight inline flow for XS/S/M tasks. |
| `sdlc-status` | List, inspect, or resume in-flight runs. |
| `sdlc-doctor` | Environment check. |

### Orchestrators & sub-skills

| Skill | What it does |
|-------|---------------|
| `sdlc-pipeline` | The heavy-flow orchestrator behind `sdlc-start` and `sdlc-autonomous`. |
| `requirements-intake` | Normalizes free-form input, tickets, or greenfield ideas into a clean `requirements.md`. |
| `complexity-scoring` | Scores task complexity; routes simple tasks past the spec phase. |
| `decision-router` | Resolves every judgment gate cheapest-first: deterministic → fast-path → subagent. |
| `qa-gates` | Vendor-neutral runner detection + lint/type/test/build execution. |
| `feature-verification` | Functional proof (Playwright / Cypress / Storybook) for user-visible changes. |
| `memory` | Per-role persistent memory; lessons from past runs surface in the next one. |

### Auxiliary skills

| Skill | What it does |
|-------|---------------|
| `knowledge-foundation` | Bootstraps project guides (project, standards, quality-gates) on first use. |
| `knowledge-auditor` | Audits and refreshes those guides as the repo evolves. |
| `product-owner` | Drafts a ticket-ready story from a raw idea. |
| `mr-creator` | Opens MR/PR via your platform's adapter. |
| `babysit-mr` | Monitors open MR/PR (CI, reviewer comments) and reports status. |

### Stand-in agents (autonomous mode)

| Agent | Role |
|-------|------|
| `product-owner-stand-in` | Resolves ambiguous requirements and clarifying questions. |
| `tech-lead-reviewer` | Approves spec and plan, watches for drift, reviews verification evidence. |
| `code-reviewer` | Reviews the final diff; runs targeted re-checks after fixes. |
| `complexity-assessor` | Decides scope on boundary cases that heuristics can't call. |
| `knowledge-harvester` | After merge, promotes recurring lessons into curated guides. |

