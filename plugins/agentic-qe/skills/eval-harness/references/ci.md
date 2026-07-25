# Wire Evals into CI and Pre-Commit

Automation reference for a two-layer eval harness (deterministic runner + LLM judge).
Everything here is **opt-in**: set nothing up unless the user explicitly asks for it.

## The one rule that shapes everything

| Layer | Needs secrets | Speed | Cost | Where it may run |
|---|---|---|---|---|
| Deterministic (code-based contracts) | No | Fast | Free | Pre-commit hook, required CI check |
| LLM judge | Yes (API key) | Slow | Paid | Optional CI job only — never a gate |

> The deterministic layer earns a place in hooks and required checks precisely because it is
> free, fast, and secret-less. The judge layer fails all three tests, so it must never block a
> commit or a merge. Keep the two layers in separate jobs and never mark the judge job required.

Blast radius: installing the automation below writes repo files (R2). The judge job itself
calls an external LLM (R3), which is why it always sits behind a human gate — manual
dispatch or a schedule someone deliberately created.

## Local hook

### Install pattern

Use a committed hooks directory wired via `core.hooksPath` — not per-clone copies into
`.git/hooks/`. The hook template ships in this skill's asset directory under `ci/hooks/`.

```bash
mkdir -p .github/hooks
cp <skill-assets>/ci/hooks/pre-commit .github/hooks/pre-commit
chmod +x .github/hooks/pre-commit          # required — copy does not preserve the bit
git config core.hooksPath .github/hooks
```

For TypeScript repos, expose the config step as a one-command install so teammates get the
hook without reading docs:

```jsonc
// package.json
{
  "scripts": {
    "hooks:install": "git config core.hooksPath .github/hooks"
  }
}
```

> `core.hooksPath` **replaces** `.git/hooks` entirely. Any other hook the repo depends on
> (husky output, lint-staged wrappers, commit-msg checks) must move into the same committed
> directory, or it silently stops running.

### Hook body per language

The template defaults to the npm test script. Edit for Python:

| Harness | Hook command |
|---|---|
| TypeScript (npm) | `npm test` |
| Python (pytest) | `pytest <path-to-eval-runner-test>` |

### pre-commit vs pre-push

Default to **pre-commit**: the deterministic layer is fast enough to run on every commit. If
the repo's test script is slow for unrelated reasons, install the identical file as
`pre-push` instead — fewer runs, but still fires before anything leaves the machine.

### The escape hatch is a signal

Developers can always bypass with `git commit --no-verify`. Occasional use is fine. If it
becomes routine, the eval contracts are too strict — loosen them (see the spec/contract
format reference in this directory) rather than normalizing the bypass.

## Pipeline: deterministic layer

Trigger on pull/merge request events plus pushes to the default branch.

| Context | Runner / image | Setup | Command |
|---|---|---|---|
| GitHub, TypeScript | `ubuntu-latest`, Node 20 with npm cache | checkout → setup-node → `npm ci` | `npm test` |
| GitHub, Python | `ubuntu-latest`, Python 3.12 | checkout → setup-python → `pip install -r requirements.txt` | `pytest <eval runner test>` |
| GitLab, TypeScript | `node:20` | `npm ci` (+ optional python3 install, below) | `npm test` |
| GitLab, Python | `python:3.12` | `pip install -r requirements.txt` | `pytest <eval runner test>` |

### GitHub Actions

File: `.github/workflows/evals.yml`. Include `workflow_dispatch` from day one — it is the
gate for the optional judge job later.

```yaml
name: evals
on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:   # manual gate for the judge job

jobs:
  evals-deterministic:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npm test
```

> GitHub's `ubuntu-latest` image ships both Node and Python. A TypeScript job can therefore
> execute script-type contracts that shell out to `python3` (and a Python job can shell out
> to Node) with zero extra setup.

### GitLab CI

Config lives in the root `.gitlab-ci.yml` (or a file included from it). Match
merge-request pipelines and the default branch:

```yaml
evals-deterministic:
  image: node:20
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  before_script:
    # Only if any skill ships script-type contracts — node:20 has no Python.
    - apt-get update && apt-get install -y python3
  script:
    - npm ci
    - npm test
```

> Unlike GitHub's runner image, the `node:20` container lacks Python. Add the
> `before_script` install only when script contracts need it; drop it otherwise.

The Python variant swaps the image for `python:3.12`, installs requirements, and runs pytest
against the eval runner test.

## Pipeline: judge layer (opt-in, never blocking)

Add this only on explicit user request. Non-negotiables:

- Separate job. Never a required check. Never merge-blocking.
- Credentials come **only** from the platform secret store: GitHub repository
  secrets/variables, or GitLab masked + protected CI variables. Never from committed files.
- Non-secret provider config (provider selector, gateway base URL) may live in plain CI
  variables; the API key itself stays masked.
- Human gate: on GitHub, run only on `workflow_dispatch`; on GitLab, set `when: manual`.

Env var names below are **placeholders** — substitute the names from the providers reference
in this directory, matching whichever provider was chosen during harness setup.

### GitHub judge job

```yaml
  evals-judge:
    if: github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npm run eval:llm
        env:
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}        # placeholder name
          LLM_PROVIDER: ${{ vars.LLM_PROVIDER }}         # non-secret, plain variable
          LLM_BASE_URL: ${{ vars.LLM_BASE_URL }}         # non-secret, plain variable
```

### GitLab judge job

```yaml
evals-judge:
  image: node:20
  when: manual
  variables:
    LLM_PROVIDER: "<provider>"   # non-secret; key comes from a masked CI variable
  script:
    - npm ci
    - npm run eval:llm
```

### Prefer a schedule over per-PR runs

The best home for judge runs is a **scheduled pipeline** — native scheduling on either
platform, e.g. nightly. That catches behavioral drift continuously without adding latency or
cost to every PR.

## Decision summary

| Question | Answer |
|---|---|
| Automate at all? | Only when the user asks. |
| Hook timing? | pre-commit by default; pre-push if repo scripts are slow. |
| Judge in CI? | Only on explicit request; separate, manual-gated, never required. |
| Test command? | `npm test` (TS) / `pytest` on the eval runner test (Python). |
| python3 in GitLab Node job? | Only when script-type contracts exist. |
| Frequent `--no-verify`? | Loosen the contracts, don't tolerate the bypass. |

## Related references

- **Spec/contract format** (sibling): loosening contracts that prove brittle.
- **Providers** (sibling): real env var names for the judge job.
- **Skill assets** `ci/hooks/`: the pre-commit template copied above.
- **Parent skill**: defines the two-layer harness this document automates.
