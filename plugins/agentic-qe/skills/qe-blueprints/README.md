# qe-blueprints

Pick one of 28 QE blueprints (organized by STLC stage) and scaffold it into a ready-to-fill agent framework on disk — no manual folder creation, no template copying.

## Use It For

- Standing up a starter agent framework from a blueprint: the skill interviews you, matches your goal against the 28-entry catalog, confirms your toolchain, then generates a `.claude/` tree with context files, a delegation-only `orchestrator.md`, leaf-subagent stubs, and per-subagent connector stubs.
- Any blueprint domain in the catalog — for example test-case generation (e.g. from Jira acceptance criteria), bug reporting, flaky-test debugging, or static code analysis.
- Either automation pattern:

| Pattern | You get |
| --- | --- |
| Human-invoked orchestrator | An orchestrator you trigger by hand |
| Event-driven workflow | Trigger stubs for Jira, Azure DevOps, CI/CD, or Teams/Outlook |

- Any of three host tools: Claude Code (default), Cursor, or GitHub Copilot. One blueprint scaffolds for any of them; the output lands in the host tool's agent-configuration layout.

> Blast radius: R2. The scaffold writes repo files only — it never commits, pushes, or touches anything outside the tree it generates.

Not a finished agent. Connector credentials, prompt tuning, and integration testing are yours to do afterward.

## How To Ask

Phrasing is loose — name a blueprint or just state the goal:

- "Scaffold the flaky-test-debugging blueprint."
- "I want an agent that turns Jira acceptance criteria into test cases."
- "Set up bug-reporting automation for Cursor."
- "Get me started with a QE agent."

What happens next, in order: intent matching → tool and project-state check → scope and automation-pattern choice → at most 5 context questions (issue tracker, test-management system, test framework, credentials) → scaffold preview → generation.

Rules the skill follows:

- No catalog match → it offers a generic single-agent scaffold; you must accept the fallback.
- Unrecognized tool name → defaults to Claude Code.
- "I don't know" is always a valid answer — the gap becomes an explicit placeholder marker you replace before first run, never a blocker.
- Existing `.claude/` files are never silently overwritten: conflicts are listed first and overwrite requires your confirmation.

## What It Needs

| Input | Required? | Notes |
| --- | --- | --- |
| Goal statement | Yes | Fuzzy-matched against the 28-blueprint catalog |
| Host tool | No | Claude Code / Cursor / GitHub Copilot; unknown → Claude Code |
| Automation pattern | Yes | Human-invoked vs event-driven; decides which trigger integrations get stubbed |
| Context answers | No | Max 5 questions; unanswered items become placeholders |
| Overwrite consent | Only on conflict | Asked per existing `.claude/` tree |

> The interview is capped at five questions by design: missing facts become grounded placeholders in the scaffold instead of invented values or a stalled setup.

The skill relies on the sibling blueprint catalog for its structure — orchestrator pattern, connector tables, event-driven pattern, and each blueprint's prerequisites table feed the interview and the generated stubs.
