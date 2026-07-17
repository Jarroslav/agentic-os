# agentic-qe

> **A tool-agnostic library of AI blueprints for Quality Engineering, plus the skills to act on them.**

A blueprint describes **WHAT** an AI agent should do for a QE task across the
software testing lifecycle (STLC); the per-platform guides describe **HOW**
to implement it (Claude Code, Cursor, GitHub Copilot). The `qe-blueprints`
skill turns a chosen blueprint into a ready-to-fill agent framework via a short
conversational interview; the `eval-harness` skill gives a repo of skills/agents
a working evaluation harness.

Every blueprint is written in the agentic-os design language: roles carry an
explicit **blast-radius** tag (R0 read-only → R3 external side-effects), any
R2/R3 step sits behind a **human review gate**, model choice is expressed as
**tiers** (economy / standard / premium), and grounding rules forbid inventing
facts absent from the source inputs.

This plugin is part of the [`agentic-os`](../../README.md) marketplace and
installs alongside `agentic-os` (governance) and `agentic-sdlc` (pipeline).

---

## Skills

| Skill | What it does |
|---|---|
| **`qe-blueprints`** | Interviews you, matches your goal to a QE blueprint, and scaffolds a ready-to-fill agent framework (context file, agent stubs, connector stubs) for Claude Code, Cursor, or GitHub Copilot. |
| **`eval-harness`** | Scaffolds a two-layer evaluation framework — deterministic contract checks plus LLM-judge behavioral cases — for a repository of skills and agents, in TypeScript or Python. |

## Blueprint catalog

28 blueprints organized by STLC stage under `qe-blueprints/references/catalog/`:

- **`analyze/`** — requirements testability, product risk, risk-based test selection, change-impact regression scoping, threat modeling, project context for QE, QA knowledge base.
- **`design/`** — test cases from acceptance criteria, BDD scenarios, negative & boundary coverage, test data.
- **`build/`** — automated test scripts, API/DB schema validation, AI static code analysis.
- **`execute/`** — execution & reporting, flaky-test debugging, coverage analysis, test-suite audit.
- **`operate/`** — APM analysis, DB performance, JVM tuning, load models from production logs, performance results, PR performance review.
- **`report/`** — high-signal bug reports, defect triage, security-findings triage, release summaries with impact analysis.

Supporting references: `method/` (untrusted-content defense, agent topologies,
context economy, tool access by blast radius, design checklists), `platforms/`
(per-tool implementation guides, connector catalog, unattended automation,
model tiers), and `templates/` (scaffold building blocks).

## How to use

Once the plugin is installed, ask naturally — the skills trigger themselves:

- *"Scaffold a framework for the bug-reporting blueprint for Claude Code."* → `qe-blueprints`
- *"What blueprint fits generating test cases from Jira requirements?"* → `qe-blueprints`
- *"Set up evals for my skills in TypeScript."* → `eval-harness`

The scaffolder produces a starting structure you complete by wiring connectors,
tuning prompts, and testing — a head start, not a finished agent.
