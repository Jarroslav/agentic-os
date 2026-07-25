# release-manager

Validate a versioned release by cross-referencing git commits against work-item tracker records. Reads commit history and ticket data, then reports gaps in both directions — tickets with no commits, commits with no tickets, orphan-ticket commits, and clean matches. Reporting only: it never cuts tags, edits tickets, or rewrites commits.

## Use It For

- Auditing a release before the tag is cut, or reconciling one after the fact.
- Finding tickets that carry a fix version/milestone but landed no commits.
- Finding commits whose subjects reference no ticket ID at all.
- Catching orphan-ticket commits — commits that cite a ticket not tagged to this fix version.
- Producing a four-table validation report across one or more repos in a single pass.

> Runs over local checkouts or remote `owner/repo` slugs. With no ticket adapter configured, it still reports the commit-side gaps.

## How To Ask

Invoke it with any of these phrases:

| Phrase |
|---|
| `release manager` |
| `validate release 2.3.0` |
| `release audit for repos api and frontend` |
| `check release readiness for v1.5.0` |
| `find commits without tickets for this release` |
| `match tickets to commits for release 4.0.0` |
| `prepare a release validation report` |

The skill then runs a five-step sequence:

1. Gather release context — repos in scope, release version, ticket system.
2. Scan git tags to detect the prior release tag; propose it and wait for confirm or override.
3. Collect all non-merge commits since that tag per repo and extract ticket IDs from subjects.
4. Query the configured work-item adapter for tickets on the current fix version/milestone.
5. Cross-match and emit the report.

> Prior-tag detection is interactive. When both a minor-base tag (e.g. `2.29.0`) and a later patch tag (e.g. `2.29.1`) exist in the previous minor series, both are offered and the minor base is the default — press Enter to accept.

## What It Needs

**Config (auto-detected).** If `.agentic/guides/project.md` exists, the ticket adapter and project key are read from it and shown in the report header instead of being prompted. Sections read: `## Ticket Adapter` and `## Work Item Tracker`. A custom adapter declares a `**Lookup**` key inside `## Ticket Adapter` with the placeholders `{{FIX_VERSION}}` and `{{PROJECT_KEY}}`, substituted at runtime. See `references/work-item-adapters.md` for the full declaration format.

**Semver-shaped tags.** Tags must be semver-shaped (with or without a leading `v`) so the sort/previous-tag logic works.

**Ticket IDs in commit subjects.** A subject counts as referenced only when it matches `[A-Z][A-Z0-9_]+-\d+`. Recognized examples:

- `PROJ-123: add user login`
- `[BE-42] fix null pointer`
- `feat(auth): implement OAuth PROJ-99`

Subjects with no matching ID land in the commits-without-tickets table.

**A VCS CLI (for remote repos).** Remote issue queries require an authenticated CLI. With neither installed, operation degrades to local `git log` only.

| Adapter | Requirement | Version linkage |
|---|---|---|
| Jira (MCP) | Jira MCP server reachable | Fix Version = release string (e.g. `2.3.0`) |
| GitHub Issues | `gh` installed + authed (`gh auth login`) | Milestone = version, `2.3.0` or `v2.3.0` |
| GitLab Issues | `glab` installed + authed (`glab auth login`) | Milestone = version, `2.3.0` or `v2.3.0` |
| Custom | Lookup template in config | placeholders substituted at runtime |
| None | — | ticket side skipped; commit gaps only |
