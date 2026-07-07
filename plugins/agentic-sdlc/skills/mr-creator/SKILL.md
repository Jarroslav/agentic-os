---
name: mr-creator
description: >-
  Handles committing with a ticket reference, pushing, and opening the MR or PR.
  Commit and branch conventions come from `.agentic/guides/standards/git-workflow.md`;
  the MR/PR adapter (CLI, MCP server, or custom command) comes from
  `.agentic/guides/project.md` — nothing source-control-specific is hardcoded.
  Triggers on "commit changes", "push changes", "create MR", "make merge request",
  and similar review-workflow requests, and enforces the ticket format on every commit.
authors:
  - agentic-os
---

# Merge Request / Pull Request Workflow

## Invocation Rule

`sdlc-autonomous` never triggers this skill on its own. It only fires when the user
explicitly asks for a commit, a push, or an MR/PR.

## Instructions

### 0. Load Conventions and Adapter

Read `.agentic/guides/standards/git-workflow.md`.

If the file is missing, stop and output:
```
[GUIDE MISSING] `.agentic/guides/standards/git-workflow.md` not found.
Run the `knowledge-foundation` skill to generate project guides before using `mr-creator`.
```

Pull three things out of that file:
- **Commit message pattern** — the format string (e.g. `PREFIX-NNN: Description`)
- **Branch naming pattern** — the format string (e.g. `PREFIX-NNN_description`)
- **MR title format** — same as commit message pattern

**Read `.agentic/guides/project.md`** (if it exists) and look for the `## MR Adapter` section:
- `Status` — `configured` or `not configured`
- `Adapter` — the CLI tool, MCP server, or command to use
- `Instructions` — any extra context for using the adapter

When `project.md` is absent or its status reads `not configured`, fall back to the
no-adapter sequence described in `references/mr-adapters.md` — infer the platform from the
remote's hostname, probe for installed CLIs, and only ask the user if neither works. Flag
this assumption to the user before moving on.

Load `references/mr-adapters.md` for the adapter contract and sample configurations.

### 1. Check Current State

Start every run by checking the git status:

```bash
git branch --show-current
git status --short
```

Then use the resolved adapter to see whether the current branch already has an open MR or
PR. Follow the adapter's **check** operation exactly as declared — don't improvise around it.

### 2. Validate Ticket Reference (Required for Commits)

**Before any commit**, confirm a ticket reference is present in context:

- Scan conversation history for the ticket pattern loaded from git-workflow.md.
- Check whether the user already supplied a ticket number.
- **If none turns up**: Ask user: "What is the ticket number? Format: `[TICKET]-NNN`" (use actual pattern from guide).

**A commit must never proceed without a ticket reference.**

### 3. Handle Based on User Request

**"commit changes"** → Commit only (requires ticket):
```bash
git add .
git commit -m "[TICKET]-NNN: Action and message"  # use pattern from git-workflow.md
```

**"push changes"** → Push only:
```bash
git push --set-upstream origin $(git branch --show-current)
```

**"create MR"** → Full workflow below.

### 4. Create MR or PR Workflow

#### If on `main` branch:
1. Create feature branch first: `git checkout -b <type>/<description>`
2. Then proceed with commit/push/MR

#### If MR or PR already exists:
```bash
git push --set-upstream origin $(git branch --show-current)
# Inform: "Changes pushed to existing MR or PR: <url>"
```

#### If no MR or PR exists:

1. Push changes:
   ```bash
   git push --set-upstream origin $(git branch --show-current)
   ```

2. Call the resolved adapter's **create** operation to open the MR or PR. Assemble the title
   and body from the patterns below, then invoke the adapter exactly as declared (substituting
   `{{TITLE}}` and `{{BODY}}` placeholders wherever the adapter instructions reference them).

   **Title**: `[TICKET]-NNN: Brief description` (from git-workflow.md pattern)

   **Body**: use the `**Body Template**` from the `## MR Adapter` section of `project.md` if
   present. If not configured, fall back to this built-in template:
   ```
   ## Summary
   [2-4 sentence overview]

   ## Changes
   - [Key highlights only]

   ## Impact
   [Optional: before/after for user-facing changes]

   ## Checklist
   - [ ] Self-reviewed
   - [ ] Manual testing performed
   - [ ] Documentation updated (if needed)
   - [ ] No breaking changes (or documented)
   ```

Once the MR or PR exists, output its URL and suggest `babysit-mr`:

```
MR or PR created: <URL>

Want me to watch it with `babysit-mr`? It will monitor CI failures, reviewer comments, and merge
conflicts until the MR or PR merges. Ask to invoke `babysit-mr` with the URL to start monitoring.
```

Whether to invoke `babysit-mr` is the user's call — never trigger it on your own.

## Commit Format

**Required Pattern**: loaded from `.agentic/guides/standards/git-workflow.md` (e.g. `[TICKET]-NNN: Description`)

**Examples** (using pattern from guide):
```bash
git commit -m "[TICKET]-123: Add new documentation"
git commit -m "[TICKET]-456: Fix authentication bug"
git commit -m "[TICKET]-789: Refactor user service"
```

**Invalid** (will reject):
```bash
git commit -m "Add new feature"   # Missing ticket
git commit -m "feat: add feature" # Wrong format
git commit -m "[TICKET]-123 add feature"  # Missing colon
```

## Branch Format

**Pattern**: loaded from `.agentic/guides/standards/git-workflow.md` (e.g. `[TICKET]-NNN_description`)

**Examples**:
- `feat/add-user-profile`
- `fix/auth-timeout`
- `docs/api-guide`
- `[TICKET]-123_user-settings` (use pattern from guide)

## MR or PR Title Format

**Pattern**: loaded from `.agentic/guides/standards/git-workflow.md` — same as commit message format.

Always start with the ticket reference.

## Troubleshooting

### Error: Adapter not configured
The skill will attempt to infer the adapter from the git remote and probe installed CLIs.
If auto-detection also fails, answer the prompt with your tool name. To make the config
permanent, add `## MR Adapter` to `.agentic/guides/project.md` (see `references/mr-adapters.md`).

### Error: Not authenticated with the VCS tool
Check the adapter's documentation for its authentication command (e.g. `glab auth login`,
`gh auth login`, `az login`).

### Error: No ticket reference in context
**Action**: Ask user: "What is the ticket number? Format: `[TICKET]-NNN`" (use actual pattern from git-workflow.md)
- Wait for user response
- Validate format matches the pattern from git-workflow.md
- Then proceed with commit

### Error: Already on main branch
**Solution**: Create feature branch first:
```bash
git checkout -b <type>/<short-description>
```

### Error: No changes to commit
**Solution**: Check `git status` — nothing to commit or changes already staged.

### MR or PR already exists
**Action**: Just push updates to existing MR or PR, don't create a new one.

## Examples

### Example 1: User provides ticket upfront
**User**: "commit these auth changes for [TICKET]-456"
```bash
git add .
git commit -m "[TICKET]-456: Fix OAuth2 token refresh"
```

### Example 2: No ticket in context
**User**: "commit the changes"
**Claude**: "What is the ticket number? Format: `[TICKET]-NNN`"
**User**: "[TICKET]-789"
```bash
git add .
git commit -m "[TICKET]-789: Update user profile API"
```

### Example 3: Full MR or PR creation
**User**: "push and create MR for [TICKET]-321"
1. Check for existing MR or PR via adapter check operation
2. Commit with ticket: `[TICKET]-321: Add payment gateway`
3. Push changes
4. Create MR or PR via adapter create operation with title `[TICKET]-321: Add payment gateway`

### Example 4: Push to existing MR or PR
**User**: "push my changes"
1. Check MR or PR status via adapter
2. If exists: push to existing
3. If not: push only (no MR or PR creation unless requested)

## Write Run Journal

Read `.agentic/runs/<branch>.json` where `<branch>` is the current branch.
Create the file if it does not exist.

Append or update the entry:

```json
{
  "step": "06",
  "agent_skill": "mr-creator",
  "primitive": "skill",
  "started_at": "<ISO8601 start time>",
  "completed_at": "<ISO8601 now>",
  "status": "completed",
  "outcome": "Committed <N> files with message '<commit-message>'. Pushed to origin. MR or PR <ID> created at <URL>.",
  "artifacts": ["<URL>"],
  "next_step": "babysit-mr"
}
```

Write the file before presenting the handoff prompt.

## Handoff

```
---
✅ mr-creator complete.

**Outcome**: MR or PR <ID> created at <URL>.

**Recommended next step**: `babysit-mr` — monitor CI and reviewer feedback until merge (optional)

How would you like to proceed?
- **yes / proceed** → I'll invoke `babysit-mr` now
- **no / skip** → stop here, I'll wait for your instruction
- **other** → tell me what to do instead
```
