# Calibration examples — XL

Totals of 27–31. Splitting is recommended and the recommendation should be
argued, not waved through. New abstractions, open architectural decisions, or a
rollback that is genuinely hard.

Drop further XL examples into this directory as separate files; nothing indexes
them.

---

## Example: Move served content from a build-time index to an incremental pipeline

**Ticket:** PROJ-4288
**Sized:** XL (29/36)
**Actually:** XL — split into three stories after the recommendation was accepted

| Dimension             | Label | Score | Evidence |
|-----------------------|-------|-------|----------|
| Component Scope       | XL    | 5     | Content builder, index format, server read path, drift check, packaging — and a new caching abstraction |
| Requirements Clarity  | L     | 4     | The goal was clear; invalidation semantics and the staleness window were open |
| Technical Risk        | XL    | 5     | The published package's behaviour changes; a wrong cache key serves stale content silently |
| File Change Estimate  | XL    | 5     | 12 modified, 5 new, spanning the server and the build scripts |
| Dependencies          | M     | 3     | One new well-known caching library under evaluation |
| Affected Layers       | XL    | 5     | Build, index, server, tests, CI, published artifact |
| **Total**             | XL    | 29/36 | |

**Why this size:** A silent failure mode plus an undecided invalidation model.
Either alone would be L; together they are why this does not start as one story.

**Calibration note:** "Silently serves the wrong thing" is the phrase that should
pin Technical Risk at 5. A loud failure is a bug report; a quiet one is a
correctness problem nobody opens a ticket for. Note also that Dependencies stayed
at 3 — one library under evaluation is not what made this XL, and inflating it to
match the neighbouring scores would have hidden the real driver.

---

## Example: Introduce a second delivery mode through the whole pipeline

**Ticket:** PROJ-4295
**Sized:** XL (27/36)
**Actually:** L — proceeded unsplit, five days, and it held

| Dimension             | Label | Score | Evidence |
|-----------------------|-------|-------|----------|
| Component Scope       | XL    | 5     | Every phase skill has to accept and honour the new mode |
| Requirements Clarity  | M     | 3     | Behaviour per phase was written down before scoring |
| Technical Risk        | L     | 4     | A mode that is honoured in some phases and not others fails confusingly |
| File Change Estimate  | XL    | 5     | 14 files, 2 new — counted across the phase skills |
| Dependencies          | S     | 2     | None |
| Affected Layers       | XXL   | 6     | Every phase, the router, the ledger, and both entry-point skills |
| **Total**             | XL    | 27/36 | |

**Why this size:** Reach. One idea touching every phase totals high even with
clear requirements and no new dependency.

**Calibration note:** This sat exactly on the 26/27 boundary, went up, and then
shipped unsplit inside the L cycle. That is evidence the boundary was rounded the
wrong way: with Requirements Clarity at 3 and a pattern the phases already shared,
the guide's own rule says round *down*. Worth remembering when the next
wide-but-well-specified change appears — breadth alone is not risk.
