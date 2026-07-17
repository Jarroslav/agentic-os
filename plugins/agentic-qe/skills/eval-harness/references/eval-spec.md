# Eval spec format: the `evals.json` contract

One JSON file per skill, stored under the skill's eval subdirectory. Two harnesses consume the same file:

| Layer | Consumes | Verdict style |
|-------|----------|---------------|
| Code layer | `contract` block | Deterministic pass/fail per check |
| Judge layer | `cases` array + `context_files` | LLM grades each assertion PASS/FAIL |

Which language the harness happens to be written in (TypeScript or Python) does not change the format — both runners parse the identical schema. Sibling references in this directory cover the runners themselves; this document covers only the spec file.

Blast radius: everything the spec triggers is R0 (reads) except script smoke runs, which execute code — keep smoke invocations side-effect free (R0/R1 at most; never point a smoke run at anything with external effects).

---

## Checks you get for free

Every discovered skill is checked even with no spec entry at all:

| Universal check | Rule |
|-----------------|------|
| Manifest present | The skill's manifest file must exist |
| Name match | Frontmatter `name` must equal the directory name |
| Description | Must be non-empty |
| Manifest size | At most 500 lines |
| Description size | At most 1000 characters — block-scalar YAML descriptions are measured on the fully expanded text, not the source lines |

The two caps are plain constants at the top of the harness runner; adjust them per repo if your conventions differ.

---

## Top-level schema

```json
{
  "skill": "my-skill",
  "contract": { ... },
  "context_files": ["references/format.md"],
  "cases": [ ... ]
}
```

| Field | Required | Meaning |
|-------|----------|---------|
| `skill` | yes | Must match both the frontmatter name and the directory name |
| `contract` | yes | Structural checks for the code layer; at least one non-empty check |
| `context_files` | no | Files inlined into the run context of **every** behavioral case. A directory entry inlines short excerpts of each markdown file inside it |
| `cases` | no | Behavioral cases for the judge layer; omit or leave empty for contract-only skills |

A minimal valid spec is `skill` plus a `contract` with one required path and one load-bearing substring. It passes the code layer; the judge layer simply skips the skill.

> Start contract-only. Add behavioral cases once you know which guarantees the skill actually makes — cases written before the skill stabilizes grade noise.

---

## The `contract` block (code layer)

```json
{
  "require_paths": ["scripts/check.py", "references/format.md"],
  "manifest_contains": ["scripts/check.py", "NDJSON"],
  "manifest_matches": ["ask\\s+before\\s+overwrit"],
  "scripts": {
    "scripts/check.py": {
      "compile": true,
      "smoke": {
        "argv": ["--help"],
        "exit_codes": [0],
        "expect_output": ["usage:"]
      },
      "source_contains": ["def main("],
      "source_matches": ["argparse|click"]
    }
  }
}
```

| Sub-field | Semantics |
|-----------|-----------|
| `require_paths` | Paths that must exist. Pin **every** asset the skill depends on — a renamed script the manifest still references is the classic silent break |
| `manifest_contains` | Exact substrings the manifest must contain |
| `manifest_matches` | Case-insensitive regexes the manifest must match. Double the backslashes — the string passes through JSON first |
| `scripts` | Map keyed by script path; each value holds the per-script checks below |

Per-script checks:

| Check | Default | What it does |
|-------|---------|--------------|
| `compile` | on | Byte-compiles the file via the Python compile module |
| `smoke` | off | Runs the script with the given `argv`; asserts the exit code is in `exit_codes` (default: `[0]` only) and that each `expect_output` substring appears in combined stdout+stderr |
| `source_contains` | — | Exact substrings that must appear in the script source |
| `source_matches` | — | Regexes the script source must match |

Script checks always shell out to a Python interpreter, whichever language the harness itself is written in.

**Smoke runs and stdin.** The harness executes smoke runs with stdin closed and empty, so a CLI that reads stdin never hangs. The flip side: a script that *defaults* to consuming stdin sees immediate EOF and may exit 0 — which silently defeats a "running with no args should fail" check. For such scripts, smoke-test an explicitly invalid invocation or a help flag instead.

### Choosing substrings and regexes

- Pick substrings that are load-bearing: behavior-changing rules, filenames of invoked scripts, output-format markers. Never pin boilerplate.
- Switch to `manifest_matches` when the instruction matters but its wording legitimately varies.

> A contract that breaks on a harmless rewording trains people to ignore red runs. Every check should fail only when behavior actually changed.

---

## The `cases` array (judge layer)

Each case is one single-turn conversation: the candidate model gets the skill manifest, the inlined context, and the prompt — no tools, no follow-up turns, no file access.

```json
{
  "id": 3,
  "prompt": "Convert this record to the target format:\n{\"a\": 1}",
  "expected": "Emits the converted record and flags the missing field.",
  "context_files": [],
  "assertions": [
    {
      "name": "flags-missing-field",
      "check": "The response explicitly points out that the input lacks the required field rather than inventing a value for it."
    }
  ]
}
```

| Field | Semantics |
|-------|-----------|
| `id` | Numeric, unique within the skill. Enables single-case targeting via the `EVAL_CASE` env var |
| `prompt` | The literal user message. Inline any input the case needs — the candidate is single-turn and cannot fetch files |
| `expected` | Prose sketch of a good answer. **Report-only** — shown to humans reading results, never graded |
| `context_files` | Reference files inlined into this case only (usually empty; prefer the top-level list) |
| `assertions` | The graded checks — see below |

### Assertions

An assertion is a name/description pair:

- `name` — kebab-case, short; it is what you scan in the report.
- `check` — one plainly worded, objectively judgeable behavior. The judge reads the candidate's response and issues PASS or FAIL on that behavior alone.

Judge semantics you can rely on:

- **Intent counts.** Because the candidate has no tools, phrase file/tool assertions so that clearly declaring intent to perform the action passes ("says it will write the file to X" rather than "writes the file").
- **Paraphrase is equivalent.** Synonyms and rewording pass by default; do not demand exact phrasing unless the exact phrasing *is* the behavior (an output-format marker, a required token).

### Writing assertions that discriminate

| Rule | Why |
|------|-----|
| Target behavior the skill specifically enforces — a rule, a format, a safety gate, a fallback | An assertion any capable base model passes measures the model, not the skill, and gives false confidence |
| One behavior per assertion; split compound expectations | A FAIL on a compound assertion tells you nothing about which half broke |
| Aim each assertion at a specific failure mode: invented values (grounding violations), a skipped step, a wrong format | A FAIL then localizes the defect instead of just lowering a score |
| Prefer few strong cases: core happy path + the most important edge case (missing input, ambiguous request) before adding volume | Case count is run cost; discrimination is signal |

> Rough prior from experience: gating behaviors (asking before overwriting, refusing on missing input) discriminate well; universally easy outputs (producing valid JSON) almost never do.

---

## Baseline A/B: proving the eval measures the skill

Toggle with the `EVAL_BASELINE` env var. In baseline mode the harness reruns every case **without** the skill manifest, grades with the identical assertions, and reports three numbers per assertion:

| Column | Meaning |
|--------|---------|
| with-skill rate | Pass rate with the manifest present |
| baseline rate | Pass rate with the manifest stripped |
| delta | with-skill minus baseline |

An assertion is flagged **non-discriminating** when the baseline already clears the pass threshold *and* the skill's lift is below the discrimination margin (default `0.25`, a runner constant). The flag is eval-quality feedback only — it never changes the pass/fail gate, which is always the with-skill rate.

Baseline mode roughly doubles run-call volume. Leave it off in routine CI; turn it on when authoring or auditing a spec.

### Bare baseline

`EVAL_BASELINE=bare` (implies plain baseline mode) additionally strips the inlined reference docs from the baseline run. That measures "skill plus its bundled docs versus nothing."

Use it for doc-heavy skills. If the answers live in bundled reference docs, a plain baseline still inlines those docs on both sides and therefore only measures what the manifest *prose* adds over the docs — usually near zero, which falsely flags good assertions.

---

## Quick reference

Limits (constants at the top of the harness runner):

| Constant | Default |
|----------|---------|
| Manifest max lines | 500 |
| Description max chars | 1000 |
| Discrimination margin | 0.25 |
| Allowed smoke exit codes | `[0]` |

Env toggles:

| Variable | Effect |
|----------|--------|
| `EVAL_CASE=<id>` | Run a single behavioral case |
| `EVAL_BASELINE=1` | A/B baseline mode (no manifest in baseline run) |
| `EVAL_BASELINE=bare` | Bare baseline: also strips inlined reference docs; implies baseline mode |

Routing:

| Spec content | Consumed by |
|--------------|-------------|
| `contract` | Code layer |
| `cases`, `context_files` | Judge layer |

---

## Out of scope

This document defines field semantics only. It does not cover harness internals, CI wiring, or report rendering; it does not grade the `expected` prose; and it does not prescribe multi-turn or tool-using evaluation. Contract-only specs are fully valid — behavioral cases are optional, not a maturity requirement.
