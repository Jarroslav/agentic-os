---
name: qa-gates
description: |-
  Walks the host project's quality gates in order — lint, then build, then unit/affected tests, then any configured UI tests — and returns a structured report. It's runner-agnostic: it detects npm/pnpm/yarn/cargo/poetry/uv/go from the manifest files, caches the resulting gate plan, and defers any missing browser-level coverage to feature-verification.
version: 0.4.0
license: Apache-2.0
authors:
  - agentic-os
---

# qa-gates

Executes the host project's quality gates and hands back a structured report for the pipeline to act on.

## Inputs

- `branch` — the working feature branch
- `merge_base` — defaults to `origin/main` if not provided
- `repo_path` — absolute path to the current checkout
- `run_dir` — for cache + report writes

## Guide-First Gate Resolution

When `.agentic/guides/quality-gates.md` exists, read it first and execute exactly the gates it defines, in the order it defines them.
Nothing here should be invented, swapped in, or auto-detected ahead of what that file says.

For each gate from `.agentic/guides/quality-gates.md`:

1. Output: `Running gate: <name> — command: <Run field value>`.
2. Run the exact command from the **Run** field verbatim.
3. Evaluate pass/fail using only the **Pass** and **Fail** criteria from the file.
4. If the gate has an **Auto-fix** field and the gate failed, run that exact command and re-run the gate once.
5. If the gate has a **Skip if** field, evaluate that condition literally. If the field is absent, do not skip.
6. Report `PASS`, `FAIL`, `SKIPPED`, or `N/A` before moving to the next gate.

Every in-scope guide-defined gate should still run even after an earlier one fails, so the final report reflects the complete quality picture. A failing gate determines the overall outcome, but it must not prevent subsequent guide-defined gates from executing.

A narrower run is fine as long as it's expressed as a subset of the gates in the file — e.g. a quick check, lint-only, or skipping tests. Anything outside that requested subset gets marked `N/A` in the report.

Fall back to runner auto-detection only when the guide file doesn't exist and the caller isn't inside a foundation-required full SDLC run.

## Step 1 — Detect the runner (project-aware)

Look at the repo root and match against the table below. Take the first match; npm is never assumed by default.

| Manifest | Runner | Default gate commands |
|----------|--------|-----------------------|
| `package.json` + `pnpm-lock.yaml` | `pnpm` | `pnpm lint`, `pnpm build`, `pnpm test`, `pnpm test:ui` |
| `package.json` + `yarn.lock` | `yarn` | `yarn lint`, `yarn build`, `yarn test`, `yarn test:ui` |
| `package.json` (other lock or none) | `npm` | `npm run lint`, `npm run build`, `npm test`, `npm run test:ui` |
| `Cargo.toml` | `cargo` | `cargo clippy -- -D warnings`, `cargo build`, `cargo test` (no UI gate) |
| `pyproject.toml` with `[tool.poetry]` | `poetry` | `poetry run ruff check`, `poetry run python -m compileall .`, `poetry run pytest` |
| `pyproject.toml` with `[tool.uv]` or `uv.lock` | `uv` | `uv run ruff check`, `uv run python -m compileall .`, `uv run pytest` |
| `pyproject.toml` (other) | `python` | `ruff check`, `python -m compileall .`, `pytest` |
| `go.mod` | `go` | `go vet ./...`, `go build ./...`, `go test ./...` (no UI gate) |
| (none of the above) | `unknown` | ASK the user once: "Which commands run lint / build / tests in this project? (or 'skip')" |

For Node-family runners, confirm each default script actually exists in `package.json.scripts` before invoking it. A missing script is marked `SKIPPED`, never treated as a failure.

Non-Node runners use tool commands rather than script names, so there's nothing to look up; if the underlying binary itself isn't installed, mark that gate `SKIPPED` and move on.

## Step 2 — Build the gate plan

Generate the plan once per repo checkout and cache it at `<run_dir>/gate-plan.json`:

```json
{
  "schema": 1,
  "runner": "npm | pnpm | yarn | cargo | poetry | uv | python | go | custom",
  "gates": [
    {"id": "lint",  "command": "...", "available": true},
    {"id": "build", "command": "...", "available": true},
    {"id": "unit",  "command": "...", "available": true},
    {"id": "affected", "command": "...", "available": false},
    {"id": "ui",    "command": "...", "available": false}
  ],
  "ui_globs": ["\\.(tsx|jsx|css|html|vue|svelte)$", "src/(ui|frontend|components)/"],
  "detected_at": "<ISO>"
}
```

Only re-detect when:

- The cache doesn't exist yet, or
- `package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, or the lockfile has changed since `detected_at`.

## Step 3 — Decide which gates to run

Compute `git diff --name-only <merge_base>...HEAD` and use it to decide what applies:

- **Lint / Build / Unit** — always run when `available: true`.
- **Affected tests** — run this when the project has a changed-file-aware command available, e.g. `vitest related`, `jest --findRelatedTests`, `pytest <derived paths>`, `go test <changed packages>`, or something the user configured. Mark `SKIPPED` if nothing like that exists.
- **UI gate** — required whenever the diff touches a path matching any of `ui_globs`.
  - Diff touches UI globs AND `gates.ui.available === true` → **run**.
  - Diff touches UI globs AND `gates.ui.available === false` → mark as `SKIPPED` with reason "UI surface changed but no configured UI test script; feature-verification must provide browser evidence."
  - Diff does **not** touch UI globs → mark as `SKIPPED` with reason "no UI surface changed". This IS a green outcome.

## Step 4 — Run the gates in order

Follow this sequence. Fallback runner-detection mode stops at the first failure and reports it; guide-first mode instead follows the continuation rules described in the Guide-First section above.

1. **Lint** — gate plan command. Zero warnings required where the runner enforces it.
2. **Build** — gate plan command.
3. **Unit tests** — gate plan command.
4. **Affected tests** — gate plan command, only if available.
5. **UI tests (conditional)** — gate plan command, only if Step 3 marked it `run`.

For each gate, capture its exit code plus the last 50 lines of combined stderr/stdout.

## Output

Write `<run_dir>/qa-report.md`:

```markdown
# QA Gate Report — <run-id>

**Branch**: <branch>
**Runner**: <detected runner>
**Started**: <ISO timestamp>
**Status**: PASSED | BLOCKED

## Gates

| Gate  | Status | Duration | Command | Notes |
|-------|--------|----------|---------|-------|
| lint  | PASS / FAIL / SKIPPED | 12s | `<exact cmd>` | ... |
| build | ... | ... | ... | ... |
| unit  | ... | ... | ... | ... |
| ui    | SKIPPED | — | (n/a) | no UI surface changed |

## Failure detail (if any)

<last 50 lines of failing gate output>

## Drift signal

<set to "yes" if implementation appears to have diverged from spec — e.g. type signatures or method names referenced in the spec no longer match. Otherwise "no".>
```

Return to the caller:

```json
{
  "passed": true,
  "blocked_gate": null,
  "drift_detected": false,
  "gate_plan": { "...": "the plan used" }
}
```

## Step 5 — Determine gate outcome

| Lint | Build | Unit | Affected | UI | Outcome |
|------|-------|------|----------|----|---------|
| any FAIL | — | — | — | — | `BLOCKED` |
| PASS | PASS | PASS | PASS or SKIPPED | PASS or SKIPPED | `PASSED` |

A `SKIPPED` UI gate for "not configured" while the UI surface actually changed only counts as green for this mechanical phase — it's not a free pass overall. The pipeline still has to run `feature-verification` afterward, and that step withholds handoff until real browser evidence shows up.

## Constraints

- Never write outside `<run_dir>` and the project's standard test output paths.
- Run custom commands from a user-provided plan exactly as given; don't rewrite them.
- A `SKIPPED` UI gate is only acceptable because `feature-verification` is the one responsible for functional browser proof.
- This skill never triggers MR/PR creation. It reports readiness and stops; `mr-creator` or whatever PR tool the host project prefers is a separate, manual next step.
