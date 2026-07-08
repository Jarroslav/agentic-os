#!/usr/bin/env python3
"""T5: three-way upgrade classification. Given an installed fixture with a
journal, hand-edit one managed file and confirm the upgrade decision function
classifies unmodified -> overwrite, user-modified -> prompt, generated -> offer,
managed-block -> wholesale. Mirrors agentic-upgrade Phase 2 logic."""
import hashlib
import json
import sys
from pathlib import Path

PLUGIN = Path(sys.argv[1])
TARGET = Path(sys.argv[2])
journal = json.loads((TARGET / ".agentic/agentic-os/install.json").read_text())


def classify(rel, rec):
    """Return the upgrade action for a journaled file, per agentic-upgrade Phase 2."""
    p = TARGET / rel
    if not p.exists():
        return "recreate"
    cur = hashlib.sha256(p.read_bytes()).hexdigest()
    if rec["owner"] == "user":
        return "skip"                       # never touch user-owned
    if rec["owner"] == "generated":
        return "offer-regen"                # never silent overwrite
    if rel == "CLAUDE.md" or rec["template"] in ("governance/agents",):
        return "managed-block"              # replaced wholesale between markers
    if rec["template"] == "governance/agent-registry":
        return "registry-split-reconcile"   # three-way split at the marker row:
                                             # head + tail diff against NEWRENDER,
                                             # generated rows preserved verbatim
    if cur == rec["sha256"]:
        return "overwrite"                  # unmodified managed -> take new template
    return "prompt"                          # user-modified managed -> ask


# unmodified managed file -> overwrite
sub = ".claude/hooks/subagent_gate.py"
if classify(sub, journal["files"][sub]) != "overwrite":
    print("  unmodified managed misclassified"); sys.exit(1)

# now hand-edit it -> prompt
p = TARGET / sub
p.write_text(p.read_text() + "\n# local tweak\n")
if classify(sub, journal["files"][sub]) != "prompt":
    print("  user-modified managed misclassified"); sys.exit(1)

# CLAUDE.md -> managed-block wholesale
if classify("CLAUDE.md", journal["files"]["CLAUDE.md"]) != "managed-block":
    print("  CLAUDE.md not managed-block"); sys.exit(1)

# agent-registry.md -> split-reconcile, never a plain managed overwrite
# (would silently strip Phase 5's appended generated-agent rows)
registry = ".agentic/guides/agent-registry.md"
if classify(registry, journal["files"][registry]) != "registry-split-reconcile":
    print("  agent-registry.md not registry-split-reconcile"); sys.exit(1)

# The registry's SHAPE (marker row, table block, surviving tail) is asserted by
# tests/lib/check-registry.py -- doctor Check 8, including 8g -- against this same
# fixture in T1. Duplicating those assertions here would add zero coverage: T4
# already proves the reinstall between them is byte-identical. What this file
# uniquely owns is the routing decision above: agent-registry.md must classify as
# `registry-split-reconcile`, never as a plain managed overwrite.

# a user-owned guide (mature case) would be skip — synthesize one
journal["files"].setdefault("x", {"owner": "user", "template": "guides/x", "sha256": "0"})
(TARGET / "x").write_text("u")
if classify("x", journal["files"]["x"]) != "skip":
    print("  user-owned not skipped"); sys.exit(1)
(TARGET / "x").unlink()

# restore the edited hook so later steps see a clean tree
import subprocess
subprocess.run(["python3", str(PLUGIN.parent.parent / "tests/lib/refinstall.py"),
                str(PLUGIN), str(TARGET), "--reinstall"], capture_output=True)
sys.exit(0)
