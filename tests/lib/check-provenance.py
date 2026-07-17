#!/usr/bin/env python3
"""Originality check — enforces the repo's originality policy: no tracked file
may substantially overlap an external text corpus the maintainer checks against.

This is a local maintainer tool. The corpus fingerprint store it reads is
built locally and is git-ignored — neither any corpus text nor its
fingerprints are ever committed. When no fingerprint store is present (e.g.
on CI runners or fresh clones) the scan is skipped with an ok note; the
--self-test mode always runs and needs no store.

Mirrors the neutrality scanner's doctrine (tests/lib/check-neutrality.py):
shapes and hashes, never values. Two fingerprint classes, all salted SHA-256:

  * file-hash    — SHA-256 of a corpus file's raw bytes; catches an exact
                   byte-for-byte copy.
  * line / shingle — each corpus file's *significant* lines (whitespace-
                   collapsed, lowercased, >= min_line_len chars) are salted-
                   hashed individually and in overlapping k-line shingles.
                   For a tracked file we recompute the same hashes and measure
                   containment = matched / total. Line containment measures
                   verbatim reuse; shingle containment adds a local-order
                   signal that catches copied passages of common lines.

Thresholds (stored in the fingerprint file, not hardcoded):
  * gate_threshold  — a finding FAILS the scan above this.
  * author_target   — files in [author_target, gate_threshold) are REPORTED as
                      a warning (the bar for freshly authored content).

Fingerprints are unrecoverable: salted one-way hashes, truncated.

Usage:
  check-provenance.py                 scan tracked files (skips if no store)
  check-provenance.py --report-only   scan but always exit 0
  check-provenance.py --self-test     prove the detectors fire on synthetic data
  check-provenance.py --file PATH...  check one or more files (tracked or not)
                                      at the strict author target
  check-provenance.py --build DIR...  (local, offline) rebuild the fingerprint
                                      store from corpus directories

Exit 0 clean (or skipped / report-only / self-test pass), 1 findings."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FP_PATH = ROOT / "tests/lib/provenance-fingerprints.json"

# Paths never scanned: the fingerprint store and this checker hold only hashes,
# but exempting them keeps the report honest and avoids self-reference.
EXEMPT = {
    "tests/lib/provenance-fingerprints.json",
    "tests/lib/check-provenance.py",
    "tests/lib/neutrality-policy.json",
}

# Fingerprint-file defaults (a freshly built file overrides these).
DEFAULTS = {
    "salt": "agentic-os-provenance-v1",
    "shingle_k": 3,
    "min_line_len": 20,
    "min_lines_gate": 5,      # files with fewer significant lines: hash-match only
    "gate_threshold": 0.40,   # containment at/above this FAILS
    "author_target": 0.25,    # containment at/above this WARNS (fresh-content bar)
    "hash_len": 12,           # hex chars kept per salted line/shingle hash (48-bit)
}

fail = 0


def report(ok: bool, where: str, msg: str) -> None:
    global fail
    if ok:
        print("  ok   %s %s" % (where, msg))
    else:
        print("  FAIL %s %s" % (where, msg))
        fail = 1


def significant_lines(text: str, min_line_len: int) -> list[str]:
    """Ordered significant lines: whitespace-collapsed, lowercased, >= min_line_len.

    Identical normalization to the provenance-audit harness, so the numbers a
    developer sees locally match what CI enforces."""
    out = []
    for ln in text.splitlines():
        s = " ".join(ln.split()).lower()
        if len(s) >= min_line_len:
            out.append(s)
    return out


def salted(s: str, salt: str, hash_len: int) -> str:
    return hashlib.sha256((salt + "\0" + s).encode("utf-8")).hexdigest()[:hash_len]


def line_and_shingle_hashes(lines: list[str], cfg: dict) -> tuple[set[str], set[str]]:
    salt, k, hlen = cfg["salt"], cfg["shingle_k"], cfg["hash_len"]
    line_h = {salted(l, salt, hlen) for l in lines}
    shingles = set()
    for i in range(len(lines) - k + 1):
        shingles.add(salted("\n".join(lines[i:i + k]), salt, hlen))
    return line_h, shingles


def containment(matched: int, total: int) -> float:
    return matched / total if total else 0.0


# ---- scan (shared by real run and self-test) -------------------------------

def scan(cfg: dict, files: list[tuple[str, str]]) -> tuple[list[str], list[str]]:
    """Return (failures, warnings) as human-readable lines. Never echoes source."""
    file_hashes = set(cfg["file_hashes"])
    line_fp = set(cfg["line_hashes"])
    shingle_fp = set(cfg["shingle_hashes"])
    gate, target = cfg["gate_threshold"], cfg["author_target"]
    failures, warnings = [], []
    for rel, text in files:
        if rel in EXEMPT:
            continue
        # Exact byte-for-byte copy — independent of line thresholds.
        raw_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if raw_hash in file_hashes:
            failures.append("%s [exact-copy] byte-identical to a corpus file" % rel)
            continue
        lines = significant_lines(text, cfg["min_line_len"])
        uniq = list(dict.fromkeys(lines))
        if len(uniq) < cfg["min_lines_gate"]:
            continue
        line_h, shingle_h = line_and_shingle_hashes(uniq, cfg)
        lc = containment(sum(1 for h in line_h if h in line_fp), len(line_h))
        # Shingles are computed over ordered (deduped-in-place) lines.
        ordered = list(dict.fromkeys(lines))
        _, sh = line_and_shingle_hashes(ordered, cfg)
        sc = containment(sum(1 for h in sh if h in shingle_fp), len(sh)) if sh else 0.0
        worst = max(lc, sc)
        if worst >= gate:
            failures.append("%s [overlap] line=%.0f%% shingle=%.0f%% (>= gate %.0f%%)"
                            % (rel, lc * 100, sc * 100, gate * 100))
        elif worst >= target:
            warnings.append("%s [overlap] line=%.0f%% shingle=%.0f%% (author target %.0f%%)"
                            % (rel, lc * 100, sc * 100, target * 100))
    return failures, warnings


def tracked_text_files() -> list[tuple[str, str]]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                         capture_output=True, check=True)
    files = []
    for rel in out.stdout.decode("utf-8").split("\0"):
        if not rel:
            continue
        try:
            raw = (ROOT / rel).read_bytes()
        except OSError:
            continue
        if b"\0" in raw[:8192]:
            continue
        try:
            files.append((rel, raw.decode("utf-8")))
        except UnicodeDecodeError:
            continue
    return files


# ---- build (local, offline; neither corpus text nor its fingerprints are committed) ----

def build(dirs: list[str]) -> None:
    cfg = dict(DEFAULTS)
    file_hashes, line_hashes, shingle_hashes = set(), set(), set()
    n_files = 0
    for d in dirs:
        root = Path(d)
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            if any(part in {".git", "node_modules", "__pycache__"} for part in p.parts):
                continue
            try:
                raw = p.read_bytes()
            except OSError:
                continue
            if b"\0" in raw[:8192]:
                continue
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            n_files += 1
            file_hashes.add(hashlib.sha256(text.encode("utf-8")).hexdigest())
            lines = list(dict.fromkeys(significant_lines(text, cfg["min_line_len"])))
            lh, sh = line_and_shingle_hashes(lines, cfg)
            line_hashes |= lh
            shingle_hashes |= sh
    doc = dict(cfg)
    doc["_doc"] = ("Local, git-ignored fingerprint store for the originality check "
                   "(tests/lib/check-provenance.py). Salted one-way hashes only — no source text. "
                   "Rebuild locally with `check-provenance.py --build <corpus dirs...>`. "
                   "line_hashes/shingle_hashes are space-separated hash_len-hex chunks — separated, "
                   "not concatenated, so text scanners never see a single megabyte-long token run.")
    doc["corpus_file_count"] = n_files
    doc["file_hashes"] = sorted(file_hashes)                 # full SHA-256, exact-copy detection
    doc["line_hashes"] = " ".join(sorted(line_hashes))       # space-separated hash_len-hex chunks
    doc["shingle_hashes"] = " ".join(sorted(shingle_hashes))
    FP_PATH.write_text(json.dumps(doc, indent=0) + "\n", encoding="utf-8")
    print("  built %s: %d corpus files, %d file-hashes, %d line-hashes, %d shingle-hashes"
          % (FP_PATH.relative_to(ROOT), n_files, len(file_hashes), len(line_hashes), len(shingle_hashes)))


def _unpack(blob, hash_len: int) -> list[str]:
    """Split a space-separated (or legacy concatenated fixed-width) hex string
    into its chunks. Tolerates a plain list too (self-test builds cfg in memory)."""
    if isinstance(blob, list):
        return blob
    if " " in blob:
        return blob.split()
    return [blob[i:i + hash_len] for i in range(0, len(blob), hash_len)]


def load_cfg() -> dict:
    doc = json.loads(FP_PATH.read_text(encoding="utf-8"))
    cfg = dict(DEFAULTS)
    cfg.update({k: doc[k] for k in doc if k in DEFAULTS})
    hlen = cfg["hash_len"]
    cfg["file_hashes"] = doc.get("file_hashes", [])
    cfg["line_hashes"] = _unpack(doc.get("line_hashes", ""), hlen)
    cfg["shingle_hashes"] = _unpack(doc.get("shingle_hashes", ""), hlen)
    return cfg


# ---- self-test --------------------------------------------------------------

def self_test() -> None:
    """Prove exact-copy, line-overlap, and clean-pass all behave, on synthetic
    in-memory data only — no corpus text, no fixtures on disk."""
    cfg = dict(DEFAULTS)
    cfg["min_lines_gate"] = 3
    # A synthetic corpus work.
    ref = "\n".join("the quick brown fox jumps over lazy dog number %d" % i for i in range(10))
    ref_lines = list(dict.fromkeys(significant_lines(ref, cfg["min_line_len"])))
    lh, sh = line_and_shingle_hashes(ref_lines, cfg)
    cfg["file_hashes"] = [hashlib.sha256(ref.encode()).hexdigest()]
    cfg["line_hashes"] = sorted(lh)
    cfg["shingle_hashes"] = sorted(sh)

    # 1. Byte-identical copy → exact-copy failure.
    f, w = scan(cfg, [("copy.md", ref)])
    report(any("exact-copy" in x for x in f), "self-test", "exact byte copy flagged")

    # 2. High line overlap (reworded first line only) → overlap failure.
    near = ref.replace("the quick brown fox jumps over lazy dog number 0",
                       "a totally different opening sentence entirely here now")
    f, w = scan(cfg, [("near.md", near)])
    report(any("overlap" in x for x in f), "self-test", "high line overlap flagged")

    # 3. Unrelated text → clean.
    clean = "\n".join("an entirely unrelated line of authored prose here %d" % i for i in range(10))
    f, w = scan(cfg, [("clean.md", clean)])
    report(not f and not w, "self-test", "unrelated authored text passes (%s)" % (f + w or "clean"))

    report(True, "self-test", "detectors present")


def check_files(paths: list[str]) -> None:
    """Check individual files (tracked or not) at the strict author target —
    the bar for freshly authored content. Prints
    per-file containment and exits non-zero if any file reaches author_target."""
    if not FP_PATH.exists():
        # Unlike the tree scan, --file is an explicit check request — passing
        # silently without a store would be misleading.
        print("  FAIL --file needs a local fingerprint store (run --build first)")
        sys.exit(1)
    cfg = dict(load_cfg())
    cfg["gate_threshold"] = cfg["author_target"]  # strict bar for freshly authored files
    files, unreadable = [], 0
    for p in paths:
        try:
            files.append((p, Path(p).read_text(encoding="utf-8")))
        except OSError as e:
            print("  FAIL %s unreadable: %s" % (p, e)); unreadable += 1
    failures, warnings = scan(cfg, files)
    for p, _ in files:
        hit = [x for x in failures if x.startswith(p + " ")]
        print("  FAIL %s" % hit[0] if hit
              else "  ok   %s below author target %.0f%%" % (p, cfg["author_target"] * 100))
    sys.exit(1 if failures or unreadable else 0)


def main() -> None:
    args = sys.argv[1:]
    if "--build" in args:
        dirs = [a for a in args if a != "--build"]
        if not dirs:
            print("  FAIL --build needs one or more corpus directories"); sys.exit(1)
        build(dirs)
        return
    if "--self-test" in args:
        self_test()
        sys.exit(fail)
    if "--file" in args:
        paths = [a for a in args if a != "--file"]
        if not paths:
            print("  FAIL --file needs one or more paths"); sys.exit(1)
        check_files(paths)
        return

    if not FP_PATH.exists():
        # The fingerprint store is a local, git-ignored maintainer artifact —
        # absent on CI runners and fresh clones. Nothing to scan against.
        print("  ok   provenance no local fingerprint store — scan skipped "
              "(build one with --build to enable)")
        sys.exit(0)
    cfg = load_cfg()
    files = tracked_text_files()
    failures, warnings = scan(cfg, files)
    for w in warnings:
        print("  warn %s" % w)
    for f in failures:
        print("  FAIL %s" % f)
    report_only = "--report-only" in args
    ok = not failures
    print("  %s provenance scanned %d tracked files: %d failure(s), %d warning(s)"
          % ("ok  " if ok else "FAIL", len(files), len(failures), len(warnings)))
    if report_only:
        if failures:
            print("  note report-only mode: %d failure(s) not blocking" % len(failures))
        sys.exit(0)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
