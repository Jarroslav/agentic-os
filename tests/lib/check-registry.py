#!/usr/bin/env python3
"""T1: agent-registry.md table integrity — the deterministic half of
agentic-doctor Check 8.

`.agentic/guides/agent-registry.md` is the routing matrix pipeline-orchestrator
reads to discover which agent owns which intent. It is a hybrid file: a static
curated table rendered at Phase 4, plus rows appended by Phase 5 step 6 below a
marker row.

GFM only recognises a table when a header row is followed *immediately* by a
delimiter row (`| --- | --- |`) whose cell count matches the header's. Any
pipe-delimited line that is not part of such a block renders as literal
paragraph text (`<p>| ... |</p>`), not a row. Two consequences this asserts:

  * Drop or mangle the delimiter row and the WHOLE table silently becomes
    paragraphs — the orchestrator sees no agents at all. (Verified against
    GitHub's renderer: `<table>` count 0.)
  * Write the marker as a bare `<!-- comment -->` line instead of a real table
    row and it terminates the table, so Phase 5's appended rows land outside it
    — while the file still exists, still hashes correctly, and still contains
    the rows as text. Nothing else catches that.

Method: find every *valid* GFM table block (header + matching delimiter +
following pipe lines). A pipe-delimited line inside no valid block is an
orphaned row. This deliberately tolerates a second, unrelated table elsewhere in
the file (it forms its own valid block) while still catching a bare row appended
anywhere.

Scope: this runs on the Phase-4 scaffold, which has zero generated agents, so
Check 8d/8e (one row per generated contract; no stale rows) are vacuous here and
remain doctor's job. Phase 5 is model-driven and cannot run in a bash harness.

Usage: check-registry.py <TARGET_REPO>
"""
import re
import sys
from pathlib import Path

REGISTRY = Path(sys.argv[1]) / ".agentic/guides/agent-registry.md"
MARKER = "<!-- generated-agent-rows -->"
HEADER_CELL = "Trigger / intent"
DELIM_CELL = re.compile(r"^:?-+:?$")


def fail(msg: str) -> None:
    print("  " + msg)
    sys.exit(1)


def cells(line: str) -> list[str]:
    """Cells of a pipe row, ignoring the optional leading/trailing pipe."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def is_row(line: str) -> bool:
    return line.lstrip().startswith("|")


if not REGISTRY.exists():
    fail("agent-registry.md not scaffolded")

lines = REGISTRY.read_text(encoding="utf-8").splitlines()

# Every valid GFM table block: header row, a delimiter row whose cell count
# matches, then the run of consecutive pipe lines. Returns (start, end) inclusive.
blocks: list[tuple[int, int]] = []
i = 0
while i < len(lines):
    if is_row(lines[i]) and i + 1 < len(lines) and is_row(lines[i + 1]):
        header, delim = cells(lines[i]), cells(lines[i + 1])
        if len(header) == len(delim) and all(DELIM_CELL.match(c) for c in delim):
            j = i + 2
            while j < len(lines) and is_row(lines[j]):
                j += 1
            blocks.append((i, j - 1))
            i = j
            continue
    i += 1

in_a_block = {n for start, end in blocks for n in range(start, end + 1)}

# The routing table: the block whose header row's first cell is HEADER_CELL.
routing = next((b for b in blocks if cells(lines[b[0]])[0] == HEADER_CELL), None)
if routing is None:
    stray = next((n for n, l in enumerate(lines)
                  if is_row(l) and cells(l)[0] == HEADER_CELL), None)
    if stray is not None:
        fail("routing table header at line %d is not followed by a valid "
             "`| --- |` delimiter row with a matching cell count — GFM renders "
             "the entire table as paragraph text, so no agent is routable"
             % (stray + 1))
    fail("no routing-table header row (first cell %r)" % HEADER_CELL)

# 8a: the marker must exist exactly once, as a real table row (its first cell).
marker_rows = [n for n in range(len(lines))
               if is_row(lines[n]) and cells(lines[n])[0] == MARKER]
non_row_marker = next((n for n, l in enumerate(lines)
                       if MARKER in l and not is_row(l) and l.strip().startswith(MARKER)),
                      None)
if non_row_marker is not None:
    fail("marker at line %d is not a table row — a bare comment line terminates "
         "the GFM table, so appended rows render as paragraph text"
         % (non_row_marker + 1))
if len(marker_rows) != 1:
    fail("expected exactly 1 marker row (`%s` as its first cell), found %d"
         % (MARKER, len(marker_rows)))

# 8b: the marker row sits inside the routing table block.
if not routing[0] <= marker_rows[0] <= routing[1]:
    fail("marker row (line %d) is outside the routing table block (lines %d-%d)"
         % (marker_rows[0] + 1, routing[0] + 1, routing[1] + 1))

# 8c: no pipe-delimited line belongs to no valid table block.
for n, line in enumerate(lines):
    if is_row(line) and n not in in_a_block:
        fail("orphaned table row outside any table block (line %d): %s"
             % (n + 1, line[:60]))

sys.exit(0)
