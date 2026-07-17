# mr-watch

Hands-off monitoring of a single open merge/pull request. The skill runs a continuous poll/act loop that clears whatever blocks the request from merging — CI failures, reviewer-requested changes, merge conflicts — and keeps going until the request merges or closes.

## Use It For

- Shepherding one open MR/PR to merge while you work on something else.
- Watching CI and retriggering flaky jobs so a green pipeline sticks.
- Implementing reviewer-requested code changes and replying to the review threads.
- Rebasing and resolving merge conflicts to keep the request mergeable.
- Receiving a handoff from another skill that just opened an MR/PR and wants monitoring to continue.

> Scope is one open MR/PR at a time. The loop exits only when the request is `merged` or `closed`. It does not open or create the request — it monitors an already-open one.

## How To Ask

Trigger with any natural-language phrasing that names the intent (watch / babysit / monitor / keep an eye on) plus the target request:

- "Watch MR !123."
- "Babysit this PR."
- "Monitor merge request !456 until it merges."
- "Keep an eye on this MR and fix any issues."

A reference argument is required to identify the target. Accepted forms:

| Form | Example |
| --- | --- |
| Full URL | `https://.../merge_requests/123` |
| GitLab-style | `!123` |
| GitHub-style | `#123` |
| Bare number | `123` |

## What It Needs

- **An open MR/PR reference** in one of the forms above.
- **A source-control adapter.** The platform is not hardcoded. Adapter selection precedence:
  1. An installed and authenticated platform CLI — `glab` (GitLab) or `gh` (GitHub).
  2. Otherwise, a custom adapter declared in `.agentic/guides/project.md`.

> Prerequisites: an authenticated CLI **or** a configured custom adapter, PLUS an open MR/PR reference. Adapter and project configuration are read from `.agentic/guides/project.md`.
