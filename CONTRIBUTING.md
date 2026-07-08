# Contributing

`main` is protected: **no direct pushes**, every change lands through a pull
request that passes CI and is approved by the owner (@Jarroslav). This holds for
everyone, including the owner.

## Workflow

```bash
# 1. Branch off main
git switch -c feat/my-change        # or fix/…, docs/…, chore/…

# 2. Make the change, then run the gates locally (CI runs the same ones)
bash tests/t0/run.sh                 # 50 hook unit tests
bash tests/t0/run-output-contract.sh # 12 output-contract parser checks
bash tests/run-matrix.sh             # T1–T7 acceptance (re-runs the output-contract suite as T7)

# 3. Push the branch and open a PR
git push -u origin feat/my-change
gh pr create --fill --base main
```

CI (`.github/workflows/ci.yml`) re-runs the hook unit tests and the T1–T7
acceptance matrix on every PR. A red run blocks merge. `@Jarroslav` is a code
owner, so the PR requests their review automatically.

## Rules that CI enforces

- **The acceptance matrix stays green.** New templates or skills must keep
  `tests/run-matrix.sh` fully passing (it prints its own `N passed, 0 failed`
  at the end) — add cases when you add behavior.
- **JSON manifests and presets parse**, and preset template IDs resolve.

## Commit style

Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`). No AI
attribution footers.

## Merging your own changes

GitHub does not let you approve your own PR. If you are the sole maintainer, see
[`docs/GITHUB-SETUP.md`](docs/GITHUB-SETUP.md) for the two supported options
(a second approver account, or an admin bypass for owner PRs).

## Reporting a bug or requesting a feature

Open a GitHub issue. Include the role preset(s) installed, the discovered
stack (matched curated profile, or a summary of the full-discovery result if
none matched), and (for bugs) the output of `/agentic-doctor`.

## License

By contributing, you agree your contribution is licensed under this repo's
[Apache-2.0 license](LICENSE).
