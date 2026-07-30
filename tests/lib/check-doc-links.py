#!/usr/bin/env python3
"""Every markdown link, anchor fragment, and docs/*.html href must resolve.

`docs/PRINCIPLES.md` once linked to
`plugins/agentic-sdlc/README.md#gate-arbiter-autonomous-gates` — an anchor that
had never existed. It survived a full skill rename because the rename's
mechanical find-replace correctly updated the substring inside the anchor
without anyone noticing the anchor itself was already wrong, and nothing in
this repo dereferenced a `#fragment` to check. The link was fixed by hand;
this checker is what stops the next one from surviving unnoticed.

Three link kinds share one failure mode — a reference to a location that does
not exist, invisible until a human clicks it — and one resolution primitive,
so they live in one checker rather than three:
  - relative markdown links       [text](path)
  - markdown anchor fragments     [text](#anchor)  and  [text](path.md#anchor)
  - docs/*.html hrefs and srcs    href="path"  src="path"

Explicitly out of scope, as a stated decision:
  - Bare prose file-path mentions with no `[...]()` syntax. Measured at
    ~1600 candidate tokens across the repo for ~5-7 true positives — too
    noisy for a regex-based checker. (One real instance of this exact rot,
    found by hand, was fixed separately in
    plugins/agentic-qe/skills/eval-harness/references/python.md.)
  - External URLs. No network calls; ~18% of them are deliberately fake
    placeholders (e.g. https://your-gateway.example.com).
  - Image links ![alt](src) — kept out so the measured baseline (86 relative
    links, 25 anchor links) this checker is calibrated against doesn't shift.
  - plugins/agentic-sdlc/sdlc.html — fully owned by check-html-refs.py, which
    already resolves its `src:` inventory array; a generic href/src regex here
    would misfire on that file's one `src="${esc(p)}"` JS template literal.
  - docs/setup/app.js and every `#...`-only href in .html/.js — docs/setup is
    a client-side hash-router SPA (`location.hash.replace('#','')`); `#mcp`
    there means "set view state to mcp", not "there must be an id=mcp
    element." Skipped by a blanket rule (any href starting with `#`), not a
    per-file exemption, because that equivalence never holds for a JS router.

Usage:
  check-doc-links.py               resolve every link/anchor/href
  check-doc-links.py --self-test   prove the extractors and resolver work

Exit 0 clean, 1 on a dangling reference."""
from __future__ import annotations

import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = Path(__file__).resolve().parent / "doc-links-policy.json"

fail = 0


def report(ok: bool, where: str, msg: str) -> None:
    global fail
    print("  %s %s %s" % ("ok  " if ok else "FAIL", where, msg))
    if not ok:
        fail = 1


# --------------------------------------------------------------------------
# extraction — pure functions, so the self-test can exercise them directly
# --------------------------------------------------------------------------

# Fenced code blocks (```/~~~, any fence length, matched fence on the closing
# line) and inline code spans. Blanked to same-length whitespace rather than
# deleted, so every surviving match's line number is still correct.
FENCE = re.compile(r'^([ \t]*)(```+|~~~+).*?\n.*?^\1\2.*?$', re.MULTILINE | re.DOTALL)
INLINE_CODE = re.compile(r'`[^`\n]+?`')


def strip_code(text: str) -> str:
    """Blank fenced blocks and inline code spans so nothing inside code is
    ever mistaken for a real link. Blanking (not deleting) keeps every
    surviving character's line/column position unchanged."""
    def blank(m: re.Match) -> str:
        return "".join(c if c == "\n" else " " for c in m.group(0))
    return INLINE_CODE.sub(blank, FENCE.sub(blank, text))


# (?<!!) excludes image syntax ![alt](src) — out of scope, see module docstring.
MD_LINK = re.compile(r'(?<!!)\[[^\]\n]*\]\(([^)\s][^)]*)\)')


def extract_links(text: str) -> list[tuple[str, int]]:
    """(target, 1-based line number) for every non-image markdown link in
    code-stripped text."""
    out = []
    for m in MD_LINK.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        out.append((m.group(1), line))
    return out


def is_placeholder(target: str) -> bool:
    """A link target is never a real path once it names itself as a
    template slot rather than a location — e.g. `[<name>](<slug>.md)` in a
    skill's own output-template documentation."""
    return "<" in target or ">" in target


def split_anchor(target: str) -> tuple[str, str | None]:
    """('path', 'anchor') or ('path', None). An empty path means same-file."""
    path, sep, anchor = target.partition("#")
    return path, (anchor if sep else None)


_URL_SCHEME = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*:')


def is_external(path: str) -> bool:
    """True for anything with a URL scheme (http:, https:, mailto:, data:, a
    bare `//host` protocol-relative URL) — out of scope, see module
    docstring. A relative filesystem path never matches: Windows drive
    letters aside (irrelevant here), nothing in this repo's markdown links a
    single letter followed by a colon."""
    return bool(_URL_SCHEME.match(path)) or path.startswith("//")


# GitHub anchor slugification: strip inline markup from the heading text,
# lowercase, drop everything but word chars/space/hyphen, spaces -> hyphens
# (one-for-one, not collapsed — "Phase 4 — spec" keeps both spaces around the
# stripped em-dash, so it becomes "phase-4--spec").
_HEADING_LINK = re.compile(r'\[([^\]]*)\]\([^)]*\)')
_HEADING_CODE = re.compile(r'`([^`]*)`')
_HEADING_BOLD = re.compile(r'\*\*([^*]*)\*\*')
_HEADING_ITALIC = re.compile(r'\*([^*]*)\*')
_NON_SLUG = re.compile(r'[^\w\- ]', re.UNICODE)
HEADING = re.compile(r'^#{1,6}\s+(.+?)\s*$', re.MULTILINE)


def gh_slug(heading_text: str) -> str:
    s = heading_text.strip()
    s = _HEADING_LINK.sub(r'\1', s)
    s = _HEADING_CODE.sub(r'\1', s)
    s = _HEADING_BOLD.sub(r'\1', s)
    s = _HEADING_ITALIC.sub(r'\1', s)
    s = s.lower()
    s = _NON_SLUG.sub('', s)
    return s.replace(' ', '-')


def anchors_for_text(text: str) -> list[str]:
    """Every heading's slug, in document order, with GitHub's -1/-2 dedup
    suffix applied to repeats. Computed on code-stripped text so a
    heading-shaped line inside a fenced block is never counted. Implemented
    even though no duplicate heading currently exists anywhere this checker
    targets — a checker with a known, applied rule beats one that would be
    silently wrong the day a second `## Overview` shows up."""
    seen: dict[str, int] = {}
    out = []
    for m in HEADING.finditer(strip_code(text)):
        base = gh_slug(m.group(1))
        n = seen.get(base, 0)
        seen[base] = n + 1
        out.append(base if n == 0 else "%s-%d" % (base, n))
    return out


def resolve(base_dir: Path, path: str) -> tuple[Path, str]:
    """(resolved_path, kind) where kind is 'dir' if the link target ends in
    '/', else 'file'."""
    clean = path.split("?", 1)[0]
    return (base_dir / clean).resolve(), ("dir" if clean.endswith("/") else "file")


def target_exists(resolved: Path, kind: str) -> bool:
    # .exists() is deliberately not used for kind == "file": it is true for a
    # directory too, and a link with no trailing slash that happens to name a
    # directory should be reported missing (see the strictness note in the
    # module docstring's directory-target-link rule).
    return resolved.is_dir() if kind == "dir" else resolved.is_file()


TEMPLATES_ROOT = "plugins/agentic-os/templates"


def resolves_as_template(source_rel: str, resolved: Path, templates_dir: Path) -> bool:
    """A link inside templates/** is written relative to where its file and
    its target will BOTH land post-install, per
    plugins/agentic-os/skills/agentic-init/SKILL.md's destination-map table
    — e.g. templates/guides/standards/<x>.md and templates/policy/<y>.md.tmpl
    both end up under .agentic/guides/ (standards/ and policy/ respectively),
    so a pre-install link like "../policy/y.md" from inside guides/standards/
    is correct post-install but does not resolve against the pre-install tree
    shape at all (that literal path doesn't land in templates/policy/, it
    lands in templates/guides/policy/, which doesn't exist).

    Replicating the full install-time remap here would mean re-deriving
    agentic-init's entire destination table. Since every template basename in
    this tree is unique (verified: no two templates/** files share a
    filename, checked at self-test time as a shape guard), searching by
    basename anywhere under templates/** is exactly as correct and far
    simpler. Scoped to both sides living under templates/** on purpose —
    broadening it would let a genuinely broken link anywhere else in the repo
    get silently laundered through a rule meant for one directory tree."""
    if TEMPLATES_ROOT not in source_rel:
        return False
    if TEMPLATES_ROOT not in resolved.as_posix():
        return False
    name = resolved.name
    candidates = list(templates_dir.rglob(name)) + list(templates_dir.rglob(name + ".tmpl"))
    return len(candidates) > 0


# HTML: only hrefs/srcs that look like a real path — the leading [^"#]
# excludes anything starting with "#" (the docs/setup hash-router) at the
# regex level, so no per-file special-casing is needed for that exclusion.
HTML_REF = re.compile(r'\b(?:href|src)="([^"#][^"]*)"')


def extract_html_refs(text: str) -> list[str]:
    out = []
    for target in HTML_REF.findall(text):
        if target.startswith(("http://", "https://", "mailto:", "data:")):
            continue
        out.append(target)
    return out


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------

def scan_md_files(root: Path, policy: dict) -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True,
                         text=True, check=True).stdout.split("\n")
    suffixes = set(policy["scan"]["suffixes"])
    excludes = policy["scan"]["exclude_globs"]
    excluded_files = set(policy.get("excluded_files", {}))
    keep = []
    for rel in out:
        if not rel:
            continue
        if rel in excluded_files:
            continue
        if any(fnmatch.fnmatch(rel, g) for g in excludes):
            continue
        p = root / rel
        if not p.is_file() or p.suffix not in suffixes:
            continue
        keep.append(p)
    return keep


def run_checks(root: Path, policy: dict) -> None:
    files = scan_md_files(root, policy)
    guards = policy["shape_guards"]
    templates_dir = root / TEMPLATES_ROOT
    unresolved: list[tuple[str, int, str]] = []
    relative_link_total = 0
    anchor_link_total = 0
    anchor_cache: dict[Path, list[str]] = {}

    # The .tmpl fallback below trusts every template basename to be unique;
    # verify that holds on every real run, not just at self-test time — a
    # future name collision would make the fallback ambiguous rather than
    # loudly wrong.
    names = [f.name for f in templates_dir.rglob("*") if f.is_file()]
    dupes = sorted({n for n in names if names.count(n) > 1})
    report(not dupes, "templates/",
           "every template basename is unique" if not dupes
           else "duplicate template basenames make the .tmpl fallback "
                "ambiguous: %s" % ", ".join(dupes))

    def anchors_of(p: Path) -> list[str]:
        if p not in anchor_cache:
            try:
                anchor_cache[p] = anchors_for_text(p.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                anchor_cache[p] = []
        return anchor_cache[p]

    for p in files:
        rel = str(p.relative_to(root))
        try:
            raw = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        text = strip_code(raw)

        for target, line in extract_links(text):
            if is_placeholder(target) or is_external(target):
                continue
            path_part, anchor = split_anchor(target)

            if path_part:
                relative_link_total += 1
                resolved, kind = resolve(p.parent, path_part)
                if (not target_exists(resolved, kind)
                        and not resolves_as_template(rel, resolved, templates_dir)):
                    unresolved.append((rel, line, "dangling link: %s" % target))
                    continue
                target_file = resolved
            else:
                target_file = p  # same-file anchor

            if anchor is not None:
                anchor_link_total += 1
                if not target_file.is_file():
                    continue  # already reported as a dangling link above
                if anchor not in anchors_of(target_file):
                    unresolved.append((rel, line,
                                       "dangling anchor #%s in %s" % (anchor, target)))

    for page_rel in policy["html_pages"]:
        page = root / page_rel
        if not page.is_file():
            unresolved.append((page_rel, 0, "listed html_pages entry does not exist"))
            continue
        raw = page.read_text(encoding="utf-8", errors="ignore")
        for target in extract_html_refs(raw):
            resolved, kind = resolve(page.parent, target)
            if not target_exists(resolved, kind):
                unresolved.append((page_rel, 0, "dangling href/src: %s" % target))

    report(relative_link_total >= guards["min_relative_links"], "scan",
           "%d relative links found (>= %d expected) — has the corpus shrunk, "
           "or has the extractor stopped matching?"
           % (relative_link_total, guards["min_relative_links"]))
    report(anchor_link_total >= guards["min_anchor_links"], "scan",
           "%d anchor links found (>= %d expected)"
           % (anchor_link_total, guards["min_anchor_links"]))

    if unresolved:
        for rel, line, why in sorted(set(unresolved)):
            where = "%s:%d" % (rel, line) if line else rel
            report(False, where, why)
    else:
        report(True, "doc-links",
               "%d relative links and %d anchor links across %d files all resolve"
               % (relative_link_total, anchor_link_total, len(files)))


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------

def self_test() -> None:
    report(extract_links(strip_code("```\n[fake](nowhere.md)\n```")) == [],
           "self-test", "a link inside a fenced code block is invisible")

    report(extract_links(strip_code("line one\n`[fake](nowhere.md)` more text")) == [],
           "self-test", "a link inside an inline code span is invisible")

    report(is_placeholder("<slug>.md") and is_placeholder("`<path>`"),
           "self-test", "angle-bracket targets are recognized as placeholders")
    report(not is_placeholder("real-file.md"), "self-test",
           "an ordinary filename is never mistaken for a placeholder")

    report(is_external("https://example.com/x") and is_external("mailto:a@example.com")
           and is_external("//cdn.example.com/x"), "self-test",
           "URL-scheme and protocol-relative targets are recognized as external")
    report(not is_external("../plugins/agentic-os/README.md")
           and not is_external("README.md"), "self-test",
           "ordinary relative paths are never mistaken for external URLs")

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "agents").mkdir()
        report(target_exists(*resolve(tmp, "agents/")), "self-test",
               "a trailing-slash link resolves on directory existence")
        report(not target_exists(*resolve(tmp, "agents")), "self-test",
               "the same target WITHOUT a trailing slash is checked as a file "
               "and correctly reported missing — a deliberate strictness choice")

        # Template .tmpl fallback: scoped to templates/** on both sides.
        tpl_root = tmp / "plugins/agentic-os/templates"
        (tpl_root / "policy").mkdir(parents=True)
        (tpl_root / "guides/standards").mkdir(parents=True)
        (tpl_root / "policy/example-policy.md.tmpl").write_text("x")
        source = tpl_root / "guides/standards/example-guide.md"
        resolved, kind = resolve(source.parent, "../../policy/example-policy.md")
        report(not target_exists(resolved, kind), "self-test",
               "the literal .md target does not exist on disk (as expected)")
        report(resolves_as_template(str(source.relative_to(tmp)), resolved, tpl_root),
               "self-test", "but it resolves via the scoped .tmpl fallback")

        # Negative: same missing-file shape, but the LINKING file is outside
        # templates/** — the fallback must not apply there.
        outside = tmp / "plugins/agentic-sdlc/skills/example/SKILL.md"
        outside.parent.mkdir(parents=True)
        resolved2, kind2 = resolve(outside.parent, "../../../agentic-os/templates/policy/example-policy.md")
        report(not resolves_as_template(str(outside.relative_to(tmp)), resolved2, tpl_root),
               "self-test",
               "the same fallback does NOT fire for a link outside templates/**")

    report(gh_slug("Judgment gates") == "judgment-gates", "self-test",
           "plain heading slugifies correctly")
    report(gh_slug("Phase 4 — spec") == "phase-4--spec", "self-test",
           "an em-dash is stripped but both surrounding spaces survive as hyphens")
    report(gh_slug("`code` in a heading") == "code-in-a-heading", "self-test",
           "inline code markup is unwrapped before slugifying")
    dup = anchors_for_text("## Overview\n\ntext\n\n## Overview\n")
    report(dup == ["overview", "overview-1"], "self-test",
           "a repeated heading gets GitHub's -1 dedup suffix (%r)" % dup)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "a.md").write_text("## Some Section\n")
        (tmp / "b.md").write_text("[x](a.md#some-section)\n[y](a.md#nonexistent-section)\n")
        a_anchors = anchors_for_text((tmp / "a.md").read_text())
        report("some-section" in a_anchors, "self-test",
               "a real cross-file anchor is found in the target file's headings")
        report("nonexistent-section" not in a_anchors, "self-test",
               "a dangling cross-file anchor is correctly absent — this is the "
               "PRINCIPLES.md incident shape, reproduced with synthetic names")

    report(extract_html_refs('<a href="#mcp">x</a><link href="styles.css">')
           == ["styles.css"], "self-test",
           "a hash-router href is skipped; a real relative href is kept")
    report(extract_html_refs('<a href="#">x</a>') == [], "self-test",
           "a bare # href is also skipped")

    report(extract_links("") == [], "self-test", "empty input yields nothing")


def main() -> None:
    args = sys.argv[1:]
    if "--self-test" in args:
        self_test()
        sys.exit(fail)
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    run_checks(ROOT, policy)
    sys.exit(fail)


if __name__ == "__main__":
    main()
