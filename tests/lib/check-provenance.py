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

Containment alone is a whole-file average, so a long lifted passage inside an
otherwise original file averages away to nothing. A third measure catches that:

  * max_run      — the longest run of consecutive significant lines whose every
                   k-line shingle is in the corpus, i.e. the longest verbatim
                   passage. Judged against its own thresholds, independent of
                   the file's size.

Thresholds (stored in the fingerprint file, not hardcoded):
  * gate_threshold  — containment at/above this FAILS the scan.
  * author_target   — files in [author_target, gate_threshold) are REPORTED as
                      a warning (the bar for freshly authored content).
  * max_run_gate    — a verbatim run this long or longer FAILS.
  * max_run_target  — a shorter run still warns (the fresh-content bar).
  * min_lines_containment — containment is only reported at or above this many
                      significant lines. Over a dozen lines a ratio is noise, and
                      a host manifest of mandated lines would score 30% however
                      original it is. Exact-copy and max_run are size-independent
                      and still apply, which is what keeps short files honest.

The salt lives outside the store: PROVENANCE_SALT, else tests/lib/.provenance-salt
(git-ignored, generated on first --build). The store records only a salt_id, so a
store built under a different salt fails loudly instead of silently measuring 0%.

Fingerprints are unrecoverable: salted one-way hashes, truncated.

Usage:
  check-provenance.py                 scan tracked files (skips if no store)
  check-provenance.py --report-only   scan but always exit 0
  check-provenance.py --require-store scan, but fail rather than skip with no store
  check-provenance.py --self-test     prove the detectors fire on synthetic data
  check-provenance.py --file PATH...  check one or more files (tracked or not)
                                      at the strict author target
  check-provenance.py --build DIR...  (local, offline) rebuild the fingerprint
                                      store from corpus directories
  check-provenance.py --attest        record a clean tree's per-file measurements
                                      to tests/lib/originality-attestation.json
  check-provenance.py --verify-attestation
                                      re-check the tree against that record;
                                      needs no store, so it runs anywhere

Exit 0 clean (or skipped / report-only / self-test pass), 1 findings."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FP_PATH = ROOT / "tests/lib/provenance-fingerprints.json"
SALT_PATH = ROOT / "tests/lib/.provenance-salt"
ATT_PATH = ROOT / "tests/lib/originality-attestation.json"

ATT_SCHEMA = 1

# Paths never scanned: the fingerprint store, this checker and the attestation
# hold only hashes, but exempting them keeps the report honest and avoids
# self-reference.
EXEMPT = {
    "tests/lib/provenance-fingerprints.json",
    "tests/lib/originality-attestation.json",
    "tests/lib/check-provenance.py",
    "tests/lib/neutrality-policy.json",
}

# Files whose text is not authored expression — reproduced verbatim because an
# external standard requires it, or emitted by a tool. Overlap here carries no
# information about originality: our Apache-2.0 text is supposed to be identical
# to everyone else's, and two lockfiles resolving the same packages are supposed
# to agree. Kept deliberately short; anything a human writes belongs in the scan.
NOT_AUTHORED = {"LICENSE"}
NOT_AUTHORED_NAMES = {"package-lock.json", "LICENSE"}

# Dependency and virtual-environment trees inside a corpus checkout: vendored
# third-party code, not the corpus author's work. Fingerprinting them would make
# every project that vendors the same library look like a copy of the corpus.
CORPUS_SKIP_DIRS = {".git", "node_modules", "__pycache__", "__MACOSX", ".venv",
                    "venv", "site-packages", ".tox", "vendor", ".mypy_cache",
                    ".pytest_cache", ".ruff_cache", ".gradle", "target"}
CORPUS_SKIP_SUFFIXES = (".dist-info", ".egg-info")


def out_of_scope(rel: str) -> bool:
    return (rel in EXEMPT or rel in NOT_AUTHORED
            or rel.rsplit("/", 1)[-1] in NOT_AUTHORED_NAMES)


# Fingerprint-file defaults (a freshly built file overrides these).
# The salt is deliberately absent — see load_salt().
DEFAULTS = {
    "shingle_k": 3,
    "min_line_len": 20,
    "min_lines_gate": 5,      # files with fewer significant lines: hash-match only
    "min_lines_containment": 20,  # below this, containment is noise — see measure()
    "gate_threshold": 0.40,   # containment at/above this FAILS
    "author_target": 0.25,    # containment at/above this WARNS (fresh-content bar)
    "max_run_gate": 8,        # verbatim run this long or longer FAILS
    "max_run_target": 5,      # shorter verbatim run still WARNS
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


def load_salt(create: bool = False) -> str | None:
    """The salt never lives in the store. A store plus a known salt would let
    anyone test arbitrary candidate lines for corpus membership, so the salt is
    the one secret here: PROVENANCE_SALT, else a git-ignored local file."""
    env = os.environ.get("PROVENANCE_SALT", "").strip()
    if env:
        return env
    if SALT_PATH.exists():
        got = SALT_PATH.read_text(encoding="utf-8").strip()
        if got:
            return got
    if not create:
        return None
    got = secrets.token_hex(32)
    SALT_PATH.write_text(got + "\n", encoding="utf-8")
    try:
        SALT_PATH.chmod(0o600)
    except OSError:
        pass
    print("  note generated a new salt at %s (git-ignored, keep it — the store "
          "is unreadable without it)" % SALT_PATH.relative_to(ROOT))
    return got


def salt_id(salt: str) -> str:
    """A public, non-reversing handle on the salt, so a store can prove which
    salt built it without disclosing the salt."""
    return hashlib.sha256(("salt-id\0" + salt).encode("utf-8")).hexdigest()[:16]


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


def longest_matched_run(ordered: list[str], shingle_fp: set[str], cfg: dict) -> int:
    """Length, in significant lines, of the longest verbatim passage.

    A present shingle at position i means lines i..i+k-1 are all corpus lines in
    corpus order. A maximal stretch of r consecutive present shingles therefore
    covers r + k - 1 lines. Containment is a whole-file average and washes such a
    passage out when the rest of the file is original — this measure does not."""
    salt, k, hlen = cfg["salt"], cfg["shingle_k"], cfg["hash_len"]
    if len(ordered) < k:
        return 0
    best = run = 0
    for i in range(len(ordered) - k + 1):
        if salted("\n".join(ordered[i:i + k]), salt, hlen) in shingle_fp:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best + k - 1 if best else 0


def measure(text: str, cfg: dict) -> dict:
    """Per-file measurements, shared by the scan and the attestation so the two
    can never disagree about what a file scores."""
    file_hashes = set(cfg["file_hashes"])
    line_fp = set(cfg["line_hashes"])
    shingle_fp = set(cfg["shingle_hashes"])
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    out = {"sha256": sha, "exact": sha in file_hashes,
           "line": 0.0, "shingle": 0.0, "max_run": 0, "measured": False}
    if out["exact"]:
        return out
    ordered = list(dict.fromkeys(significant_lines(text, cfg["min_line_len"])))
    if len(ordered) < cfg["min_lines_gate"]:
        return out
    out["max_run"] = longest_matched_run(ordered, shingle_fp, cfg)
    out["measured"] = True
    # Containment is a ratio, and a ratio over a dozen lines is noise. A host
    # manifest whose every mandated line — "license": "Apache-2.0", a
    # ${CLAUDE_PLUGIN_ROOT} permission glob — is necessarily identical to
    # everyone else's scores 30% however original the rest of it is. Below the
    # floor, report only the two size-independent signals: an exact copy, and a
    # verbatim run. Both caught every real finding this check has ever made in a
    # short file, so nothing is lost by declining to guess from a ratio.
    if len(ordered) < cfg["min_lines_containment"]:
        return out
    line_h, shingle_h = line_and_shingle_hashes(ordered, cfg)
    out["line"] = containment(sum(1 for h in line_h if h in line_fp), len(line_h))
    out["shingle"] = (containment(sum(1 for h in shingle_h if h in shingle_fp),
                                  len(shingle_h)) if shingle_h else 0.0)
    return out


# ---- scan (shared by real run and self-test) -------------------------------

def scan(cfg: dict, files: list[tuple[str, str]]) -> tuple[list[str], list[str]]:
    """Return (failures, warnings) as human-readable lines. Never echoes source."""
    gate, target = cfg["gate_threshold"], cfg["author_target"]
    run_gate, run_target = cfg["max_run_gate"], cfg["max_run_target"]
    failures, warnings = [], []
    for rel, text in files:
        if out_of_scope(rel):
            continue
        m = measure(text, cfg)
        # Exact byte-for-byte copy — independent of every other threshold.
        if m["exact"]:
            failures.append("%s [exact-copy] byte-identical to a corpus file" % rel)
            continue
        if not m["measured"]:
            continue
        lc, sc, mr = m["line"], m["shingle"], m["max_run"]
        worst = max(lc, sc)
        if worst >= gate:
            failures.append("%s [overlap] line=%.0f%% shingle=%.0f%% (>= gate %.0f%%)"
                            % (rel, lc * 100, sc * 100, gate * 100))
        elif worst >= target:
            warnings.append("%s [overlap] line=%.0f%% shingle=%.0f%% (author target %.0f%%)"
                            % (rel, lc * 100, sc * 100, target * 100))
        # Reported separately: a file can sit far below the containment bar and
        # still carry a wholly lifted passage.
        if mr >= run_gate:
            failures.append("%s [verbatim-run] longest matched run = %d lines "
                            "(>= gate %d)" % (rel, mr, run_gate))
        elif mr >= run_target:
            warnings.append("%s [verbatim-run] longest matched run = %d lines "
                            "(author target %d)" % (rel, mr, run_target))
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

def build(dirs: list[str], force: bool = False) -> None:
    for d in dirs:
        if not Path(d).is_dir():
            print("  FAIL --build: %s is not a directory" % d)
            sys.exit(1)
    cfg = dict(DEFAULTS)
    cfg["salt"] = load_salt(create=True)
    file_hashes, line_hashes, shingle_hashes = set(), set(), set()
    n_files = 0
    for d in dirs:
        root = Path(d)
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            if any(part in CORPUS_SKIP_DIRS for part in p.parts):
                continue
            if any(part.endswith(CORPUS_SKIP_SUFFIXES) for part in p.parts):
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
    # A rebuild replaces the store outright. Rebuilding from a subset of the
    # corpus would quietly weaken every later scan, so shrinking needs intent.
    if FP_PATH.exists() and not force:
        try:
            prev = json.loads(FP_PATH.read_text(encoding="utf-8")).get("corpus_file_count", 0)
        except (OSError, ValueError):
            prev = 0
        if n_files < prev:
            print("  FAIL --build: %d corpus files now vs %d in the existing store.\n"
                  "       Pass every corpus directory in one invocation, or --force to "
                  "shrink deliberately." % (n_files, prev))
            sys.exit(1)
    doc = dict(cfg)
    doc.pop("salt")                      # the salt is never stored; only its id
    doc["salt_id"] = salt_id(cfg["salt"])
    doc["_doc"] = ("Local, git-ignored fingerprint store for the originality check "
                   "(tests/lib/check-provenance.py). Salted one-way hashes only — no source text, "
                   "and not the salt: without the salt named by salt_id these hashes cannot be "
                   "tested against any candidate line. "
                   "Rebuild locally with `check-provenance.py --build <corpus dirs...>`, passing "
                   "every corpus directory in one invocation. "
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
    salt = load_salt()
    if not salt:
        # Silence here would look identical to a clean tree: every hash would
        # miss and every file would score 0%. Say so instead.
        print("  FAIL provenance a store is present but no salt is. Set PROVENANCE_SALT "
              "or restore %s." % SALT_PATH.relative_to(ROOT))
        sys.exit(1)
    want = doc.get("salt_id")
    if want and salt_id(salt) != want:
        print("  FAIL provenance the salt does not match the one that built this store "
              "(salt_id mismatch). Every measurement would read 0%. Restore the "
              "matching salt, or rebuild the store with --build.")
        sys.exit(1)
    if not want:
        print("  warn provenance store predates salt_id — rebuild it with --build to "
              "bind it to the current salt.")
    cfg["salt"] = salt
    hlen = cfg["hash_len"]
    cfg["file_hashes"] = doc.get("file_hashes", [])
    cfg["line_hashes"] = _unpack(doc.get("line_hashes", ""), hlen)
    cfg["shingle_hashes"] = _unpack(doc.get("shingle_hashes", ""), hlen)
    cfg["corpus_file_count"] = doc.get("corpus_file_count", 0)
    cfg["store_id"] = hashlib.sha256(
        FP_PATH.read_bytes()).hexdigest()
    cfg["salt_id"] = salt_id(salt)
    return cfg


# ---- self-test --------------------------------------------------------------

def self_test() -> None:
    """Prove exact-copy, line-overlap, verbatim-run and clean-pass all behave, on
    synthetic in-memory data only — no corpus text, no fixtures on disk."""
    cfg = dict(DEFAULTS)
    cfg["min_lines_gate"] = 3
    cfg["salt"] = "self-test-salt-not-the-real-one"
    # A synthetic corpus work.
    ref = "\n".join("the quick brown fox jumps over lazy dog number %d" % i for i in range(20))
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

    # 3. A lifted passage buried in otherwise original prose. Containment stays
    #    under the author target, so only the run metric can see it — this is the
    #    case a containment-only gate lets through.
    own = ["a freshly authored sentence of my own number %d" % i for i in range(88)]
    lifted = ["the quick brown fox jumps over lazy dog number %d" % i for i in range(12)]
    buried = "\n".join(own[:44] + lifted + own[44:])
    m = measure(buried, cfg)
    report(max(m["line"], m["shingle"]) < cfg["author_target"],
           "self-test", "buried passage stays under the containment bar (line=%.0f%%)"
           % (m["line"] * 100))
    f, w = scan(cfg, [("buried.md", buried)])
    report(any("verbatim-run" in x for x in f), "self-test",
           "buried 12-line verbatim run flagged (run=%d)" % m["max_run"])

    # 4. Unrelated text → clean on every measure.
    clean = "\n".join("an entirely unrelated line of authored prose here %d" % i for i in range(10))
    f, w = scan(cfg, [("clean.md", clean)])
    report(not f and not w, "self-test", "unrelated authored text passes (%s)" % (f + w or "clean"))

    # 5. The containment floor must not hide a short file that is genuinely
    #    copied — the two size-independent signals still have to fire.
    short = "\n".join(ref.splitlines()[:9])          # 9 lines, under the floor
    m = measure(short, cfg)
    report(m["line"] == 0.0 and m["max_run"] >= 8, "self-test",
           "short copied file: containment suppressed (%.0f%%) but run still fires (%d)"
           % (m["line"] * 100, m["max_run"]))

    # 6. The salt is what makes the store unreadable; a different salt must not
    #    keep matching.
    other = dict(cfg)
    other["salt"] = "a-different-salt-entirely"
    m = measure(ref, other)
    report(m["line"] == 0.0 and m["max_run"] == 0, "self-test",
           "a mismatched salt matches nothing (so a silent 0% is a real signal)")

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
    # Strict bar for freshly authored files: the warn levels become the gate.
    cfg["gate_threshold"] = cfg["author_target"]
    cfg["max_run_gate"] = cfg["max_run_target"]
    files, unreadable = [], 0
    for p in paths:
        try:
            files.append((p, Path(p).read_text(encoding="utf-8")))
        except OSError as e:
            print("  FAIL %s unreadable: %s" % (p, e)); unreadable += 1
    failures, warnings = scan(cfg, files)
    for p, _ in files:
        hits = [x for x in failures if x.startswith(p + " ")]
        if hits:
            for h in hits:
                print("  FAIL %s" % h)
        else:
            print("  ok   %s below author target %.0f%% and run target %d"
                  % (p, cfg["author_target"] * 100, cfg["max_run_target"]))
    sys.exit(1 if failures or unreadable else 0)


# ---- attestation ------------------------------------------------------------
#
# The corpus is a private local checkout and its fingerprints are never
# committed, so CI cannot repeat the scan. What CI can do is hold the maintainer
# to a recorded result: --attest records every tracked file's measurements from a
# clean scan, and --verify-attestation re-checks that record against the tree
# without needing the store at all. Same shape as mcp/content-index.json and
# check-content-drift.mjs — a committed claim plus a cheap check that it still
# holds. Changing any tracked text file then means either re-running the scan
# locally or turning CI red.

def _att_thresholds(cfg: dict) -> dict:
    return {k: cfg[k] for k in ("gate_threshold", "author_target", "max_run_gate",
                                "max_run_target", "shingle_k", "min_line_len",
                                "min_lines_gate", "hash_len")}


def attest() -> None:
    if not FP_PATH.exists():
        print("  FAIL --attest needs a local fingerprint store (run --build first)")
        sys.exit(1)
    cfg = load_cfg()
    files = tracked_text_files()
    target, run_target = cfg["author_target"], cfg["max_run_target"]
    entries, blocking = {}, []
    for rel, text in files:
        if out_of_scope(rel):
            continue
        m = measure(text, cfg)
        if m["exact"]:
            blocking.append("%s [exact-copy] byte-identical to a corpus file" % rel)
        elif max(m["line"], m["shingle"]) >= target:
            blocking.append("%s [overlap] line=%.0f%% shingle=%.0f%% (>= author target %.0f%%)"
                            % (rel, m["line"] * 100, m["shingle"] * 100, target * 100))
        elif m["max_run"] >= run_target:
            blocking.append("%s [verbatim-run] longest matched run = %d lines "
                            "(>= author target %d)" % (rel, m["max_run"], run_target))
        entries[rel] = {"sha256": m["sha256"], "line": round(m["line"], 4),
                        "shingle": round(m["shingle"], 4), "max_run": m["max_run"]}
    if blocking:
        # An attestation is a claim that the tree is clean. It may not exist for
        # a tree that is not.
        for b in blocking:
            print("  FAIL %s" % b)
        print("  FAIL --attest refused: %d file(s) at or above the author target. "
              "Attest only a clean tree." % len(blocking))
        sys.exit(1)
    doc = {
        "schema": ATT_SCHEMA,
        "_doc": ("Committed record of the originality check's per-file results "
                 "(tests/lib/check-provenance.py). Holds no corpus fingerprints and no "
                 "salt — only this repo's own file hashes and the scores they scored. "
                 "Refresh with --attest after a local --build; CI re-checks it with "
                 "--verify-attestation, which needs no corpus."),
        "attested_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "corpus_file_count": cfg["corpus_file_count"],
        "store_id": cfg["store_id"],
        "salt_id": cfg["salt_id"],
        "thresholds": _att_thresholds(cfg),
        "files": dict(sorted(entries.items())),
    }
    ATT_PATH.write_text(json.dumps(doc, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    print("  ok   attested %d tracked files against %d corpus files → %s"
          % (len(entries), cfg["corpus_file_count"], ATT_PATH.relative_to(ROOT)))


def verify_attestation() -> None:
    """Needs no fingerprint store, so it runs on any clone or CI runner."""
    if not ATT_PATH.exists():
        print("  FAIL provenance no %s — build a store and run --attest"
              % ATT_PATH.relative_to(ROOT))
        sys.exit(1)
    try:
        doc = json.loads(ATT_PATH.read_text(encoding="utf-8"))
    except ValueError as e:
        print("  FAIL provenance attestation is not valid JSON: %s" % e)
        sys.exit(1)
    if doc.get("schema") != ATT_SCHEMA:
        print("  FAIL provenance attestation schema %r is not the expected %d"
              % (doc.get("schema"), ATT_SCHEMA))
        sys.exit(1)
    th = doc.get("thresholds") or {}
    target = th.get("author_target", DEFAULTS["author_target"])
    run_target = th.get("max_run_target", DEFAULTS["max_run_target"])
    recorded = doc.get("files") or {}
    failures = []
    seen = 0
    for rel, text in tracked_text_files():
        if out_of_scope(rel):
            continue
        seen += 1
        got = recorded.get(rel)
        if got is None:
            failures.append("%s not covered by the attestation (re-run --attest)" % rel)
            continue
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if sha != got.get("sha256"):
            failures.append("%s changed since it was attested (re-run --attest)" % rel)
            continue
        if max(got.get("line", 0.0), got.get("shingle", 0.0)) >= target:
            failures.append("%s attested at or above the author target" % rel)
        if got.get("max_run", 0) >= run_target:
            failures.append("%s attested with a %d-line verbatim run"
                            % (rel, got.get("max_run", 0)))
    stale = [rel for rel in recorded if rel not in
             {r for r, _ in tracked_text_files()}]
    for f in failures:
        print("  FAIL %s" % f)
    if stale:
        print("  note %d attested path(s) no longer tracked — harmless, tidied on "
              "the next --attest" % len(stale))
    if failures:
        print("  FAIL provenance attestation does not hold for %d of %d tracked files"
              % (len(failures), seen))
        sys.exit(1)
    print("  ok   provenance attestation holds for %d tracked files (recorded %s "
          "against %s corpus files)"
          % (seen, doc.get("attested_at", "?"), doc.get("corpus_file_count", "?")))


def main() -> None:
    args = sys.argv[1:]
    if "--build" in args:
        dirs = [a for a in args if a not in ("--build", "--force")]
        if not dirs:
            print("  FAIL --build needs one or more corpus directories"); sys.exit(1)
        build(dirs, force="--force" in args)
        return
    if "--self-test" in args:
        self_test()
        sys.exit(fail)
    if "--attest" in args:
        attest()
        sys.exit(fail)
    if "--verify-attestation" in args:
        verify_attestation()
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
        if "--require-store" in args:
            print("  FAIL provenance no local fingerprint store (build one with --build)")
            sys.exit(1)
        print("  ok   provenance no local fingerprint store — scan skipped "
              "(build one with --build to enable; CI holds the tree to "
              "--verify-attestation instead)")
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
