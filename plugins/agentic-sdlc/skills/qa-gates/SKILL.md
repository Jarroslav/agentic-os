---
name: qa-gates
version: 0.1.0
license: Apache-2.0
author: agentic-os
description: >-
  Run the host project's quality gates in a fixed order (lint -> build -> unit
  tests -> affected tests -> optional UI tests) and return a structured,
  machine-readable merge-readiness report. Runner-agnostic: detects the build
  tool (npm/pnpm/yarn/cargo/poetry/uv/go) from manifest files, caches a gate
  plan, and defers browser-level proof to feature-verification. Invoke during a
  change's implementation phase when an orchestrator needs to know whether the
  diff is mechanically merge-ready — triggered by "run qa gates", "run the
  quality gates", "check merge readiness", "run lint/build/tests on this
  branch", or the SDLC pipeline's post-implementation QA step. This skill
  reports readiness only; it never creates an MR/PR.
---

# qa-gates

Execute the host project's quality gates in a fixed sequence and emit a
structured report the caller uses to decide merge readiness. You detect the
project's runner, resolve a gate plan, run the gates, and return a verdict.
You never create a merge request or pull request, and you never supply
functional browser evidence — that belongs to `feature-verification`.

Blast radius: **R0** (read-only detection, diff, manifest inspection) plus
**R1** (writes only under `<run_dir>` and standard test output paths). Never
write repo files outside those locations. Run user-provided plan commands
exactly — no rewriting.

## Inputs

| Input | Meaning | Default |
|---|---|---|
| `branch` | branch under test | required |
| `merge_base` | base ref for the diff | `origin/main` |
| `repo_path` | repository root | required |
| `run_dir` | directory for cache + report writes | required |

Compute the change set once with:

```
git diff --name-only <merge_base>...HEAD
```

## Gate order (fixed)

1. `lint`
2. `build`
3. `unit`
4. `affected` (changed-file-aware tests)
5. `ui` (conditional — only when the diff touches a UI surface)

## Step 1 — Resolve the gate plan

Two resolution modes. Prefer the guide.

**Guide-first.** If a rendered gate registry file exists, read it and run
exactly the gates it lists, in the order it lists them. Guide file paths,
top-level preferred over the standards subpath:

- `.agentic/guides/quality-gates.md`
- `.agentic/guides/standards/quality-gates.md`

When both exist, the top-level path wins. Do not invent, swap in, or
auto-detect any gate ahead of what this file specifies.

**Fallback auto-detection.** Fall back to runner auto-detection only when the
guide file does not exist and the caller is not inside a foundation-required
full run. A foundation-required run expects the guide to be present.

### Runner detection (first match wins; npm is never assumed by default)

| Manifest | Runner | lint / build / test / ui |
|---|---|---|
| `package.json` + `pnpm-lock.yaml` | pnpm | `pnpm lint` / `pnpm build` / `pnpm test` / `pnpm test:ui` |
| `package.json` + `yarn.lock` | yarn | `yarn lint` / `yarn build` / `yarn test` / `yarn test:ui` |
| `package.json` (other/no lock) | npm | `npm run lint` / `npm run build` / `npm test` / `npm run test:ui` |
| `Cargo.toml` | cargo | `cargo clippy -- -D warnings` / `cargo build` / `cargo test` / (no UI) |
| `pyproject.toml` `[tool.poetry]` | poetry | `poetry run ruff check` / `poetry run python -m compileall .` / `poetry run pytest` |
| `pyproject.toml` `[tool.uv]` or `uv.lock` | uv | `uv run ruff check` / `uv run python -m compileall .` / `uv run pytest` |
| `pyproject.toml` (other) | python | `ruff check` / `python -m compileall .` / `pytest` |
| `go.mod` | go | `go vet ./...` / `go build ./...` / `go test ./...` / (no UI) |
| none | unknown | ask user once |

For an `unknown` runner, ask the user **once** for the lint/build/test commands
(or `'skip'`), then proceed with whatever they give.

Affected-test command examples: `vitest related`, `jest --findRelatedTests`,
`pytest <derived paths>`, `go test <changed packages>`. Only run the affected
gate when a changed-file-aware command is available; otherwise mark it
`SKIPPED`.

### Cache

Persist the resolved plan to `<run_dir>/gate-plan.json`:

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

Re-detect the plan only when the cache is absent **or** a manifest/lockfile
(`package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, or the lockfile) has
changed since `detected_at`. Otherwise reuse the cached plan.

## Step 2 — Run the gates

Log each gate before running it, verbatim:

```
Running gate: <name> — command: <Run field value>
```

For every gate, capture the exit code and the **last 50 lines** of combined
stderr/stdout.

**Node-family runners:** before running a script, confirm it exists in
`package.json.scripts`. A missing script is `SKIPPED`, not a failure.

**Non-Node runners:** these use tool commands rather than script names, so
there is nothing to look up; if the underlying binary is not installed, mark
the gate `SKIPPED` and move on.

### Guide-gate semantics

Each guide gate carries these fields: **Run**, **Pass**, **Fail**,
**Auto-fix**, **Skip if**.

- Execute **Run** verbatim.
- Decide pass/fail via **Pass** / **Fail** only.
- If **Auto-fix** is present and the gate failed, run it once and re-run the
  gate once.
- If **Skip if** is present, evaluate it literally; absent means never skip.

### Execution-mode difference

- **Guide-first:** run every in-scope gate even after an earlier failure, for a
  complete picture. A failing gate sets the overall outcome but does not halt
  the remaining gates.
- **Fallback auto-detection:** stop at the first failure and report it.

Narrower runs are allowed only as a subset of the guide gates. Any gate outside
the requested subset is marked `N/A` in the report.

### UI gate rule

The UI gate is required when the diff touches any `ui_globs` path.

| Condition | Result |
|---|---|
| touches UI globs AND `ui.available === true` | run the gate |
| touches UI globs AND `ui.available === false` | `SKIPPED`, reason: `UI surface changed but no configured UI test script; feature-verification must provide browser evidence.` |
| no UI globs touched | `SKIPPED`, reason: `no UI surface changed` (GREEN outcome) |

A `SKIPPED` UI gate that is simply not configured counts green **for this
mechanical phase only**. Downstream `feature-verification` still withholds
handoff until real browser evidence exists.

## Step 3 — Outcome

| Situation | Status |
|---|---|
| any gate `FAIL` | `BLOCKED` |
| `lint` + `build` + `unit` PASS, and `affected`/`ui` each PASS-or-SKIPPED | `PASSED` |

Per-gate report states: `PASS` | `FAIL` | `SKIPPED` | `N/A`.

## Outputs

### Report file

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

## Failure detail

<last 50 lines of the failing gate's output, if any>

## Drift signal

<"yes" if the implementation appears to have diverged from spec — e.g. type
signatures or method names referenced in the spec no longer match — otherwise
"no">
```

### Return object

Return to the caller:

```json
{ "passed": true, "blocked_gate": null, "drift_detected": false, "gate_plan": { "...": "the plan used" } }
```

## References

- `.agentic/guides/quality-gates.md` (or `.agentic/guides/standards/quality-gates.md`)
  — the rendered gate registry. When present it is authoritative: run exactly
  the gates it lists, with **Run/Pass/Fail/Auto-fix/Skip if** semantics. The
  agentic-os installer renders this registry into the standards path.

## Boundaries

- Does not create merge requests or pull requests. Handoff to `mr-creator` (or
  the host's PR tool) is a separate, manual next step.
- Does not provide browser/functional UI proof — that is delegated to
  `feature-verification`, which owns the final handoff gate.
- Does not invent, swap, or auto-detect gates beyond what the guide file
  specifies.
- Does not rewrite user-provided plan commands.
- Never writes outside `<run_dir>` and standard test output paths.
