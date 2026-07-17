# Verdict Schema — Code-Review Orchestrator

The orchestrator emits one verdict object per review round. It is a machine
hand-off, not user-facing prose: `decision-router` reads it, logs it, and routes
on it. Write it to disk; producing the file does **not** end the orchestrator's
turn.

> Turn-continuation is owned by the parent `SKILL.md` *Output* section.
> Persisting the verdict is a side effect of the round, not a stopping point.

## Where it lands

| Round | Round id | Output path |
|---|---|---|
| Full | `code-review.final` | `<run_dir>/code-review-final.json` |
| Check | `code-review.check` | `<run_dir>/code-review-check.json` |

- **Full round** — fresh lens fan-out, triage, verdict built from scratch.
- **Check round** — findings-only re-check of a fix-up diff. The full lens
  fan-out does **not** re-run. A narrow blind-spot + edge-case confirmation pass
  over the fix-up diff alone is permitted, but only to confirm or refute a
  *suspected-new* high-risk issue.

The check round takes the prior round's persisted object as its `prior_verdict`
input.

## Contract with the router

`decision-router` consumes exactly three fields: `decision`, `confidence`,
`risk_flags`. The remaining review fields (`rationale`, `business_review`,
`standards_review`, `findings`, `finding_status`) match the prior single-pass
review contract and are logged verbatim.

**The shape is frozen.** Do not rename a field; do not add a field. Older parsers
must keep working. The per-finding `triage` field is additive and optional — the
router ignores it.

## The object

```json
{
  "decision": "approve | request-changes",
  "rationale": "<1-3 sentences>",
  "confidence": "high | medium | low",
  "risk_flags": ["security", "breaking-change", "public-api"],
  "business_review": [
    { "kind": "story-ac | spec", "item": "<criterion or requirement>",
      "status": "pass | fail | partial | na", "notes": "<brief evidence>" }
  ],
  "standards_review": [
    { "kind": "commit-format | code-quality | security",
      "status": "pass | fail | partial | na", "notes": "<brief evidence>" }
  ],
  "findings": [
    { "id": "CR-001", "severity": "critical | major",
      "triage": "patch | decision_needed", "file": "path/to/file.ext",
      "line": 123, "title": "<short issue title>", "problem": "<what is wrong>",
      "impact": "<why it matters>", "recommendation": "<specific fix direction>" }
  ],
  "finding_status": [
    { "id": "CR-001", "status": "resolved | unresolved | superseded",
      "notes": "<only for code-review.check>" }
  ]
}
```

## Enums

| Field | Allowed values |
|---|---|
| `decision` | `approve`, `request-changes` |
| `confidence` | `high`, `medium`, `low` |
| `risk_flags` | `security`, `breaking-change`, `public-api` (plus any flag carried in the review bundle) |
| `severity` | `critical`, `major` |
| `triage` | `patch`, `decision_needed` (emitted); `defer`, `dismiss` (counted only) |
| `business_review.kind` | `story-ac`, `spec` |
| `standards_review.kind` | `commit-format`, `code-quality`, `security` |
| review `status` | `pass`, `fail`, `partial`, `na` |
| `finding_status.status` | `resolved`, `unresolved`, `superseded` |

## Triage buckets

Every raw finding lands in exactly one bucket. Only two of the four reach
`findings[]`:

| Bucket | Emitted as a `findings[]` object? | Effect on `decision` |
|---|---|---|
| `patch` | yes | forces `request-changes` when `critical`/`major` |
| `decision_needed` | yes | always forces `request-changes` |
| `defer` | no — counted in `rationale` only | never forces `request-changes` |
| `dismiss` | no — counted in `rationale` only | none |

Keep `findings[]` blocker-scoped. A downstream fix-up consumer (`sdlc-pipeline`)
must never be handed a pre-existing `defer` item to fix.

## Populating a full round (`code-review.final`)

Omit `finding_status` entirely. Build `business_review`, `standards_review`, and
`findings` fresh from the lens fan-out plus triage.

### decision

`request-changes` if **any** of these hold:

- a surviving `patch` finding is `critical` or `major`;
- any `decision_needed` finding exists;
- any required acceptance criterion is `fail` **or** `partial`;
- any concrete security issue is present;
- any blocking standards check is `fail` **or** `partial`.

Otherwise `approve`. `defer` findings never tip the decision.

### confidence

- **high** — all three lenses ran, a spec/story was present, and no
  `decision_needed` remains.
- **low** — any of: a `decision_needed` remains (the **only** ambiguity
  escalation — there is no ambiguity `risk_flag`); a lens failed; acceptance
  failed with a spec present; the diff was too large to review fully; or the
  round was genuinely no-spec.
- **medium** — every lens ran, but one returned thin-but-parseable results, with
  nothing left ambiguous.

### rationale

1–3 sentences. Name any failed lens, skipped acceptance (no-spec),
`decision_needed` items, the `defer` count with one-line notes, and the count of
`dismiss` findings filtered out.

### risk_flags

Derived from findings: `security`, `breaking-change`, `public-api`, plus any
flags carried in the review bundle.

### business_review / standards_review

`business_review` is the acceptance lens's per-criterion status list; empty when
there is no spec/story. `standards_review` is the orchestrator's standards and
security adjudication (`commit-format`, `code-quality`, `security`).

### findings

Triaged, deduplicated, blocking/actionable only: `severity` in
`{critical, major}`, `triage` in `{patch, decision_needed}`, stable `CR-NNN` ids.

- `file` is required. If no location is recoverable, use `"unknown"`.
- `line` is optional. Omit it when the lens gave no line (blind bullets,
  acceptance criteria, vague locations).

## Populating a check round (`code-review.check`)

Findings-only. Do not re-derive acceptance or standards — carry
`business_review` and `standards_review` forward from `prior_verdict` unchanged;
re-running those lenses is out of scope.

### finding_status

One entry per **original blocking** finding id (triage `patch` /
`decision_needed`) taken from `prior_verdict`. `defer` findings are not
re-checked and never produce a `finding_status` entry.

| Status | Meaning |
|---|---|
| `resolved` | the fix-up diff addresses the finding and evidence confirms it |
| `unresolved` | a **non-empty** fix-up diff leaves the finding present or untouched |
| `superseded` | the targeted code was deleted or rewritten, so the finding no longer applies — moot, not fixed-and-verified ("the location is gone") |

### findings (check round)

Populate `findings` only for **newly introduced** high-risk issues in the fix-up
diff (security, public API, data loss, build/runtime correctness); otherwise an
empty array. A new check-round finding gets a fresh, collision-safe id —
`max(existing CR number in prior_verdict.findings) + 1`, never reused or carried
forward — and `triage: "patch"`.

### decision (check round)

`request-changes` if **any** of these hold:

- `prior_verdict` is missing or unusable;
- any `finding_status` is `unresolved`;
- a new high-risk finding was added;
- a suspected-new high-risk issue could not be refuted (the confirmation pass
  did not run or did not clear it — an open high-risk suspicion is never
  auto-approved even when every original finding is `resolved`).

Otherwise `approve`. A `superseded` status does **not** block.

### confidence (check round)

- **high** — every original finding is `resolved` or `superseded` with clear
  fix-up evidence.
- **lower** — evidence is thin, or any status is uncertain.

## Safe-fail rules (check round)

Safe-fail when `prior_verdict` is absent, unreadable (a path-only ref you cannot
open), unparseable, or parsed but lacking a usable `findings[]`. Without a usable
prior verdict you do not know which findings to re-verify, so emit — **never** a
degraded `approve`:

- `decision: "request-changes"`
- `confidence: "low"`
- empty arrays for `business_review`, `standards_review`, `findings`,
  `finding_status`
- `rationale` naming the exact problem

An **empty fix-up diff** is also a safe-fail — do not fabricate `unresolved`
statuses for findings you never re-checked against a diff.

Two related guards:

- A prior finding carrying **no** `triage` is treated as blocking and
  re-checked — never skipped for a missing annotation.
- A `prior_verdict` whose `decision` is `request-changes` but which lists **no**
  blocking findings (e.g. a safe-fail final) leaves nothing to verify → keep
  `request-changes` / `confidence: low`; never read the empty set as "clean".

## Downstream

- `decision-router` — reads `decision` / `confidence` / `risk_flags`, logs the
  full object; does not depend on `triage`.
- `sdlc-pipeline` — the fix-up consumer; reads `findings[]`.
