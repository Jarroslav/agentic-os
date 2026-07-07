# MR/PR Babysitter

Monitors an open MR or PR and autonomously handles anything blocking it from merging — CI failures, reviewer feedback, and merge conflicts — looping until the MR merges or closes.

## Use It For

- Watching a CI pipeline and retriggering flaky jobs.
- Implementing reviewer-requested code changes and replying to threads.
- Rebasing or resolving merge conflicts to unblock the MR.
- Hands-off monitoring while you focus on other work.

## How To Ask

Examples:

- "Watch MR !123."
- "Babysit this PR."
- "Monitor merge request !456 until it merges."
- "Keep an eye on this MR and fix any issues."

## What It Needs

- A GitLab CLI (`glab`) or GitHub CLI (`gh`) installed and authenticated, or a custom MR adapter configured in `.agentic/guides/project.md`.
- An open MR or PR reference (URL, `!123`, `#123`, or bare number).
