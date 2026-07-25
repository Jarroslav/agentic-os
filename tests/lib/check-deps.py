#!/usr/bin/env python3
"""T6: dependency registration guard (agentic-init Phase 3). Simulate the
registration step against manifest/dependencies.json and assert: pinned
non-optional sources get extraKnownMarketplaces + enabledPlugins entries; any
source containing the OWNER/ placeholder is NOT registered but journaled as
pending-source-pin."""
import json
import sys
from pathlib import Path

PLUGIN = Path(sys.argv[1])
manifest = json.loads((PLUGIN / "manifest/dependencies.json").read_text())

settings = {}
follow_ups = []
for dep in manifest["plugins"]:
    if dep.get("optional"):
        continue
    src = dep["source"]
    repo = src.get("repo", "")
    if "OWNER/" in repo:
        follow_ups.append("pending-source-pin: %s" % dep["name"])
        continue
    settings.setdefault("extraKnownMarketplaces", {})[dep["marketplace"]] = src
    settings.setdefault("enabledPlugins", []).append("%s@%s" % (dep["name"], dep["marketplace"]))

fail = 0
# superpowers is pinned (anthropics/...) -> must be registered
if not any("superpowers" in e for e in settings.get("enabledPlugins", [])):
    print("  superpowers not registered"); fail = 1
# the dependency manifest now pins a real owner (no `OWNER/` placeholder), so there
# should be NO pending-source-pin left, and agentic-sdlc must be registered.
owner_left = any("OWNER/" in d["source"].get("repo", "") for d in manifest["plugins"])
if owner_left:
    # if any OWNER remains it must have been skipped (not registered)
    if not follow_ups:
        print("  OWNER/ source present but not skipped"); fail = 1
else:
    if not any("agentic-sdlc" in e for e in settings.get("enabledPlugins", [])):
        print("  agentic-sdlc not registered after pin"); fail = 1
sys.exit(fail)
