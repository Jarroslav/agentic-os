#!/usr/bin/env python3
"""T1: PATTERNS.md guide-index integrity.

`PATTERNS.md` is the index agents read to find the canonical guide for a domain.
Its guide table carries a `<!-- generated-guide-rows -->` marker row where Phase 5
appends one row per generated stack guide (data/api/development/architecture).

If that marker is a bare comment line instead of a real table row, it terminates
the GFM table and the appended rows render as paragraph text — the same silent
failure the agent-registry marker had. This asserts the same invariant here, from
the shared `gfm.py`, on the Phase-4 scaffold (Phase 5's model-driven append can't
run in a bash harness — this guarantees the append *point* is sound).

Usage: check-patterns.py <TARGET_REPO>
"""
import sys
from pathlib import Path

from gfm import cells, is_row, validate_marker_table

PATTERNS = Path(sys.argv[1]) / "PATTERNS.md"
HEADER_CELL = "Domain"
MARKER = "<!-- generated-guide-rows -->"
TAIL_HEADING = "## How to propose a change"

if not PATTERNS.exists():
    print("  PATTERNS.md not scaffolded")
    sys.exit(1)

lines = PATTERNS.read_text(encoding="utf-8").splitlines()
err = validate_marker_table(lines, HEADER_CELL, MARKER)
if err is not None:
    print("  " + err)
    sys.exit(1)

# Tail survival (the analogue of check-registry's 8g). PATTERNS regenerates its
# generated rows rather than preserving them across a split, so it has no legacy
# two-way-split truncation history — but a future upgrade bug that truncated the
# file at the generated-row run would silently drop the `## How to propose a change`
# section, which validate_marker_table cannot see (marker row + table stay valid).
marker_line = next(n for n in range(len(lines))
                   if is_row(lines[n]) and cells(lines[n])[0] == MARKER)
j = marker_line + 1
while j < len(lines) and is_row(lines[j]):
    j += 1
if not any(l.startswith(TAIL_HEADING) for l in lines[j:]):
    print("  tail below the generated-guide rows lost the %r section — the file "
          "was truncated at the marker's row run" % TAIL_HEADING)
    sys.exit(1)
sys.exit(0)
