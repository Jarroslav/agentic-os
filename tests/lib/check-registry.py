#!/usr/bin/env python3
"""T1: agent-registry.md table integrity — the deterministic half of
agentic-doctor Check 8.

`.agentic/guides/agent-registry.md` is the routing matrix pipeline-orchestrator
reads to discover which agent owns which intent. It is a hybrid file: a static
curated table rendered at Phase 4, rows appended by Phase 5 step 6 immediately
below a marker row, and template output again below those (a closing paragraph
and the `## Orchestration rules` section).

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
Check 8e/8f (one row per generated contract; no stale rows) are vacuous here and
remain doctor's job. Phase 5 is model-driven and cannot run in a bash harness.

Usage: check-registry.py <TARGET_REPO>
"""
import sys
from pathlib import Path

from gfm import cells, is_row, validate_marker_table

REGISTRY = Path(sys.argv[1]) / ".agentic/guides/agent-registry.md"
MARKER = "<!-- generated-agent-rows -->"
HEADER_CELL = "Trigger / intent"


def fail(msg: str) -> None:
    print("  " + msg)
    sys.exit(1)


if not REGISTRY.exists():
    fail("agent-registry.md not scaffolded")

lines = REGISTRY.read_text(encoding="utf-8").splitlines()

# 8a-8d: the routing table is a valid GFM block, the marker is a real row inside
# it, and no pipe line is orphaned. Shared with check-patterns.py via gfm.py.
err = validate_marker_table(lines, HEADER_CELL, MARKER)
if err is not None:
    fail(err)

marker_line = next(n for n in range(len(lines))
                   if is_row(lines[n]) and cells(lines[n])[0] == MARKER)

# 8g: the tail below the marker's generated-row run survived. The template
# renders a closing paragraph and `## Orchestration rules` unconditionally, so an
# empty tail is never legitimate -- it means an /agentic-upgrade run under the old
# two-way split reconciliation truncated the file at the marker row. 8a-8d cannot
# see that: the marker row, the table block, and every generated row survive the
# truncation, and GitHub still renders a perfectly valid table.
j = marker_line + 1
while j < len(lines) and is_row(lines[j]):
    j += 1
tail = lines[j:]
if not tail:
    fail("file ends at the generated rows — no tail. An /agentic-upgrade under "
         "the old two-way split truncated it at the marker row")
if not any(l.startswith("## Orchestration rules") for l in tail):
    fail("tail below the marker row lost the `## Orchestration rules` section")

sys.exit(0)
