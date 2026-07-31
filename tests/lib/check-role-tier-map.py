#!/usr/bin/env python3
"""Role-tier map drift check — every role named in
plugins/agentic-sdlc/references/role-tier-map.json must still be named (as a
backticked identifier) somewhere in
plugins/agentic-sdlc/references/model-routing.md, so a role renamed or
removed from one place can't silently drift from the other.

Schema validity of role-tier-map.json itself is covered by
tests/lib/check-schemas.py (registered there as a fixture); this checker only
guards the doc <-> data correspondence, and only in the JSON -> doc
direction. model-routing.md's tier table legitimately names things that are
NOT (and may never be) actual subagent dispatches -- code-review-orchestrator
is a skill, not one of agentic-sdlc's five agent files, so the reverse
direction (every doc entry must appear in the JSON) is deliberately NOT
checked here; enforcing it would fail today on that exact, intentional
exception.

Usage:
  check-role-tier-map.py               run the check
  check-role-tier-map.py --self-test   prove the extractor works

Exit 0 clean (or self-test pass), 1 on any dangling role."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAP_PATH = ROOT / "plugins/agentic-sdlc/references/role-tier-map.json"
DOC_PATH = ROOT / "plugins/agentic-sdlc/references/model-routing.md"

fail = 0


def report(ok: bool, what: str) -> None:
    global fail
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok:
        fail = 1


def backticked_identifiers(text: str) -> set[str]:
    return set(re.findall(r"`([a-z][a-z0-9-]*)`", text))


def check() -> None:
    role_map = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    doc_identifiers = backticked_identifiers(DOC_PATH.read_text(encoding="utf-8"))

    missing = sorted(role for role in role_map if role not in doc_identifiers)
    report(not missing,
           "every role-tier-map.json role is named in model-routing.md (%s)"
           % (missing or "none missing"))


def self_test() -> None:
    ids = backticked_identifiers("the `codebase-scout` role and `sizing-analyst` role")
    report(ids == {"codebase-scout", "sizing-analyst"},
           "self-test: extracts backticked identifiers (%r)" % ids)
    report(backticked_identifiers("no backticks here") == set(),
           "self-test: no false positives on plain prose")


def main() -> None:
    if "--self-test" in sys.argv[1:]:
        self_test()
        sys.exit(fail)
    check()
    sys.exit(fail)


if __name__ == "__main__":
    main()
