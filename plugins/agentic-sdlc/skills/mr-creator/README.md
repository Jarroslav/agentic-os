# MR/PR Creator

Commits staged changes with ticket-formatted messages, pushes the branch to origin, and creates a merge request or pull request using the project's configured VCS adapter.

## Use It For

- Committing changes with the correct ticket-reference format (e.g. `PROJ-123: description`).
- Pushing a feature branch and opening an MR on GitLab or a PR on GitHub.
- Enforcing commit message conventions from `.agentic/guides/standards/git-workflow.md`.
- Handing off to `babysit-mr` for automated post-MR monitoring.

## How To Ask

Examples:

- "Commit changes for PROJ-456."
- "Push changes."
- "Create MR."
- "Make a merge request for PROJ-321."

## What It Needs

- `.agentic/guides/standards/git-workflow.md` — for commit and branch naming conventions.
- A GitLab CLI (`glab`) or GitHub CLI (`gh`) installed and authenticated, or a custom adapter configured in `.agentic/guides/project.md`.
- A ticket reference (the skill will ask if none is found in context).
