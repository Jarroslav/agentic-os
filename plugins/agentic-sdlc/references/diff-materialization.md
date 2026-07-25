# Diff materialization: giving review subagents a stable diff to read

Canonical recipe for turning a code-review target into a unified-diff **file on disk** that the review orchestrator can open. Skills cite this page instead of re-deriving git invocations. Preserve every id, path, marker, and command below character-for-character.

## Why a file

Review lenses read diff **text** — not a base ref, not metadata, not a summary. The `code-review-orchestrator` opens whatever the `path` field points at, so that path must resolve to a real, readable file.

> Writing bytes to disk is the contract because it is the least ambiguous channel. It fixes exactly what was reviewed, and it lets the caller bind a sha-256 `signature` to those bytes. A placeholder string is not a path; if the orchestrator cannot read diff text it **safe-fails** and the review never runs — better a missing review than a phantom one.

A read-only fallback exists but is not the contract: the orchestrator may reconstruct the diff itself from a `diff_base` via `git diff <diff_base>`.

## Consumers

Authors wiring up code-review gate resolution: the `code-review-orchestrator` and the callers that feed it — `sdlc-task`, `sdlc-pipeline`, and the standalone `code-review` wrapper.

## Gates and output files

| Gate id | Output file |
|---|---|
| `code-review.final` | `<run_dir>/code-review.diff` |
| `code-review.check` | `<run_dir>/code-review-check.diff` |

The artifact handed to the orchestrator, `kind: "diff"`:

```json
{"kind": "diff", "path": "<run_dir>/code-review.diff", "summary": "<diffstat + risk flags>", "signature": "<sha-256>"}
```

The `code-review-orchestrator` consumes `path`, `signature`, and (in the fallback path) `diff_base`.

## Global rules

- **Lockfile churn is always dropped.** Every command carries the pathspec `-- . ':(exclude)package-lock.json'`. The review never reads `package-lock.json`.
- **`git diff` never shows untracked files** in any form. Untracked handling is separate (see below).
- **Pick a scope first; paths only filter.** Explicit paths are appended to a chosen scope, never a scope on their own.
- **Read-only stays read-only.** Only a caller that is already permitted to mutate the tree may stage. Untracked enumeration and rendering never run `git add` or `git add -N`.

## Diff range forms

- **Three dots** (`A...HEAD`) — symmetric difference against the merge-base of the two endpoints. This is the final-round form.
- **Two dots** (`A..B`) — plain range between two commits.
- **From a commit** (`git diff <commit>`) — captures both committed and working-tree changes relative to that commit.

## Final round — `code-review.final`

Resolve the merge-base base ref in this order:

1. Configured base branch in `.agentic/guides/standards/git-workflow.md`, if that file names one.
2. Otherwise the repository's default branch.
3. Otherwise fall back to `main`. (The pipeline uses `origin/main` when no base is set.)

Then materialize:

```
git diff <merge_base>...HEAD -- . ':(exclude)package-lock.json' > <run_dir>/code-review.diff
```

## Check round — `code-review.check`

Record the pre-fix head **before** touching anything. Capturing the baseline after the fixes have landed yields an empty diff.

```
reviewed_head=$(git rev-parse HEAD)     # record this BEFORE changing anything
# ... apply fixes ...
git diff "$reviewed_head" -- . ':(exclude)package-lock.json' > <run_dir>/code-review-check.diff
```

## Untracked files (working-tree scope only)

Untracked files belong to the working-tree scope alone. Include them there **whenever that scope is used** — not as a last resort, and independent of whether the tracked diff came back empty. Never fold them into staged, branch-vs-base, or explicit-range scopes.

Enumerate:

```
git status --porcelain=v1 -z --untracked-files=all -- <paths>
```

- Split on the NUL separator. `-uall` expands untracked directories down to each nested file — plain `--porcelain` would collapse them to `?? dir/`. `-z` emits raw, unquoted, NUL-terminated paths.
- Skip the run/output directory you just created; its own `code-review.diff` is itself untracked.
- Render each `?? ` entry read-only and append it:

```
git diff --no-index /dev/null <file>
```

`git diff --no-index` exits 1 when the two inputs differ. That is expected output for a present file, not an error — do not treat the exit code as failure.

## Empty-diff guard

An empty in-scope diff means there is nothing to review. Do **not** call the orchestrator on it: every lens would return its "nothing to review" sentinel, and a wall of sentinels reads like a false clean approve. After materializing tracked changes (and untracked, for the working-tree scope), if the result is empty, surface a no-changes state to the caller or select a different scope.

## Standalone wrapper — scope to command

All rows write into `<run_dir>/code-review.diff`.

| Scope | Command range |
|---|---|
| Branch vs merge-base | `git diff <merge_base>...HEAD -- . ':(exclude)package-lock.json'` |
| Staged | `git diff --cached -- . ':(exclude)package-lock.json'` |
| Working tree (committed-or-not vs HEAD) | `git diff HEAD -- . ':(exclude)package-lock.json'` |
| Explicit commit range | `git diff <from>..<to> -- . ':(exclude)package-lock.json'` |
| Explicit paths | filter only — append `-- <paths>` before the `':(exclude)package-lock.json'` pathspec of a chosen scope |

## Scope

This page defines only the diff-capture channel and its ranges. It does not define review lenses, verdict semantics, or the orchestrator's internal logic; it does not stage or commit for read-only callers; it never reviews `package-lock.json`; and it is not a general git tutorial.

## Related

- Cited by `plugins/agentic-sdlc/skills/code-review/SKILL.md` — "follow exactly" and "reuse the canonical diff recipe; do not invent".
- Siblings in this directory: `gate-catalog.md`, `mr-adapters.md`, `schemas/review-bundle.schema.json`.
