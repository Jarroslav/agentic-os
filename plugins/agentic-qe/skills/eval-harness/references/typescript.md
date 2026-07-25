# TypeScript harness installation

Install the skill-eval harness into a target repo: copy templates, wire dependencies and scripts, configure environment, verify. Blast radius: installation is R2 (writes repo files); eval runs are R1 (writes run artifacts under `.cache/`).

This doc covers installation only. For provider choice and its env vars, see the providers reference. For the per-skill spec schema and baseline/discrimination semantics, see the spec-format reference. All templates come from this skill's `assets/typescript/` directory.

## Defaults at a glance

| Setting | Default |
| --- | --- |
| Harness directory | `eval/` at repo root |
| Skills discovery root | `<repoRoot>/.claude` |
| Pass threshold | 0.5 |
| Discrimination margin | 0.25 |
| Minimum Node | 18 |
| Report output | `.cache/eval-reports/` |

## Prerequisites

- Node 18 or newer. The judge runner uses global `fetch` and Node's experimental type-stripping flag to execute `.ts`/`.mts` sources directly — there is no build step, and older Node lacks both.
- A repo that hosts agent skills under a discoverable root (default `<repoRoot>/.claude`).
- The host `package.json` does not need `"type": "module"`. The runner is an `.mts` file, and Vitest resolves module format for the test files on its own.

## Step 1 — Pick the harness directory

Check for an existing evaluation/test-harness convention in the repo. If one exists, use it. Otherwise create `eval/` at the repo root.

> Respecting an existing convention keeps the harness discoverable by the people and tooling already working in the repo; `eval/` is only the fallback.

## Step 2 — Copy the templates

Six templates ship with this skill. Copy five into the harness directory; the sixth is reference-only.

| Template | Role | Copy? |
| --- | --- | --- |
| Contract-validation module | Skill discovery, frontmatter parsing, schema and script checks | Yes |
| Vitest unit tests | Exercises the validation primitives themselves | Yes |
| Vitest all-skills suite | Runs every discovered skill against its declared contract | Yes |
| LLM-judge runner (`.mts`) | Multi-provider run → grade → repeat loop | Yes |
| TypeScript config | Strict compiler settings, Node16 module resolution, scoped to the harness dir | Yes |
| Sample spec JSON | Shape reference for authoring each skill's own `eval/evals.json` | No — never copy into the harness dir |

> The sample spec exists so you can see the expected shape while writing a skill's spec. Copying it into the harness would make a fake spec discoverable as if it were real.

## Step 3 — Install dependencies

Dev dependencies:

```sh
npm install -D typescript vitest @types/node
```

Runtime dependency:

```sh
npm install dotenv
```

Provider SDKs — install only what the chosen provider path needs:

| Provider path | SDK to install |
| --- | --- |
| Gateway-routed Anthropic | The gateway SDK |
| Native Anthropic | The official Anthropic SDK |
| OpenAI-compatible endpoint | None — the runner uses plain `fetch` |

All provider implementations already ship inside the runner; selecting one is configuration, not code (see Step 5).

## Step 4 — Add npm scripts

Wire three scripts in the host `package.json`:

1. Single-run contract tests — invoke `vitest run` against the harness dir.
2. Watch-mode contract tests — same suite via `vitest` in watch mode.
3. LLM evals — invoke the judge runner with `node` and the type-stripping flag, e.g. `node --experimental-strip-types eval/<runner>.mts` (adjust the path to your harness dir).

## Step 5 — Wire the environment

1. Create `.env.example` listing the provider variable names with placeholder values only — never real credentials.
2. Ensure `.gitignore` covers `.env`, `node_modules/`, and `.cache/`.
3. To run LLM evals, create a local `.env` with `EVAL_PROVIDER` plus that provider's variables (names and semantics in the providers reference).

The contract-test layer needs no credentials at all. Only the judge runner reads `.env`.

## Step 6 — Point discovery at your skills

Both the validation module and the judge runner discover skills under `<repoRoot>/.claude` by default. If your skills live elsewhere:

- Preferred: set `SKILLS_ROOT` in the environment. It resolves against the repo root.
- Fallback: edit the default constant — but it exists in **both** files, and the two copies must stay identical.

> An env override is one line of config; an edited constant is two files that can silently drift apart. Prefer the override.

## Step 7 — Verify

Run checks in this order:

1. `node --version` — confirm 18+.
2. Run the single-run test script. The validation-primitive unit tests must pass with no credentials configured.
3. Expect the all-skills contract suite to **fail while zero skills carry a spec**. This is by design: the suite refuses to pass on an empty discovery result, forcing you to author at least one per-skill `eval/evals.json` (schema in the spec-format reference) before the gate can go green.
4. After the first spec exists, rerun the contract suite — it should now execute that skill's contract checks.
5. With `.env` populated, run the LLM-eval script and confirm a report lands in `.cache/eval-reports/`. Read `latest.md` there for the summary.

## Judge-runner tuning

All knobs are environment variables; none require code changes.

| Variable | Effect |
| --- | --- |
| `SKILL` | Restrict the run to one skill |
| `ONLY_CASE` | Restrict the run to one case |
| `REPEATS` | Runs per case |
| `PASS_THRESHOLD` | Minimum score to pass (default 0.5) |
| `MAX_TOKENS` | Cap on generation length |
| `CONCURRENCY` | Parallel case execution |

### Baseline A/B mode

| Variable | Effect |
| --- | --- |
| `BASELINE=1` | Rerun each case with the skill instruction file removed, to flag assertions that pass regardless of the skill |
| `DISCRIMINATION_MARGIN` | Required score gap between skill and baseline runs (default 0.25) |
| `BASELINE_BARE=1` | Also strip reference docs from the baseline — use for documentation-heavy skills |

> A case that scores the same with and without the skill measures the model, not the skill. Baseline mode exposes those cases so you can tighten them.

## Out of scope

- Spec JSON schema — spec-format reference.
- Provider comparison and selection guidance — providers reference.
- Non-TypeScript harnesses and CI wiring.
