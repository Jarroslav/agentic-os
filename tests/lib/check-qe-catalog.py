#!/usr/bin/env python3
"""Keep the QE blueprint index honest against the catalog on disk.

`qe-blueprints/SKILL.md` carries a hand-maintained "Blueprint index" table, and
the skill's own Step 1 tells the model to enumerate `references/catalog/**/*.md`
to pick a blueprint. Those are two sources for one fact. When they disagree the
failure is quiet and bad in both directions: a table row for a deleted file
sends the model after a blueprint that is not there, and a catalog file missing
from the table is invisible to anyone reading the skill.

Same posture as `mcp/content-index.json`: the derived view is allowed to exist,
but CI fails when it drifts from what it describes.

Deliberately not adding a generated manifest file. `mcp/src/tools/list_qe_blueprints.ts`
already derives `{id, stage, title, summary, uri}` from the catalog at build
time, and `check-presets.py` resolves preset entries by globbing it. A third
copy of the same data on disk would be one more thing to drift; this check
makes the copy that already exists trustworthy instead.

Usage: check-qe-catalog.py [PLUGIN_ROOT]   (default: plugins/agentic-qe)
Exit 0 clean, 1 on drift.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "plugins/agentic-qe"
SKILL = PLUGIN / "skills/qe-blueprints/SKILL.md"
CATALOG = PLUGIN / "skills/qe-blueprints/references/catalog"

# | analyze | `product-risk.md` | Assess product risk |
ROW = re.compile(r"^\|\s*([a-z]+)\s*\|\s*`([a-z0-9-]+\.md)`\s*\|\s*(.+?)\s*\|\s*$")

fail = 0

if not CATALOG.is_dir():
    print("  FAIL qe-catalog: no catalog at %s" % CATALOG)
    sys.exit(1)

on_disk = {p.name: p.parent.name for p in sorted(CATALOG.rglob("*.md"))}

in_table: dict[str, str] = {}
for line in SKILL.read_text(encoding="utf-8").splitlines():
    m = ROW.match(line)
    if not m:
        continue
    stage, fname, purpose = m.group(1), m.group(2), m.group(3)
    if fname in in_table:
        print("  FAIL qe-catalog: %s listed twice in the index table" % fname)
        fail = 1
    in_table[fname] = stage
    if not purpose:
        print("  FAIL qe-catalog: %s has an empty Purpose cell" % fname)
        fail = 1

for fname, stage in sorted(on_disk.items()):
    if fname not in in_table:
        print("  FAIL qe-catalog: %s/%s is on disk but missing from the index table"
              % (stage, fname))
        fail = 1
    elif in_table[fname] != stage:
        print("  FAIL qe-catalog: %s is under %s/ on disk but indexed as %s"
              % (fname, stage, in_table[fname]))
        fail = 1

for fname, stage in sorted(in_table.items()):
    if fname not in on_disk:
        print("  FAIL qe-catalog: index row %s (%s) points at a file that does not exist"
              % (fname, stage))
        fail = 1

if not fail:
    print("  ok   qe-catalog index matches the catalog (%d blueprints, %d stages)"
          % (len(on_disk), len(set(on_disk.values()))))
sys.exit(fail)
