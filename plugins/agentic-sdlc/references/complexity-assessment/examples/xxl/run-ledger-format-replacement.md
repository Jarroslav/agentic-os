# Calibration examples — XXL

Totals of 32–36. Splitting is mandatory: no planning skill runs until the user
brings back decomposed stories. Conflicting expectations, discovery needed
before anything else, effects that cannot be undone.

Drop further XXL examples into this directory as separate files; nothing indexes
them.

---

## Example: Replace the run-ledger format everything downstream reads

**Ticket:** PROJ-4310
**Sized:** XXL (33/36)
**Actually:** never started as one story — decomposed into five

| Dimension             | Label | Score | Evidence |
|-----------------------|-------|-------|----------|
| Component Scope       | XXL   | 6     | Both orchestrators, every phase skill, the router, the status skill, and the schemas |
| Requirements Clarity  | XL    | 5     | Two incompatible proposals on the table; no decision on whether old runs stay readable |
| Technical Risk        | XXL   | 6     | Runs in flight during the change have no defined behaviour; a half-migrated ledger is unreadable |
| File Change Estimate  | XL    | 5     | 20+ files across three plugin trees, plus every schema and fixture |
| Dependencies          | S     | 2     | None — which is exactly why the score must not be padded |
| Affected Layers       | XXL   | 6     | Every layer that records or reads run state, plus the published server |
| **Total**             | XXL   | 33/36 | |

**Why this size:** An undecided compatibility story on top of a format change
that cannot be half-applied. The discovery has to happen before an estimate means
anything.

**Calibration note:** Two things worth carrying forward. First, Dependencies
scored 2 while five other dimensions scored 5 or 6 — resist the pull to average;
the low score is true and says something real about where the difficulty is not.
Second, "runs in flight have no defined behaviour" is the sentence that makes this
XXL rather than XL: an irreversible, mid-flight failure mode is not a risk to
manage, it is a decision to make first.

---

## Example: Split delivery-lifecycle guidance into a separate installable plugin

**Ticket:** PROJ-4322
**Sized:** XXL (32/36)
**Actually:** decomposed into four stories; three shipped, the fourth was dropped

| Dimension             | Label | Score | Evidence |
|-----------------------|-------|-------|----------|
| Component Scope       | XXL   | 6     | A new plugin tree, the marketplace manifest, the installer, and the served index |
| Requirements Clarity  | XXL   | 6     | Which guidance moves and which stays was contested throughout scoring |
| Technical Risk        | XL    | 5     | Existing installs must keep working across the split; the boundary is guesswork until drawn |
| File Change Estimate  | XL    | 5     | 30+ files moved or created; the count itself depended on the undecided boundary |
| Dependencies          | L     | 4     | A cross-plugin dependency declaration that did not exist yet |
| Affected Layers       | M     | 3     | Fewer than it looks: packaging and install, not the runtime |
| **Total**             | XXL   | 32/36 | |

**Why this size:** Both clarity dimensions at the ceiling. When the scope
boundary is the thing under dispute, no other estimate can be trusted — including
the file count, which visibly depends on it.

**Calibration note:** Affected Layers came in at 3, well below its neighbours,
and that is the useful detail: this was a packaging problem wearing an
architecture problem's clothes. Dropping the fourth story cost nothing at
runtime — which the low Affected Layers score predicted and the high total did
not.
