# repo-audit-guides

Read-only survey of a repository's documentation, layout, and coding-agent setup. Grades whether the repo is ready for knowledge planting and hands the sibling `repo-guides` skill a structured evidence report. It writes nothing.

## Use It For

Surveying three surfaces before any knowledge gets planted:

| Dimension | What it inspects |
| --- | --- |
| Documentation | READMEs, guides, and doc coverage/quality |
| Repository structure | Directory layout and project shape |
| Assistant configuration | Agent instruction files and setup assets |

- Grading assistant-setup quality across four asset classes: skills, subagents, hooks, and assistant entrypoints.
- Comparing coexisting instruction files — `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, and Copilot instructions — and flagging conflicts between them.
- Answering one question: is this repo ready for `repo-guides` to plant knowledge?

> The report tags each finding so `repo-guides` can later decide `preserve` / `incorporate` / `replace` / `skip`. This skill supplies the evidence; it never makes the disposition call.

## How To Ask

Trigger in chat with any survey-shaped intent — survey, audit, inspect, assess, review:

- "Audit the docs in this repo."
- "Inspect the coding-agent setup here."
- "Check whether this repo is ready for repo-guides."
- "Review the assistant instructions and flag any conflicts."

## What It Needs

- Read access to the target repository. Nothing else.

> Blast radius R0: strictly read-only, zero filesystem writes. All remediation — editing, planting, replacing — belongs to `repo-guides`, never here.
