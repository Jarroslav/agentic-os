---
name: sdlc-start
description: Starts a human-in-the-loop agentic-sdlc run from a task description, an external work-item reference, or a greenfield idea. Triggers include "start sdlc", "implement this with sdlc", "begin SDLC workflow", or a request for the legacy sdlc:start command on a skills-based host.
version: 0.1.0
license: Apache-2.0
discoverable: false
authors:
  - agentic-os
---

# sdlc-start

Skill entry point for the human-in-the-loop agentic-sdlc flow, standing in for the old `sdlc:start` command on hosts such as Codex that lack command support.

## Entrypoint Purity Contract

`sdlc-start` only launches the flow — it MUST NOT create, modify, or repair repository files, run directories, run ledgers, or phase artifacts.

This skill must never:

- Create `docs/superpowers/runs/<run-id>/` or any task/run directory.
- Write `meta.json`, `requirements.md`, `complexity.json`, `design.md`, `plan.md`, `events.jsonl`, `decisions.jsonl`, `work-item.md`, or work-item ledgers.
- Run phase logic inline — that covers requirements intake, complexity scoring, brainstorming, planning, branch guards, implementation, QA, or status repair.
- Emulate `sdlc-pipeline` when direct skill invocation isn't available.

If the host can't invoke `sdlc-pipeline`, stop and report that SDLC startup is blocked rather than approximating the pipeline by hand. Artifact ownership only begins once `sdlc-pipeline` Phase 0 takes over.

## Inputs

- `raw_input` — task description, external work-item reference, story path, or greenfield idea
- `mode_flag` — optional `--greenfield`
- `escalate_on` — optional risk flags; default `["security", "breaking-change"]`

## Usage Examples

```text
Use the sdlc-start skill for "add SAML SSO provider with admin onboarding flow"
Use the sdlc-start skill for PROJ-12345
Use the sdlc-start skill with --greenfield "tiny note-taking CLI in Python"
```

## Steps

1. Treat the user's task text as `raw_input`.
2. When the user includes `--greenfield`, set `mode_flag = "--greenfield"` and treat whatever text remains as `raw_input`.
3. Invoke the `sdlc-pipeline` skill with:

   ```json
   {
     "mode": "hitl",
     "raw_input": "<as captured>",
     "mode_flag": "<--greenfield or none>",
     "escalate_on": ["security", "breaking-change"]
   }
   ```

4. From there, the pipeline takes over starting at Phase 0. Every judgment gate goes through `decision-router` in HITL mode and prompts the user for approval.
5. Once delegated, this skill performs no further SDLC phase work — any artifact creation or mutation from this point belongs to `sdlc-pipeline` or a downstream phase skill.

## Preconditions

Full SDLC runs need repo-guides output already in place. If any required `.agentic/guides/` files are missing, `sdlc-pipeline` halts and points the user to the `repo-guides` skill.

Before reaching any implementation-capable phase, the delegated `sdlc-pipeline` run must clear the branch guard: current branch, configured base branch, `git status --porcelain`, upstream state, target branch existence, dirty-state resolution, and latest-base handling.

## Notes

- Checking `superpowers` itself isn't this skill's job — `sdlc-pipeline` Phase 0 handles that.
- There's no core workflow logic living here; it only normalizes user intent and hands off to `sdlc-pipeline`.
- A compliant `sdlc-start` response writes no files of its own — it either passes normalized inputs to `sdlc-pipeline` or reports that delegation is blocked.
