#!/usr/bin/env python3
"""Every path a shipped HTML page points at must exist.

`plugins/agentic-sdlc/sdlc.html` is a map of the package: its inventory names each
skill, agent and hook, and each entry carries the source file it lives in, which
the page fetches on demand. A renamed or deleted file leaves the page pointing at
nothing, and the failure is invisible until somebody clicks that one node — so it
is checked here instead.

The page renders itself from a single inventory array, which is what makes this
check cheap: extract the `src:` lists, resolve each path against the plugin
directory, and report the ones that are not there.

Usage:
  check-html-refs.py            check every known page
  check-html-refs.py --self-test  prove the extractor and the resolver both work

Exit 0 clean, 1 on a dangling reference."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# page -> directory its relative paths resolve against (the page's own directory)
PAGES = ["plugins/agentic-sdlc/sdlc.html"]

SRC_BLOCK = re.compile(r"src:\s*\[(.*?)\]", re.DOTALL)
QUOTED = re.compile(r'"([^"]+)"')

fail = 0


def report(ok: bool, where: str, msg: str) -> None:
    global fail
    print("  %s %s %s" % ("ok  " if ok else "FAIL", where, msg))
    if not ok:
        fail = 1


def referenced_paths(html: str) -> list[str]:
    """Paths listed in the inventory's `src:` arrays, in order, deduped."""
    out = []
    for block in SRC_BLOCK.findall(html):
        for path in QUOTED.findall(block):
            if path not in out:
                out.append(path)
    return out


def check_page(rel: str) -> None:
    page = ROOT / rel
    if not page.is_file():
        return report(False, rel, "page not found")
    base = page.parent
    paths = referenced_paths(page.read_text(encoding="utf-8"))
    if not paths:
        # Not "clean" — it means the extractor stopped matching how the page is
        # written, so the check would silently pass forever.
        return report(False, rel, "no source paths found — has the inventory "
                                  "changed shape? this check would pass blindly")
    missing = [p for p in paths if not (base / p).exists()]
    if missing:
        for p in missing:
            report(False, rel, "points at a path that does not exist: %s" % p)
        return
    report(True, rel, "all %d referenced source paths resolve" % len(paths))


def self_test() -> None:
    sample = '''
      {id:"a", src:["skills/x/SKILL.md"]},
      {id:"b", src:["agents/y.md", "references/z.md"]},
      {id:"c"},
    '''
    got = referenced_paths(sample)
    report(got == ["skills/x/SKILL.md", "agents/y.md", "references/z.md"],
           "self-test", "extracts every src path in order (%r)" % got)
    report(referenced_paths('{id:"a"}') == [],
           "self-test", "an inventory with no sources yields nothing")
    # A dangling path must actually be caught, not merely collected.
    page = ROOT / PAGES[0]
    base = page.parent
    report(not (base / "skills/definitely-not-a-real-skill/SKILL.md").exists(),
           "self-test", "resolver reports a made-up path as absent")


def main() -> None:
    if "--self-test" in sys.argv[1:]:
        self_test()
        sys.exit(fail)
    for rel in PAGES:
        check_page(rel)
    sys.exit(fail)


if __name__ == "__main__":
    main()
