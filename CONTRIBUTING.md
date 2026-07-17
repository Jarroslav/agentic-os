# Contributing

`main` is protected: **no direct pushes — by anyone, including the owner.** Every
change lands through a pull request whose `gate` CI check passes. Pull requests
from contributors also require review from a code owner (@Jarroslav).

## Workflow

```bash
# 1. Branch off main
git switch -c feat/my-change        # or fix/…, docs/…, chore/…

# 2. Make the change, then run the gates locally (CI runs the same ones)
bash tests/t0/run.sh                 # 105 hook unit tests
bash tests/t0/run-output-contract.sh # 12 output-contract parser checks
bash tests/run-matrix.sh             # T1–T8 acceptance (re-runs the output-contract suite as T7)

# 3. Push the branch and open a PR
git push -u origin feat/my-change
gh pr create --fill --base main
```

CI (`.github/workflows/ci.yml`) re-runs the hook unit tests and the T1–T8
acceptance matrix on every PR. A red run blocks merge. `@Jarroslav` is a code
owner, so the PR requests their review automatically.

## Rules that CI enforces

- **The acceptance matrix stays green.** New templates or skills must keep
  `tests/run-matrix.sh` fully passing (it prints its own `N passed, 0 failed`
  at the end) — add cases when you add behavior.
- **Manifests stay consistent** (`tests/lib/check-manifests.py`): every JSON
  manifest and preset parses, each plugin's `.claude-plugin` /
  `.cursor-plugin` / `.codex-plugin` manifests carry the same version, and the
  author/owner identity matches the canonical block everywhere.
- **Neutrality is mechanical** (`tests/lib/check-neutrality.py`): no PII,
  personal names, or organization names in tracked files — cleartext shape
  classes (emails, home paths, confidentiality markers, vendor model IDs)
  plus a hashed token denylist in `tests/lib/neutrality-policy.json`. The
  canonical plugin-author identity is the one sanctioned exception.

## Releasing

Each plugin versions independently, so releases are cut and tagged per plugin:

1. Bump `version` in **all** of that plugin's host manifests
   (`.claude-plugin/plugin.json`, `.cursor-plugin/plugin.json`, and
   `.codex-plugin/plugin.json` where present) — CI fails on drift.
2. Move the plugin's `CHANGELOG.md` `[Unreleased]` entries under the new
   version heading.
3. Merge via PR as usual, then tag the merge commit and push the tag:

   ```bash
   git tag -a agentic-os-v0.1.0 -m "agentic-os 0.1.0"   # agentic-sdlc-v<X.Y.Z> for the SDLC plugin
   git push origin --tags
   ```

Tags activate the clean template-only upgrade diff documented in
[`plugins/agentic-os/docs/UPGRADING.md`](plugins/agentic-os/docs/UPGRADING.md).

## Commit style

Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`). No AI
attribution footers.

## Reporting a bug or requesting a feature

Open a GitHub issue. Include the role preset(s) installed, the discovered
stack (matched curated profile, or a summary of the full-discovery result if
none matched), and (for bugs) the output of `/agentic-doctor`.

## License

By contributing, you agree your contribution is licensed under this repo's
[Apache-2.0 license](LICENSE).
