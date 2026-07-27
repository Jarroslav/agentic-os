#!/usr/bin/env python3
"""Changelog gate — a pull request that changes a plugin's shipped content must
also record what changed in that plugin's CHANGELOG.md.

The plugins here are distributed: users install whatever is on main, and the
changelog is the only place they learn what moved. A change that lands without
an entry is invisible to them and, in practice, stays invisible — the entry is
never written later, because nobody remembers a release contained it. That is
how the /agentic-init interview gained a screen with no note anywhere.

Deliberately NOT a version check. Asserting that plugin.json's version has a
matching `## [x.y.z]` heading sounds like the same gate and is not: both gaps
this was written for kept version and heading perfectly consistent, because the
version was never bumped at all. What is missing in the real failure is the
*entry*, so the entry is what is checked.

Scope: only files a user receives. A plugin's own CHANGELOG.md is excluded
(editing it is the fix, not the trigger), and so are files that exist to satisfy
other gates — a re-attestation or a regenerated content index is bookkeeping
forced by the edit, never a user-visible change on its own.

Escape hatch: the `no-changelog` PR label, applied by the workflow, for changes
a user genuinely cannot observe. Reach for it rarely; a typo in shipped text is
still text a user reads.

Usage:
  check-changelog.py --base REF   compare HEAD against REF (the PR base)
  check-changelog.py --self-test  prove the rule fires on synthetic file lists

Exit 0 clean or self-test pass, 1 findings."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Bookkeeping a plugin edit forces elsewhere. Changing one of these alone says
# nothing a user could observe, so it must not demand a changelog entry.
IGNORED_SUFFIXES = ("/CHANGELOG.md",)

fail = 0


def report(ok: bool, name: str, msg: str = "") -> None:
    global fail
    if ok:
        print("  ok   %s %s" % (name, msg))
    else:
        print("  FAIL %s %s" % (name, msg))
        fail = 1


def plugins_needing_entry(changed: list[str]) -> dict[str, bool]:
    """Map plugin name → whether its CHANGELOG.md is among the changed files.

    Pure, so the self-test can exercise it without a git history."""
    touched: dict[str, bool] = {}
    for path in changed:
        parts = path.split("/")
        if len(parts) < 3 or parts[0] != "plugins":
            continue
        name = parts[1]
        if path.endswith(IGNORED_SUFFIXES):
            touched.setdefault(name, False)
            continue
        touched[name] = touched.get(name, False)
    for path in changed:
        parts = path.split("/")
        if len(parts) >= 3 and parts[0] == "plugins" and path.endswith("/CHANGELOG.md"):
            touched[parts[1]] = True
    return touched


def content_changed(changed: list[str], plugin: str) -> bool:
    """Did anything a user receives change for this plugin?"""
    prefix = "plugins/%s/" % plugin
    return any(p.startswith(prefix) and not p.endswith(IGNORED_SUFFIXES)
               for p in changed)


def self_test() -> None:
    def case(changed, expect_fail, label):
        touched = plugins_needing_entry(changed)
        bad = [n for n in touched
               if content_changed(changed, n) and not touched[n]]
        report(bool(bad) == expect_fail, "self-test", label)

    case(["plugins/agentic-os/skills/x/SKILL.md"], True,
         "shipped edit with no changelog entry is flagged")
    case(["plugins/agentic-os/skills/x/SKILL.md",
          "plugins/agentic-os/CHANGELOG.md"], False,
         "shipped edit with a changelog entry passes")
    case(["plugins/agentic-os/CHANGELOG.md"], False,
         "a changelog-only edit needs no entry of its own")
    case(["tests/lib/refinstall.py", "mcp/content-index.json"], False,
         "changes outside plugins/ are out of scope")
    case(["plugins/agentic-os/skills/x/SKILL.md",
          "plugins/agentic-sdlc/CHANGELOG.md"], True,
         "another plugin's changelog does not cover this one")
    case(["plugins/agentic-os/skills/x/SKILL.md",
          "plugins/agentic-os/CHANGELOG.md",
          "plugins/agentic-sdlc/references/y.md"], True,
         "two plugins touched, only one recorded")
    report(True, "self-test", "rule present")
    sys.exit(fail)


def main() -> None:
    args = sys.argv[1:]
    if "--self-test" in args:
        self_test()
    if "--base" not in args:
        print("  FAIL usage: check-changelog.py --base REF | --self-test")
        sys.exit(1)
    base = args[args.index("--base") + 1]
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", "%s...HEAD" % base],
            cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, OSError) as e:
        print("  FAIL cannot diff against %r: %s" % (base, e))
        sys.exit(1)
    changed = [line for line in out.splitlines() if line]
    touched = plugins_needing_entry(changed)
    if not touched:
        print("  ok   changelog no plugin content changed")
        sys.exit(0)
    for name in sorted(touched):
        if not content_changed(changed, name):
            continue
        if touched[name]:
            report(True, "plugins/%s" % name, "(changelog updated)")
        else:
            report(False, "plugins/%s" % name,
                   "shipped content changed with no CHANGELOG.md entry. Add one "
                   "under the plugin's current version, or apply the "
                   "'no-changelog' label if a user cannot observe this change.")
    sys.exit(fail)


if __name__ == "__main__":
    main()
