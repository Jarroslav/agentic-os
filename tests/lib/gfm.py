"""GFM table primitives shared by the registry/index integrity checks.

GitHub only recognises a table when a header row is followed *immediately* by a
delimiter row (`| --- | --- |`) whose cell count matches the header's. Any
pipe-delimited line outside such a block renders as literal paragraph text
(`<p>| ... |</p>`), not a row — so an appended row, or a marker written as a bare
`<!-- comment -->` line, silently falls out of the table. These helpers detect the
valid blocks and validate that a marker sits inside its table as a real row.

Used by `check-registry.py` (agent-registry.md) and `check-patterns.py`
(PATTERNS.md) so both enforce the same GFM semantics from one implementation.
"""
import re

DELIM_CELL = re.compile(r"^:?-+:?$")


def cells(line):
    """Cells of a pipe row, ignoring the optional leading/trailing pipe."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def is_row(line):
    return line.lstrip().startswith("|")


def find_blocks(lines):
    """Every valid GFM table block as (start, end) inclusive line indices.

    A block is a header row + a matching-cell-count delimiter row + the run of
    consecutive pipe lines that follows.
    """
    blocks = []
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
    return blocks


def validate_marker_table(lines, header_cell, marker):
    """Return an error string, or None if the marker/table invariant holds.

    Checks, in order: the table whose header's first cell is `header_cell` is a
    valid GFM block; `marker` appears exactly once and as a real table row (never a
    bare comment line, which terminates the table); that row is inside the block;
    and no pipe line lies outside every valid block.
    """
    blocks = find_blocks(lines)
    in_a_block = {n for start, end in blocks for n in range(start, end + 1)}

    table = next((b for b in blocks if cells(lines[b[0]])[0] == header_cell), None)
    if table is None:
        stray = next((n for n, l in enumerate(lines)
                      if is_row(l) and cells(l)[0] == header_cell), None)
        if stray is not None:
            return ("table header at line %d is not followed by a valid `| --- |` "
                    "delimiter row with a matching cell count — GFM renders the whole "
                    "table as paragraph text" % (stray + 1))
        return "no table header row (first cell %r)" % header_cell

    bare = next((n for n, l in enumerate(lines)
                 if marker in l and not is_row(l) and l.strip().startswith(marker)), None)
    if bare is not None:
        return ("marker at line %d is not a table row — a bare comment line "
                "terminates the GFM table, so appended rows render as paragraph text"
                % (bare + 1))

    marker_rows = [n for n in range(len(lines))
                   if is_row(lines[n]) and cells(lines[n])[0] == marker]
    if len(marker_rows) != 1:
        return ("expected exactly 1 marker row (`%s` as its first cell), found %d"
                % (marker, len(marker_rows)))
    if not table[0] <= marker_rows[0] <= table[1]:
        return ("marker row (line %d) is outside the table block (lines %d-%d)"
                % (marker_rows[0] + 1, table[0] + 1, table[1] + 1))

    for n, line in enumerate(lines):
        if is_row(line) and n not in in_a_block:
            return "orphaned table row outside any table block (line %d): %s" % (
                n + 1, line[:60])
    return None
