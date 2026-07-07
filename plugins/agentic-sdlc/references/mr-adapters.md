# MR / PR Adapters

MR and PR operations are adapter-driven. agentic-sdlc must not hardcode any specific
source control CLI, platform API, or tool name.

## Adapter Declaration

Projects declare adapter behavior in `.agentic/guides/project.md`.

There are two forms depending on whether the adapter is a well-known CLI or a custom tool.

### Well-known CLI (shorthand form)

If the adapter is a recognized CLI (`glab`, `gh`), only the name is required. Skills resolve
the concrete commands for each operation from the **Known Adapters** section of this file.

```markdown
## MR Adapter

**Status**: configured
**Adapter**: glab | gh
```

### Custom adapter (explicit form)

If the adapter is not a well-known CLI (custom tool, MCP server, REST API, etc.), each
operation the project uses must be declared explicitly. Use `{{PLACEHOLDER}}` tokens for
values the skill will substitute at runtime.

```markdown
## MR Adapter

**Status**: configured
**Adapter**: <tool name or description>
**check**: <command to check for an open MR or PR on branch {{BRANCH}}; print URL if found>
**create**: <command to create an MR or PR with title {{TITLE}} and body {{BODY}}>
**state**: <command to get state of MR or PR {{ID}}; print open | merged | closed>
**ci-status**: <command to get CI status for {{ID}}; print running | passed | failed | none>
**discussions**: <command to list unresolved review comments on {{ID}}>
**comment**: <command to post {{BODY}} as a general comment on {{ID}}>
**diff**: <command to get the line-level diff for {{ID}}>
**inline-comment**: <command to post {{BODY}} on {{FILE}} line {{LINE}} of {{ID}}>
**target-branch**: <command to get the target branch of {{ID}}>
```

Only declare the operations your project's skills actually use. Omit the rest.

An optional `**Body Template**` field sets the default MR or PR description. Use `{{PLACEHOLDER}}`
tokens for values the skill substitutes at runtime. When omitted, `mr-creator` uses its built-in
template.

```markdown
**Body Template**: |
  ## Summary
  {{SUMMARY}}

  ## Changes
  {{CHANGES}}
```

An optional `**Comment Template**` field sets the format for inline review comments. Available
placeholders: `{{SEVERITY}}`, `{{TITLE}}`, `{{DESCRIPTION}}`, `{{IMPACT}}`, `{{FIX}}`. When
omitted, `mr-code-review` uses its built-in template.

```markdown
**Comment Template**: |
  **{{SEVERITY}}: {{TITLE}}**

  {{DESCRIPTION}}

  **Fix:** {{FIX}}
```

## Resolution Order

Skills resolve the adapter in this order:

1. Read `.agentic/guides/project.md` → `## MR Adapter` section. Use it if status is `configured`.
2. If not configured, try to infer from `git remote get-url origin` hostname.
3. If still ambiguous, ask the user.

## Skill Contract

Skills invoke each operation exactly as declared. For well-known CLIs, operations are resolved
from the **Known Adapters** section below. For custom adapters, the declared command is used
verbatim after placeholder substitution.

| Operation | What the skill needs |
|-----------|---------------------|
| **check** | Does an open MR or PR exist for the current branch? Return URL if yes. |
| **create** | Create an MR or PR with a given title and body. Return the URL. |
| **state** | Current state of MR or PR `{{ID}}` — `open`, `merged`, or `closed`. |
| **ci-status** | CI pipeline status for `{{ID}}` — `running`, `passed`, `failed`, or `none`. |
| **discussions** | Unresolved review comments on `{{ID}}`. |
| **comment** | Post a general comment on `{{ID}}`. |
| **diff** | Line-level diff for `{{ID}}`. |
| **inline-comment** | Post a comment on a specific file and line of `{{ID}}`. |
| **target-branch** | Target branch of `{{ID}}`. |

If the adapter cannot perform a required operation, the skill degrades gracefully and reports
the gap to the user.

## No-Adapter Fallback

When adapter status is `not configured`, skills must not fail immediately. Use this inference
sequence before giving up:

1. **Infer from remote URL** — run `git remote get-url origin` and inspect the hostname.
   Map known hostnames to their default CLI (e.g. `github.com` → `gh`, `gitlab.com` → `glab`).
2. **Verify the inferred CLI** — check that the inferred tool is installed and authenticated
   (e.g. `glab auth status`). If it is, proceed with it and note the assumption to the user
   (e.g. "No MR adapter configured — inferred `glab` from remote. Add `## MR Adapter` to
   `project.md` to make this explicit.").
3. **If the inferred CLI is unavailable** — ask the user which tool manages MRs and PRs
   for this project.
4. **If remote inference yields nothing** — ask the user directly.

## Known Adapters

Operation commands for well-known CLIs. Skills use these when the adapter is declared by
name only (shorthand form).

### `glab` — GitLab CLI

| Operation | Command |
|-----------|---------|
| **check** | `glab mr list --source-branch={{BRANCH}}` |
| **create** | `glab mr create --remove-source-branch --title "{{TITLE}}" --description "{{BODY}}"` |
| **state** | `glab api "projects/:id/merge_requests/{{ID}}" \| jq -r '.state'` |
| **ci-status** | `glab api "projects/:id/merge_requests/{{ID}}" \| jq -r '.head_pipeline.status'` |
| **discussions** | `glab api "projects/:id/merge_requests/{{ID}}/discussions"` |
| **comment** | `printf '{"body":"%s"}' "{{BODY}}" \| glab api --method POST "projects/:id/merge_requests/{{ID}}/discussions" --input -` |
| **diff** | `glab mr diff {{ID}}` |
| **inline-comment** | `glab api --method POST "projects/:id/merge_requests/{{ID}}/discussions" --input -` with position object (base_sha, start_sha, head_sha, path, new_line) |
| **target-branch** | `glab api "projects/:id/merge_requests/{{ID}}" \| jq -r '.target_branch'` |

### `gh` — GitHub CLI

| Operation | Command |
|-----------|---------|
| **check** | `gh pr list --head {{BRANCH}} --state open` |
| **create** | `gh pr create --title "{{TITLE}}" --body "{{BODY}}"` |
| **state** | `gh pr view {{ID}} --json state --jq '.state'` |
| **ci-status** | `gh pr view {{ID}} --json statusCheckRollup --jq '.statusCheckRollup[].state'` |
| **discussions** | `gh api "repos/:owner/:repo/pulls/{{ID}}/comments"` |
| **comment** | `gh api --method POST "repos/:owner/:repo/issues/{{ID}}/comments" --field body="{{BODY}}"` |
| **diff** | `gh pr diff {{ID}}` |
| **inline-comment** | `gh api --method POST "repos/:owner/:repo/pulls/{{ID}}/comments" --field body="{{BODY}}" --field commit_id={{SHA}} --field path="{{FILE}}" --field line={{LINE}} --field side=RIGHT` |
| **target-branch** | `gh pr view {{ID}} --json baseRefName --jq '.baseRefName'` |

## Example Adapter Configurations

### GitLab CLI — shorthand
```markdown
## MR Adapter
**Status**: configured
**Adapter**: glab
```

### GitHub CLI — shorthand
```markdown
## MR Adapter
**Status**: configured
**Adapter**: gh
```

### Azure DevOps CLI — explicit
```markdown
## MR Adapter
**Status**: configured
**Adapter**: az repos pr
**check**: az repos pr list --source-branch {{BRANCH}} --status active --query "[0].pullRequestId" -o tsv
**create**: az repos pr create --title "{{TITLE}}" --description "{{BODY}}" --auto-complete
**state**: az repos pr show --id {{ID}} --query "status" -o tsv
**target-branch**: az repos pr show --id {{ID}} --query "targetRefName" -o tsv
```

### Custom MCP Server — explicit
```markdown
## MR Adapter
**Status**: configured
**Adapter**: my-vcs-mcp
**check**: invoke tool `find_open_pr` with branch={{BRANCH}}
**create**: invoke tool `create_pr` with title={{TITLE}} body={{BODY}}
**state**: invoke tool `get_pr_status` with id={{ID}}
**comment**: invoke tool `post_comment` with id={{ID}} body={{BODY}}
```

## Constraints

- For well-known CLIs, use the Known Adapters command table — do not re-declare standard commands.
- For custom adapters, declare only the operations the project's skills actually use.
- Always substitute `{{PLACEHOLDER}}` tokens before invoking any command.
- Never use plain `git push --force`; always use `git push --force-with-lease`.
