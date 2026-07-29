#!/usr/bin/env python3
"""Differential comparator for the uninstall round-trip invariant.

    install(a,b) → uninstall(b)   ==   install(a)

Compares two target trees and reports every divergence with a path. A golden
manifest is deliberately not used: tests/golden/fresh-developer-manifest.txt is
directory-level and cannot see a file deleted inside .agentic/, and a golden for
a differential property hides regressions behind a re-record. Building the
reference install in the same run and diffing is self-maintaining and strictly
stronger.

Comparison classes:
  exact      every file under .claude/, .agentic/ (minus agentic-os/),
             .githooks/, scripts/, plus AGENTS.md, PATTERNS.md, CLAUDE.md,
             .gitignore — path set AND sha256.
  semantic   .agentic/agentic-os/install.json — answers (presets as an ordered
             list), agentic_os_version, and files as a sorted
             {path: (owner, template, sha256)} map. Never raw bytes: JSON key
             insertion order differs after a key deletion.
  semantic   docs/audits/instruction-scorecard.json — key set exact; entries
             compared on content_sha256 and source.
  out-of-tree presence/absence and the agentic-os: marker of
             .git/hooks/pre-commit, and presence of pre-commit.local.

Excluded, i.e. the accepted non-determinism (each is a real divergence a fresh
install would show, not an oversight):
  1. doctor.json — carries checked_at.
  2. install.json key insertion order — deleting a key reorders the object.
  3. journal.stack_discovery — a fresh install re-runs discovery; uninstall
     reuses the journaled record by design (init Phase 1's own rule).
  4. journal.follow_ups — uninstall appends its own.
  5. gen/* content and composite_score — LLM output; neither executor runs
     Phase 5, so only slot sets and scorecard key coverage are comparable.
  6. mtimes.

Usage: check-roundtrip.py <TREE_A> <TREE_B> [--label "T9a round-trip"]
Exit 0 identical, 1 divergent.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

EXACT_DIRS = (".claude", ".agentic", ".githooks", "scripts")
EXACT_FILES = ("AGENTS.md", "PATTERNS.md", "CLAUDE.md", ".gitignore")
JOURNAL = ".agentic/agentic-os/install.json"
SCORECARD = "docs/audits/instruction-scorecard.json"
# Excluded from the exact sweep; compared semantically or not at all.
SKIP = {JOURNAL, ".agentic/agentic-os/doctor.json"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def exact_set(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for d in EXACT_DIRS:
        base = root / d
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            if rel in SKIP or rel.startswith(".agentic/state/"):
                continue
            out[rel] = sha(p)
    for f in EXACT_FILES:
        p = root / f
        if p.is_file():
            out[f] = sha(p)
    return out


def journal_view(root: Path) -> dict | None:
    p = root / JOURNAL
    if not p.is_file():
        return None
    d = json.loads(p.read_text())
    files = {k: (v.get("owner"), v.get("template"), v.get("sha256"))
             for k, v in d.get("files", {}).items()}
    answers = dict(d.get("answers", {}))
    return {"agentic_os_version": d.get("agentic_os_version"),
            "presets": list(answers.get("presets") or []),
            "files": dict(sorted(files.items()))}


def scorecard_view(root: Path) -> dict | None:
    p = root / SCORECARD
    if not p.is_file():
        return None
    d = json.loads(p.read_text())
    return {k: (v.get("content_sha256"), v.get("source"))
            for k, v in sorted(d.get("files", {}).items())}


def hook_view(root: Path) -> dict:
    hooks = root / ".git" / "hooks"
    live, local = hooks / "pre-commit", hooks / "pre-commit.local"
    marked = live.is_file() and "agentic-os:" in live.read_text(errors="replace")
    return {"pre-commit": live.is_file(), "ours": marked, "local": local.is_file()}


def diff_maps(a: dict, b: dict, what: str, problems: list[str]) -> None:
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    for k in only_a:
        problems.append("%s: only in A (uninstalled): %s" % (what, k))
    for k in only_b:
        problems.append("%s: only in B (fresh install): %s" % (what, k))
    for k in sorted(set(a) & set(b)):
        if a[k] != b[k]:
            problems.append("%s: differs at %s\n      A=%r\n      B=%r" % (what, k, a[k], b[k]))


def main() -> None:
    if len(sys.argv) < 3:
        print("  FAIL check-roundtrip: usage: check-roundtrip.py <A> <B> [--label X]")
        sys.exit(1)
    a, b = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    label = "round-trip"
    if "--label" in sys.argv:
        label = sys.argv[sys.argv.index("--label") + 1]

    problems: list[str] = []
    diff_maps(exact_set(a), exact_set(b), "tree", problems)

    ja, jb = journal_view(a), journal_view(b)
    if ja is None or jb is None:
        problems.append("journal: missing in %s" % ("A" if ja is None else "B"))
    else:
        if ja["presets"] != jb["presets"]:
            problems.append("journal: presets %r != %r" % (ja["presets"], jb["presets"]))
        if ja["agentic_os_version"] != jb["agentic_os_version"]:
            problems.append("journal: version %r != %r"
                            % (ja["agentic_os_version"], jb["agentic_os_version"]))
        diff_maps(ja["files"], jb["files"], "journal.files", problems)

    sa, sb = scorecard_view(a), scorecard_view(b)
    if (sa is None) != (sb is None):
        problems.append("scorecard: present in only one tree")
    elif sa is not None:
        diff_maps(sa, sb, "scorecard", problems)

    ha, hb = hook_view(a), hook_view(b)
    if ha != hb:
        problems.append("git hooks: %r != %r" % (ha, hb))

    if problems:
        print("  FAIL %s: %d divergence(s)" % (label, len(problems)))
        for p in problems[:40]:
            print("    " + p)
        if len(problems) > 40:
            print("    ... and %d more" % (len(problems) - 40))
        sys.exit(1)
    print("  ok   %s: trees are equivalent" % label)


if __name__ == "__main__":
    main()
