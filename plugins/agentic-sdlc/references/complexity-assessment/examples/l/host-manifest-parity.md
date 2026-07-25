# Calibration examples — L

Totals of 21–26. Cross-cutting work, several unknowns, and usually a dimension
sitting at 4 or higher that the others cannot outvote.

Drop further L examples into this directory as separate files; nothing indexes
them.

---

## Example: Bring a second host's manifest flavour to parity across all plugins

**Ticket:** PROJ-4262
**Sized:** L (23/36)
**Actually:** L — five days

| Dimension             | Label | Score | Evidence |
|-----------------------|-------|-------|----------|
| Component Scope       | L     | 4     | Every plugin, its manifests, the version-sync check, and the packaging test |
| Requirements Clarity  | L     | 4     | The host's schema is documented unevenly; two fields had to be settled by experiment |
| Technical Risk        | M     | 3     | One flavour already exists to copy the structure from, but its quirks are undocumented |
| File Change Estimate  | L     | 4     | 3 new manifests, 6 modified, across 3 plugin trees — counted, not guessed |
| Dependencies          | S     | 2     | No packages; a new packaging step in CI |
| Affected Layers       | L     | 4     | Manifests, the sync check, packaging, CI, and the install path each host takes |
| **Total**             | L     | 23/36 | |

**Why this size:** Breadth rather than depth. No single file is hard; the change
has to land identically in three trees and stay that way, which is what the sync
check exists to enforce.

**Calibration note:** Requirements Clarity at 4 was the honest score and it was
worth arguing for. "Match the other host" reads as clear, but an
under-documented target schema means the acceptance criteria are not knowable
until you have tried it — that is a clarity problem, not a risk problem, and
scoring it in the wrong dimension would have hidden it.

---

## Example: Replace guessed file counts with a measured footprint across the sizing path

**Ticket:** PROJ-4271
**Sized:** L (21/36)
**Actually:** M — three days; the blast radius was smaller than scored

| Dimension             | Label | Score | Evidence |
|-----------------------|-------|-------|----------|
| Component Scope       | M     | 3     | The sizing agent, the guide, and the scoring skill |
| Requirements Clarity  | L     | 4     | "Measured, not guessed" was agreed in principle with no agreed mechanism |
| Technical Risk        | L     | 4     | Changing how scores are produced invalidates existing calibration examples |
| File Change Estimate  | M     | 3     | 5 files modified, 0 new |
| Dependencies          | XS    | 1     | None |
| Affected Layers       | L     | 4     | Agent, guide, skill, examples, and every future score's comparability |
| **Total**             | L     | 21/36 | |

**Why this size:** Two 4s that were genuinely there at scoring time — an
undecided mechanism and a change that reaches backwards into existing data.

**Calibration note:** It came in at M, and the reason is instructive rather than
embarrassing: the existing examples turned out to be re-scorable mechanically, so
Technical Risk resolved to 2 within the first hour. Scoring before that was known
was correct — you score the uncertainty you actually have, not the certainty
hindsight supplies. A 21 that lands as M is the boundary rule working, not a
scoring failure.
