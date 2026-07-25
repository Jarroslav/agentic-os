# Per-lens output formats for review findings

Each review lens emits a fixed, machine-parseable shape so `code-review-orchestrator`
can parse and triage findings deterministically. This document is the format contract
for the three lens variants — nothing else.

> A lens reports what it sees; it never rates what it found. Severity, priority, and
> ranking belong to the orchestrator. Emit findings, not judgments about their weight.

## Universal rules

- Run exactly **one** lens per pass. Emit **only** that lens's format.
- No preamble, no trailing commentary, no prose framing around the output.
- Never assign severity, score, or priority — that is the orchestrator's job.
- Every location references the diff. Precision order: prefer `file:line-range`, fall
  back to `file:line`, then `file:hunk` when the exact line is not visible.
- Each lens has a defined output for the empty / degenerate case (nothing found, or no
  usable input). Return the sentinel exactly as specified.

## Lens catalog

| lens id | format | empty-case sentinel |
|---|---|---|
| blind | Markdown bullets | "No blocking concerns found in the changed lines." |
| edge-case | JSON array (4 fixed fields) | `[]` valid; N/A object for empty/undecodable input |
| acceptance | JSON status array + Markdown findings bullets | `[]` array + one "no criteria" bullet |

Anchors the orchestrator resolves against:

- `blind` → `#lens--blind` — Markdown bullets
- `edge-case` → `#lens--edge-case` — JSON array
- `acceptance` → `#lens--acceptance` — criterion-status list + findings list

---

## lens = blind {#lens--blind}

**Output:** a Markdown bullet list — one concern per bullet. Each bullet states the
concern and its location (file, plus hunk or line).

Use this lens for open-ended inspection of the changed lines with no external checklist.

When nothing blocking is found, return exactly:

```markdown
No blocking concerns found in the changed lines.
```

---

## lens = edge-case {#lens--edge-case}

**Output:** a single JSON array. Each object carries **exactly** these four fields and
nothing else:

| field | content |
|---|---|
| `location` | diff reference — `file:line-range`, else `file:line`, else `file:hunk` |
| `trigger_condition` | what state or input exposes the gap (max ~15 words) |
| `guard_snippet` | minimal single-line code sketch that closes the gap |
| `potential_consequence` | what breaks if unguarded (max ~15 words) |

String rules: single-line, escaped — no raw newlines, no unescaped quotes.

An empty array `[]` is a valid result (no edge cases identified).

When the input is empty or cannot be decoded, return this sentinel verbatim:

```json
[{"location":"N/A","trigger_condition":"Input empty or undecodable","guard_snippet":"Provide valid content to review","potential_consequence":"Review skipped — no analysis performed"}]
```

---

## lens = acceptance {#lens--acceptance}

**Output:** two fenced blocks, in this order.

### Block 1 — Criterion status

A JSON array, one row per criterion. This block becomes the orchestrator's
"business review". Each object:

| field | content |
|---|---|
| `kind` | `story-ac` (criterion from a story's acceptance criteria) or `spec` (from a spec/design requirement) |
| `item` | the criterion text or identifier |
| `status` | `pass`, `fail`, `partial`, or `na` |
| `notes` | brief supporting note |

Status selection:

- A **required** criterion with no implementing change is `fail` (not implemented) —
  **not** `na`.
- Use `na` only when the criterion is genuinely not applicable to this change.

### Block 2 — Findings

Markdown bullets, one per `fail` or `partial` row. Each bullet cites the violated
criterion and the diff evidence. Omit `pass` and `na` rows — they produce no bullet.

### No-criteria case

When no acceptance criteria are available, return an empty status array `[]` for
Block 1, plus a single Block 2 bullet noting that acceptance review was not possible
without criteria.

---

## Schema key registry (verbatim)

Parsers depend on these exact keys and enum values.

- edge-case object keys: `location`, `trigger_condition`, `guard_snippet`, `potential_consequence`
- acceptance status object keys: `kind`, `item`, `status`, `notes`
- enum `kind`: `story-ac` | `spec`
- enum `status`: `pass` | `fail` | `partial` | `na`

## Boundaries

- Input to every lens is a code diff, referenced by file + hunk/line.
- The acceptance lens draws its criteria from external story acceptance criteria and
  spec/design requirements; it does not invent criteria.
- Lenses do not merge, rank, or triage findings, and do not define how a diff is
  obtained or how a lens is dispatched. Those concerns live in `code-review-orchestrator`.
