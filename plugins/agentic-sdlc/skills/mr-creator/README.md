# mr-creator

Finalize a change into a review request: commit staged work with a ticket-formatted message, push the branch to origin, and open a merge/pull request through a project-configured, adapter-driven VCS layer. No source-control platform is hardcoded.

## Use It For

- Committing staged changes with a ticket reference baked into the message.
- Pushing the current branch to origin.
- Opening a review request on the platform your project's adapter selects:

  | Adapter CLI | Platform | Request type |
  |-------------|----------|--------------|
  | `glab`      | GitLab   | merge request (MR) |
  | `gh`        | GitHub   | pull request (PR) |
  | custom (from project guide) | any | adapter-defined |

- Handing off to `mr-watch` for automated post-request monitoring once the MR/PR is open.

> Conventions are not embedded here. Commit format and branch naming come from the standards file; platform choice comes from whichever adapter is installed and authenticated. This skill neither defines conventions nor monitors the request itself — both are delegated.

## How To Ask

Trigger with any of:

- "commit changes"
- "push changes"
- "create MR" / "make a merge request"

Three stages run in order: commit (ticket-formatted) → push branch to origin → create review request.

If no ticket reference is present in context, you'll be asked for one before anything is committed. Use the format:

```
PROJ-123: description
```

## What It Needs

| Requirement | Source / value |
|-------------|----------------|
| Ticket reference | Provided in context, or prompted for. Format `PROJ-123: description`. Mandatory. |
| Commit & branch conventions | `.agentic/guides/standards/git-workflow.md` — enforced before the request is created. |
| Adapter config (custom platforms) | `.agentic/guides/project.md` |
| Platform CLI | `glab` (GitLab) or `gh` (GitHub) — installed and authenticated; else a custom adapter from the project guide. |
| Downstream monitor | `mr-watch` skill (optional handoff after the MR/PR opens). |

Platform resolution: `glab` present → GitLab MR; `gh` present → GitHub PR; otherwise the custom adapter defined in the project guide.
