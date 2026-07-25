# Calibration examples — XS

Totals of 6–9. Nearly every dimension sits at 1, and the work has no real
unknown left in it by the time it is written down.

Drop further XS examples into this directory as separate files; nothing indexes
them.

---

## Example: Add an optional field to an existing run-artifact schema

**Ticket:** PROJ-4180
**Sized:** XS (7/36)
**Actually:** XS — merged the same afternoon

| Dimension             | Label | Score | Evidence |
|-----------------------|-------|-------|----------|
| Component Scope       | XS    | 1     | One file: `references/schemas/complexity.schema.json` |
| Requirements Clarity  | XS    | 1     | Field name, type and optionality all stated in the ticket |
| Technical Risk        | XS    | 1     | Three sibling schemas already carry an optional string this way |
| File Change Estimate  | XS    | 1     | 1 file modified, 0 new — confirmed by grepping for readers of the schema |
| Dependencies          | XS    | 1     | None; the validator is already a dependency |
| Affected Layers       | S     | 2     | Schema plus the one skill that writes the artifact |
| **Total**             | XS    | 7/36  | |

**Why this size:** Optional and additive. Nothing already written becomes
invalid, so there is no migration and no compatibility question to answer.

**Calibration note:** The tell for XS is not "small diff" — it is *no open
question*. A one-line change with an undecided default belongs in S at least,
because the decision, not the edit, is the work.

---

## Example: Correct a stale command name in a skill's usage examples

**Ticket:** PROJ-4193
**Sized:** XS (6/36)
**Actually:** XS — under an hour

| Dimension             | Label | Score | Evidence |
|-----------------------|-------|-------|----------|
| Component Scope       | XS    | 1     | Documentation inside one skill directory |
| Requirements Clarity  | XS    | 1     | The correct name is unambiguous and already in use elsewhere |
| Technical Risk        | XS    | 1     | No executable path touched |
| File Change Estimate  | XS    | 1     | 2 files, both prose |
| Dependencies          | XS    | 1     | None |
| Affected Layers       | XS    | 1     | Docs only |
| **Total**             | XS    | 6/36  | |

**Why this size:** The floor of the scale. Six 1s is what a change looks like
when it carries no decision, no risk and no coupling.

**Calibration note:** A total of 6 should be rare enough to be worth a second
look. If several tickets a week score 6, the scorer is reading titles rather
than measuring.
