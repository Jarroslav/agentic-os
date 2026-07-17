# SDLC Start (HITL)

Starts a human-in-the-loop agentic-sdlc run. Every judgment gate — spec approval, plan approval, code review, QA drift — prompts you for a decision before the pipeline proceeds.

`sdlc-start` is launcher-only: it normalizes the request and hands it to `sdlc-pipeline`. It must not create run directories, write `meta.json`, `requirements.md`, `plan.md`, ledgers, or run any phase logic itself. If `sdlc-pipeline` cannot be invoked, startup is blocked rather than emulated manually.

## Use It For

- Implementing a ticket with full control over spec, plan, and review checkpoints.
- Starting an SDLC run for a Jira ticket, story file, or free-form task description.
- Building a feature with guided approvals at each phase boundary.
- Greenfield project setup with interactive checkpoints.

## How To Ask

Examples:

- "Start SDLC for PROJ-123."
- "Implement this feature with SDLC."
- "Begin SDLC workflow for the login timeout fix."
- "Use sdlc-start with --greenfield 'simple REST API in Go'."

## What It Needs

- `.agentic/guides/` files from `repo-guides` (project.md, git-workflow.md, quality-gates.md).
- superpowers plugin >= 5.0.7.
- A feature branch or base branch to create one from.
