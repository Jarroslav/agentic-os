#!/usr/bin/env python3
"""Neutrality & PII scan — the mechanical form of the repo's neutrality rule:
no PII, personal names, or organization names ship in this repo.

Two layers, both driven by tests/lib/neutrality-policy.json:

  1. Cleartext pattern classes (shapes, never values): email addresses outside
     an allowlist, home-directory paths, confidentiality markers, and vendor
     model IDs outside an allowlist of files. The regexes describe *shapes*, so
     publishing them leaks nothing.
  2. A hashed token denylist: every tracked text file is tokenized
     (lowercase alphanumeric runs), and each token — plus n-grams for
     multi-word entries — is SHA-256'd and compared against the policy's
     hashes. Banned names are enforced without ever appearing in the repo.

The one sanctioned identity is the canonical plugin author enforced by
check-manifests.py; nothing here matches it, by construction.

Zero dependencies, scans `git ls-files` only. `--self-test` proves every
detector class fires (on synthetic in-memory content) and that allowlists
pass — no violating fixture files ever land in the tree.

Exit 0 clean, 1 findings (or self-test failure)."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "tests/lib/neutrality-policy.json"

fail = 0


def report(ok: bool, where: str, msg: str) -> None:
    global fail
    if ok:
        print("  ok   %s %s" % (where, msg))
    else:
        print("  FAIL %s %s" % (where, msg))
        fail = 1


def tracked_text_files() -> list[tuple[str, str]]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                         capture_output=True, check=True)
    files = []
    for rel in out.stdout.decode("utf-8").split("\0"):
        if not rel:
            continue
        p = ROOT / rel
        try:
            raw = p.read_bytes()
        except OSError:
            continue
        if b"\0" in raw[:8192]:
            continue  # binary
        try:
            files.append((rel, raw.decode("utf-8")))
        except UnicodeDecodeError:
            continue
    return files


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def scan_layer1(policy: dict, files: list[tuple[str, str]]) -> list[str]:
    findings = []
    exempt = set(policy.get("layer1_exempt_paths", []))
    for cls, spec in policy.get("patterns", {}).items():
        rx = re.compile(spec["regex"])
        allow = [re.compile(a) for a in spec.get("allow", [])]
        allow_files = set(spec.get("allow_files", []))
        for rel, text in files:
            if rel in exempt or rel in allow_files:
                continue
            for m in rx.finditer(text):
                if any(a.search(m.group(0)) for a in allow):
                    continue
                findings.append("%s:%d [%s] %r" % (rel, line_of(text, m.start()), cls, m.group(0)))
    return findings


def scan_layer2(policy: dict, files: list[tuple[str, str]]) -> list[str]:
    entries = policy.get("banned_token_hashes", [])
    by_words: dict[int, set[str]] = {}
    for e in entries:
        by_words.setdefault(int(e.get("words", 1)), set()).add(e["sha256"])
    findings = []
    token_rx = re.compile(r"[a-z0-9]+")
    for rel, text in files:
        tokens = token_rx.findall(text.lower())
        for n, hashes in by_words.items():
            if len(tokens) < n:
                continue
            seen = set()
            for i in range(len(tokens) - n + 1):
                gram = " ".join(tokens[i:i + n])
                if gram in seen:
                    continue
                seen.add(gram)
                if hashlib.sha256(gram.encode("utf-8")).hexdigest() in hashes:
                    # Deliberately do not echo the token back in cleartext.
                    findings.append("%s [banned-token] %d-word token matches the hashed denylist"
                                    % (rel, n))
    return findings


def self_test(policy: dict) -> None:
    """Prove every detector class fires and every allowlist passes, on
    synthetic in-memory content only — nothing violating touches the tree."""
    # Layer 1 positives (constructed at runtime so this source stays clean).
    at = chr(64)
    cases = {
        "email": "contact person.name" + at + "somecorp.com today",
        "home_path": "logs at /Users" + "/some" + "body/project/out.txt",
        "confidentiality_marker": "Proprietary " + "& Confidential. page 4",
        "vendor_model_id": "pin the model " + "claude-" + "sonnet-9-9 here",
    }
    for cls, content in cases.items():
        got = scan_layer1(policy, [("selftest.md", content)])
        report(any("[%s]" % cls in f for f in got), "self-test", "layer1 %s fires" % cls)
    # Layer 1 negatives: the allowlists actually allow.
    clean = [
        ("selftest.md", "mail valid" + at + "example.com and path /home/runner and CLAUDE.md .claude/hooks"),
    ]
    got = scan_layer1(policy, clean)
    report(not got, "self-test", "layer1 allowlists pass (%s)" % (got or "clean"))
    # Layer 2: a synthetic banned token, single and multi-word.
    tok = "zz" + "internalorg" + "zz"
    phrase = tok + " holding " + tok
    test_policy = {"banned_token_hashes": [
        {"sha256": hashlib.sha256(tok.encode()).hexdigest(), "words": 1},
        {"sha256": hashlib.sha256((tok + " holding " + tok).encode()).hexdigest(), "words": 3},
    ]}
    got = scan_layer2(test_policy, [("selftest.md", "Ship it for " + phrase.upper() + "!")])
    report(len(got) == 2, "self-test", "layer2 single + 3-gram hashed tokens fire (%d/2)" % len(got))
    got = scan_layer2(test_policy, [("selftest.md", "an ordinary sentence about plugins")])
    report(not got, "self-test", "layer2 clean text passes")
    # The real policy scans the real tree clean of its own hashes' *hex* form.
    report(bool(policy.get("banned_token_hashes")), "self-test", "real policy has hashed entries")


def main() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if "--self-test" in sys.argv[1:]:
        self_test(policy)
        sys.exit(fail)

    files = tracked_text_files()
    findings = scan_layer1(policy, files) + scan_layer2(policy, files)
    for f in findings:
        report(False, f.split(" ", 1)[0], f.split(" ", 1)[1])
    report(not findings, "neutrality", "scanned %d tracked text files, %d finding(s)"
           % (len(files), len(findings)))
    sys.exit(fail)


if __name__ == "__main__":
    main()
