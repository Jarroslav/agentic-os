# Set up the eval harness in a Python repo

Follow this reference when the host repo is Python and you are installing the
skill-evaluation harness there. It covers copying the templates, wiring imports,
installing dependencies, and running both test layers. It does **not** cover spec
authoring (`spec-format.md`), provider credentials (`references/providers.md`),
or the TypeScript variant of this harness.

Overall blast radius of the install: **R2** — you write files into the target
repo. Running the harness afterwards is **R1** (report artifacts only).

## Prerequisites

| Requirement | Why |
|---|---|
| Python >= 3.10 | Harness code uses `X \| Y` union annotations; older interpreters raise at import time. |
| pytest | Only hard dependency; drives the code-based layer. |
| python-dotenv (optional) | Auto-loads `.env` for the LLM layer. Without it, export provider vars into the process environment yourself. |
| Provider SDK (conditional) | Only for the provider path you pick — see [Dependencies](#2-install-dependencies). |

## What gets installed

Copy all four templates from the parent skill's `assets/python/` directory into
the harness directory. Copy them — never symlink or reference them in place;
the target repo must own its copies.

| Template | Role |
|---|---|
| `runner.py` | Contract validation: skill discovery, frontmatter, schemas, scripts. Also runs standalone as a one-shot summary via `python -m`. |
| `test_runner.py` | Pytest suite: unit tests of harness primitives plus repo-wide per-skill coverage checks. |
| `llm_eval_runner.py` | Multi-provider LLM judge; run/grade/repeat loop. |
| `evals.example.json` | Shape reference for each skill's own `eval/evals.json`. Never executed. |

## Installation steps

### 1. Pick the harness directory

Default to `eval/` at repo root. If the repo already has an established
location for evaluation code, use that instead — repo convention beats the
default.

Copy the four templates there, then create an **empty `__init__.py` in the
harness directory. This is mandatory**, not a nicety: `python -m` invocation of
the LLM runner fails without it.

### 2. Install dependencies

Check whether the interpreter is externally managed (PEP 668 — the norm on
current macOS/Homebrew Pythons and many Linux distros). If it is, a bare
`pip install` will be refused; create a venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pytest python-dotenv
```

Add `.venv/` to `.gitignore`.

> Prefer the venv route whenever the system Python is externally managed.
> Fighting PEP 668 with override flags pollutes the system site-packages and
> breaks on the next OS update.

Provider SDKs are selective — install only what the chosen provider path
needs:

- Gateway-routed path: its one gateway package.
- Native-SDK path: the provider's own package.
- OpenAI-compatible endpoints: **nothing** — that path uses stdlib `urllib`
  only.

`references/providers.md` is the authoritative list of packages, providers, and
per-provider env vars; don't duplicate that here.

Record the dependencies in the repo manifest. Suggested: an
optional-dependencies group in `pyproject.toml`:

```toml
[project.optional-dependencies]
eval = ["pytest", "python-dotenv"]
```

### 3. Wire both import regimes

The harness has two distinct import mechanisms and **both** must work:

1. **Loose-module imports** — the runner files import each other as plain
   modules, so the harness directory must be on pytest's import path:

   ```toml
   [tool.pytest.ini_options]
   pythonpath = ["eval"]
   ```

2. **Package invocation** — `python -m eval.llm_eval_runner` requires the
   `__init__.py` created in step 1.

Skipping either one produces confusing partial breakage: pytest passes but
`python -m` fails, or vice versa.

### 4. Point the harness at the skills tree

Both runners discover skills under `<repoRoot>/.claude` by default and honor a
`SKILLS_ROOT` env override, resolved against the repo root.

- Skills live elsewhere? Set `SKILLS_ROOT` — no code edit.
- Only as a fallback, change the default in code — and change it in **both**
  `runner.py` and `llm_eval_runner.py`. The two defaults must never diverge.

### 5. Repo hygiene

- Append the provider variable names (placeholders, no values) to
  `.env.example`.
- Git-ignore `.env`, `__pycache__/`, and the harness report cache directory.

## Running the harness

### Code-based layer (no credentials)

Runs entirely offline; safe to wire into CI immediately.

```bash
python -m eval.runner        # one-shot contract summary
pytest eval/test_runner.py   # unit + repo coverage checks
```

> Fresh-install expectation: the repository-coverage tests **require at least
> one discovered skill with a spec**. Until per-skill `eval/evals.json` files
> exist, they fail. That is the designed sequencing — author specs first, then
> run — not a broken install.

### LLM-judge layer (credentials required)

Needs provider credentials from `.env` (or the process environment if
python-dotenv is absent). Select the provider with `EVAL_PROVIDER` plus the
provider-specific vars from `references/providers.md`. Every provider
implementation ships inside the runner — switching providers is env-only, no
code change.

Invoke either way:

```bash
python -m eval.llm_eval_runner     # package module
python eval/llm_eval_runner.py     # direct script path
```

Raw-HTTP provider paths deliberately use stdlib `urllib` — no `requests`, no
`httpx` — so the dependency footprint stays at pytest.

### Runtime knobs

Env knobs deliberately mirror the sibling TypeScript runner, so a repo hosting
both harnesses configures them once. The knobs cover:

| Knob | Effect |
|---|---|
| Skill filter | Restrict the run to one skill. |
| Case filter | Restrict to a single eval case. |
| Repeat count | Runs per case. |
| Pass threshold | Minimum grade to count a case as passing. |
| Max tokens | Cap on generation length. |
| Concurrency | Worker-pool size; default 6. |
| Report directory | Where run reports land. |
| Report suppression flag | Skip writing report output. |

Concurrency model: the runner fans `cases x repeats` work units across a
thread pool (size env-tunable, default 6). Assertions **within** each unit are
graded sequentially by design — nesting a second pool inside the workers is
what deadlocks, so don't "optimize" that.

### Baseline mode

An env flag switches the runner into A/B baseline comparison: each assertion
is checked for discrimination between the skill-present and skill-absent runs,
and assertions that fail to discriminate are flagged. The margin is
configurable, defaulting to `0.25`. A stricter bare-baseline flag additionally
strips reference docs from the baseline side — use it for documentation-heavy
skills where the references alone might carry the eval. Semantics are
documented in `spec-format.md`.

## Quick decision table

| Situation | Do |
|---|---|
| Repo already has an evals dir | Use it; skip the `eval/` default. |
| `pip install` refused (PEP 668) | venv, git-ignore `.venv/`. |
| OpenAI-compatible provider | No SDK install at all. |
| Skills outside `.claude/` | `SKILLS_ROOT` env override first; synchronized code edit only as fallback. |
| Repo coverage tests red before specs exist | Expected. Author specs, rerun. |

## Related documents

- `references/providers.md` — provider selection, packages, credential vars.
- `spec-format.md` — `evals.json` authoring, assertion and baseline semantics.
- TypeScript harness reference (sibling) — same knob set, different runtime.
