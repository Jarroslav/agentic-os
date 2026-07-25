# Triage & Verdict Assembly

The reduction step between lens analysis and the emitted review decision. Three
lens subagents produce heterogeneous output; this procedure folds them into one
consolidated finding set plus a single machine-readable verdict. Deterministic:
same inputs, same verdict.

> Scope note. This reference owns the fold logic only. The verdict JSON shape
> lives in `verdict-schema.md`; diff handling, round sequencing, and safe-fail
> live in `SKILL.md`; human escalation of `low` / `decision_needed` verdicts
> lives in `decision-router`. Do not re-derive those rules here.

## Inputs

| lens | source tag | raw format |
|---|---|---|
| blind | `blind` | Markdown bullets |
| edge-case | `edge` | JSON array |
| acceptance | `acceptance` | criterion-status list |
| standards | `standards` | violated-standard entries |

- **Full mode** — a spec/story was available and the acceptance lens ran.
- **No-spec mode** — the acceptance lens did not run (no spec/story present).

## The pipeline (fixed 5-step order)

Run these in order. Nothing is discarded after Step 4. Severity exists only
after Step 5.

1. **Normalize** — coerce every raw item into a candidate finding carrying the
   five required fields (`title`, `problem`, `impact`, `recommendation`, plus
   `file`/`line`). Synthesize any field a source does not emit.
2. **Deduplicate** — collapse candidates that describe the same defect,
   combining source tags.
3. **Classify** — assign exactly one bucket (`decision_needed`, `patch`,
   `defer`, `dismiss`) to each surviving candidate.
4. **Drop dismissed** — remove `dismiss`-bucket candidates from the emitted set.
   This is the only place findings leave the set.
5. **Assign severity + assemble** — set `critical | major` on each emitted
   finding, number IDs, and build the verdict object.

> Conservative-tie rule. Whenever a call is genuinely uncertain — which bucket,
> which severity, whether something is a finding at all — choose the more severe
> / less dismissive option. Ties never resolve toward `approve`.

## Step 1 — Normalize

Every emitted finding needs five fields. No single lens supplies all of them;
synthesize the rest here.

- `title` — a short phrase (~≤8 words) summarizing `problem`. Synthesize it the
  same way for every source. **Never blank.**
- Missing/unparseable location never drops a finding. Set `file` to the best
  available reference, or the literal `"unknown"`, and omit the optional `line`.

### Per-source field mapping

| source | file/line from | problem | impact | recommendation |
|---|---|---|---|---|
| `blind` | parse file/hunk ref from the bullet | bullet text | synthesized, severity-aligned | fix implied by the bullet, else `investigate <location>` |
| `edge` | `location` | `trigger_condition` | `potential_consequence` | `guard_snippet` |
| `acceptance` | cited evidence | unmet criterion + actual behavior | effect of shipping it unmet | implement/correct the criterion |
| `standards` | file/commit the check cites | violated standard + actual code/commit | why the violation blocks the workflow | conform to the documented standard |

The edge-case JSON object field names consumed here are exactly `location`,
`trigger_condition`, `potential_consequence`, `guard_snippet`.

### Acceptance lens is not a findings source

The criterion-status list maps to `business_review[]`, not to `findings[]`.
Only its `fail` and `partial` bullets additionally become findings. A `partial`
is treated exactly like a `fail` everywhere downstream — severity, decision,
standards. A required criterion mislabeled `na` is treated as `fail` for the
decision rule.

### Empty-lens sentinels → zero findings

Recognize these; never leak them as bogus findings.

| lens | sentinel | meaning |
|---|---|---|
| blind | `No blocking concerns found in the changed lines.` | zero findings |
| edge | `[]` | zero findings |
| edge | single object with `location` `"N/A"` | not a real finding — input was empty/undecodable |
| acceptance | empty status array with the "no criteria" note | zero findings **and** treat the round as no-spec |

Caveat: an edge `"N/A"` returned against a **non-empty** diff means the lens
failed, not that it found nothing — carry no finding but lower confidence.

## Step 2 — Deduplicate

Collapse candidates describing the same defect. Combine their source tags with
`+`, e.g. `blind+edge`. On merge, take the **most-blocking** bucket any
contributor warrants:

```
decision_needed / patch  >  defer  >  dismiss
```

> A newly-introduced defect must never inherit a weaker `defer` bucket through a
> merge. Blocking always wins the tie.

## Step 3 — Classify into buckets

Exactly one bucket per finding.

| bucket | when | emitted in `findings[]`? |
|---|---|---|
| `decision_needed` | needs a human judgment call; **requires a spec (full mode only)** | yes |
| `patch` | fixable defect this change should resolve now | yes |
| `defer` | genuine issue, but out of scope for this change | no |
| `dismiss` | below the emission floor and not made blocking by any rule | no |

### Emission floor

Cosmetic, trivial, or purely stylistic items sit below the floor and go to
`dismiss` **unless** a documented project standard makes them blocking. A
would-be-minor finding that a documented standard turns blocking is classified
`patch` and later scored `major` — it is never `dismiss`ed.

### No-spec mode — `decision_needed` is unavailable

There is no spec to arbitrate against, so never emit `decision_needed`. Route
instead:

- Unambiguous fix → `patch`.
- Genuinely pre-existing / out of scope → `defer`.
- Ambiguous **and** introduced by this change → keep it blocking as `patch`
  (severity `major`), state the ambiguity in `recommendation`, and lower
  `confidence`.

## Step 4 — Drop dismissed

Remove `dismiss` candidates. `defer` and `dismiss` survivors are **not** emitted
in `findings[]`. Record their counts in `rationale`, plus a one-line note per
`defer`. A `defer` finding never forces `request-changes` — by definition it is
out of scope for the change.

## Step 5 — Severity, IDs, and verdict

### Severity (independent of bucket)

Severity has only two values. There is no `minor` slot — sub-floor items were
already dismissed at Step 3, not carried here and dropped.

| severity | assign when |
|---|---|
| `critical` | security issue, data loss, broken runtime path, public/data-contract breakage, or missing required behavior (`fail`/`partial` on a required criterion/requirement) |
| `major` | real bug, meaningful test gap, fragile implementation, or significant project-standard violation |

Standards-sourced findings default to `major`, or `critical` when the violation
is a security issue.

### Finding IDs

Format `CR-001`, `CR-002`, … numbered in stable order. On a `code-review.check`
re-review round, **reuse the original IDs — never renumber.**

Canonical total sort key for numbering:

1. `file` ascending — missing / `"unknown"` sorts **last**.
2. `line` ascending when present — a finding **with** a line sorts before one
   **without** within the same file.
3. `title` ascending — final tie-breaker.

### `triage` field

Emitted findings may carry an optional `triage` value of `patch` or
`decision_needed`, mirroring the surviving bucket.

### risk_flags

| flag | covers |
|---|---|
| `security` | auth / secrets / injection / unsafe-IO |
| `breaking-change` | behavior or build/runtime regression |
| `public-api` | exported-signature or data-contract change |

Carry through any flags already present on the bundle.

## Decision

Set `decision` to `request-changes` if **any** condition holds; otherwise
`approve`.

- A surviving `patch` finding is `critical` or `major`; or
- Any `decision_needed` finding exists; or
- Any `fail`/`partial` on a required story criterion or spec requirement (`na`
  on a clearly required criterion counts as `fail`); or
- Any concrete security issue; or
- Any blocking `standards_review` `fail`/`partial`; or
- The review could not run — every applicable lens failed / no usable output.
  Then also force `confidence: low` and **never** `approve`.

## Confidence

| confidence | when |
|---|---|
| `high` | all three lenses ran with parseable output, spec/story present, no `decision_needed` remains |
| `medium` | every lens ran but one returned thin-but-parseable results, no unresolved ambiguity |
| `low` | genuine no-spec round; a lens failed outright; diff too large; incomplete bundle; **or** ≥1 `decision_needed` remains |

> An acceptance lens failing **while a spec was present** is a broken audit, not
> a clean no-spec round — that is `low`, not the ordinary no-spec case.

> `low` confidence is the only mechanism that escalates ambiguity — there is no
> ambiguity `risk_flag`. Any `decision_needed` must force `low` so the
> `decision-router` routes the verdict to a human.

## Verdict fields, at a glance

`findings[]`, `business_review[]`, `standards_review[]`, `risk_flags`,
`decision`, `confidence`, `rationale`, and per-finding `triage`, `file`, `line`.
Enums: severity `critical | major`; decision `request-changes | approve`;
confidence `high | medium | low`. Authoritative shapes: `verdict-schema.md`.

## Non-goals

- Does not define lens internals or how each lens produces its raw output.
- Does not define the verdict JSON schema (see `verdict-schema.md`).
- Does not cover diff handling, round sequencing, or safe-fail (see `SKILL.md`).
- Does not define human-escalation routing (see `decision-router`).
- Produces no `minor` severity and emits no non-blocking finding in `findings[]`.
