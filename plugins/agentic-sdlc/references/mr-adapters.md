# MR adapters: resolving the MR/PR backend without hardcoding one

SDLC skills that open, inspect, or comment on a merge request or pull request never name a
source-control CLI, platform API, or vendor tool in their own logic. Every such action routes
through an **adapter** — a declared mapping from a fixed set of named operations to concrete
commands. This keeps the pipeline portable: swap the adapter, keep the skills.

> The contract is the abstraction boundary. A skill asks for `create` or `ci-status`; the adapter
> decides whether that resolves to `glab`, `gh`, an MCP tool call, or a bespoke REST invocation. No
> skill is allowed to assume the answer.

Adapters are external side-effect surfaces. The read-only ops (`check`, `state`, `ci-status`,
`discussions`, `diff`, `target-branch`) query remote APIs but change nothing; the write ops
(`create`, `comment`, `inline-comment`) are R3 and always run behind a judgment gate in the calling
skill.

## Where the adapter lives

The chosen adapter is recorded in exactly one place:

- **File:** `.agentic/guides/project.md`
- **Section header:** `## MR Adapter`

That section is the single source of truth. `mr-creator` writes and reads it; `mr-watch` and the
review skills read it before invoking any operation.

### Declaration fields

| Field | Values / meaning |
|-------|------------------|
| `**Status**` | `configured` \| `not configured` |
| `**Adapter**` | adapter name (recognized CLI) or the marker for an explicit block |
| `**Body Template**` | *(optional)* overrides the built-in MR/PR body template |
| `**Comment Template**` | *(optional)* overrides the built-in review-comment template |

Omit a template field to fall back to `mr-creator`'s built-in template — never restate the default.

## Two ways to declare an adapter

Choose the form by whether the backend is a recognized CLI.

### 1. Shorthand — recognized CLI

For `glab` or `gh`, name the adapter and stop. The skill resolves each command from the built-in
Known Adapters table below. **Do not re-declare standard commands** for a known CLI; the table owns
them.

### 2. Explicit — custom tool, MCP server, or REST API

For anything the table does not recognize, declare each operation you use, verbatim, keyed by its
operation name. **Declare only the operations the project actually uses; omit the rest.** An adapter
that only ever opens and checks PRs needs `check`, `create`, `state`, and nothing more.

> Recognized CLI → shorthand. Everything else → explicit per-operation declaration.

## How a skill resolves the adapter

Resolution runs top to bottom; the first hit wins.

1. Read `.agentic/guides/project.md` → `## MR Adapter`. If `**Status**` is `configured`, use it.
2. Otherwise infer from the remote: `git remote get-url origin`, mapped by hostname.
3. Otherwise ask the user which tool manages MRs/PRs.

## When the adapter is not configured

A `not configured` status is not a failure. Do **not** abort. Run inference first, degrade
gracefully, then report any gaps back to the user.

1. Map the remote hostname to a CLI: `github.com` → `gh`, `gitlab.com` → `glab`.
2. Verify the inferred CLI is installed and authenticated (for example `glab auth status`). If it
   checks out, proceed and note the assumption to the user.
3. If the inferred CLI is missing or unauthenticated, ask which tool manages MRs/PRs.
4. If remote inference yields nothing, ask the user directly.

## The operation set

Nine operations cover the full review/merge surface. Placeholder tokens in the `need` column are
substituted at runtime — **always substitute every token before invoking the command.**

| Operation | What it must do |
|-----------|-----------------|
| `check` | Is there an open MR/PR for the current branch? Return its URL. |
| `create` | Create an MR/PR from title + body; return its URL. |
| `state` | Report `open` / `merged` / `closed` for `{{ID}}`. |
| `ci-status` | Report `running` / `passed` / `failed` / `none` for `{{ID}}`. |
| `discussions` | List unresolved review comments on `{{ID}}`. |
| `comment` | Post a general comment on `{{ID}}`. |
| `diff` | Return the line-level diff for `{{ID}}`. |
| `inline-comment` | Comment on a specific file + line of `{{ID}}`. |
| `target-branch` | Return the target branch of `{{ID}}`. |

### Enumerated returns

Callers branch on these exact strings — an adapter must normalize its backend's raw output to them.

- `state` → `open` \| `merged` \| `closed`
- `ci-status` → `running` \| `passed` \| `failed` \| `none`
- `inline-comment` diff side → `RIGHT`

## Placeholder tokens

Substituted at runtime before any command runs.

**Operation tokens:** `{{BRANCH}}`, `{{TITLE}}`, `{{BODY}}`, `{{ID}}`, `{{FILE}}`, `{{LINE}}`, `{{SHA}}`

**Body-template tokens:** `{{SUMMARY}}`, `{{CHANGES}}`

**Comment-template tokens:** `{{SEVERITY}}`, `{{TITLE}}`, `{{DESCRIPTION}}`, `{{IMPACT}}`, `{{FIX}}`

## Known Adapters (built-in command tables)

Shorthand adapters resolve to these. Reproduced here for reference only — do not copy them into a
project's declaration.

### `glab` (GitLab CLI)

| Operation | Command |
|-----------|---------|
| check | `glab mr list --source-branch={{BRANCH}}` |
| create | `glab mr create --remove-source-branch --title "{{TITLE}}" --description "{{BODY}}"` |
| state | `glab api "projects/:id/merge_requests/{{ID}}" \| jq -r '.state'` |
| ci-status | `glab api "projects/:id/merge_requests/{{ID}}" \| jq -r '.head_pipeline.status'` |
| discussions | `glab api "projects/:id/merge_requests/{{ID}}/discussions"` |
| comment | `printf '{"body":"%s"}' "{{BODY}}" \| glab api --method POST "projects/:id/merge_requests/{{ID}}/discussions" --input -` |
| diff | `glab mr diff {{ID}}` |
| inline-comment | `glab api --method POST "projects/:id/merge_requests/{{ID}}/discussions" --input -` with a position object (`base_sha`, `start_sha`, `head_sha`, `path`, `new_line`) |
| target-branch | `glab api "projects/:id/merge_requests/{{ID}}" \| jq -r '.target_branch'` |

### `gh` (GitHub CLI)

| Operation | Command |
|-----------|---------|
| check | `gh pr list --head {{BRANCH}} --state open` |
| create | `gh pr create --title "{{TITLE}}" --body "{{BODY}}"` |
| state | `gh pr view {{ID}} --json state --jq '.state'` |
| ci-status | `gh pr view {{ID}} --json statusCheckRollup --jq '.statusCheckRollup[].state'` |
| discussions | `gh api "repos/:owner/:repo/pulls/{{ID}}/comments"` |
| comment | `gh api --method POST "repos/:owner/:repo/issues/{{ID}}/comments" --field body="{{BODY}}"` |
| diff | `gh pr diff {{ID}}` |
| inline-comment | `gh api --method POST "repos/:owner/:repo/pulls/{{ID}}/comments" --field body="{{BODY}}" --field commit_id={{SHA}} --field path="{{FILE}}" --field line={{LINE}} --field side=RIGHT` |
| target-branch | `gh pr view {{ID}} --json baseRefName --jq '.baseRefName'` |

## Explicit-config examples

**Azure DevOps** — a partial adapter over `az repos pr`, declaring only the four operations the
project uses:

```
## MR Adapter
**Status**: configured
**Adapter**: custom

check:         az repos pr list --source-branch {{BRANCH}}
create:        az repos pr create --title "{{TITLE}}" --description "{{BODY}}"
state:         az repos pr show --id {{ID}} --query status
target-branch: az repos pr show --id {{ID}} --query targetRefName
```

**Custom MCP server** — operations map to named tool invocations with named arguments:

```
## MR Adapter
**Status**: configured
**Adapter**: custom

check:   invoke tool find_open_pr   (branch={{BRANCH}})
create:  invoke tool create_pr      (title={{TITLE}}, body={{BODY}})
state:   invoke tool get_pr_status  (id={{ID}})
comment: invoke tool post_comment   (id={{ID}}, body={{BODY}})
```

## Hard constraints

- Known-CLI adapters use the command table; do not re-declare standard commands.
- Custom adapters declare only the operations they use.
- Always substitute every placeholder token before invoking any command.
- Never `git push --force`; always `git push --force-with-lease`.

## Non-goals

- No single platform or CLI is bound; there is no default provider.
- Unused operations are never required.
- This is not a git-workflow or ticket-format spec — those live elsewhere under the guides.

## Cross-references

- `.agentic/guides/project.md` — where adapters are declared and read.
- `mr-creator` — owns the default body/comment templates and consumes the adapter.
- `mr-watch` and the review skills — invoke the operation set.
- Remote inference relies on `git remote get-url origin`.
