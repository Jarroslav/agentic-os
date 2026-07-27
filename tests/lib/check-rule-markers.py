#!/usr/bin/env python3
"""Rule-provenance marker checks — every `agentic-os:rules` marker pair in
shipped plugin content is well-formed:

  <!-- agentic-os:rules source=".agentic/guides/..." topic="slug" -->
  ...digest...
  <!-- /agentic-os:rules -->

Validated per file: every open has a matching close before the next open (no
nesting, no unclosed blocks); `source` and `topic` attributes present and
non-empty; `topic` is a lowercase-hyphen slug; a `source` under
`.agentic/guides/standards/` or `.agentic/guides/policy/` must map to a
shipped template (those guides exist at install time); any other
`.agentic/guides/` source is prefix-validated only (generated guides exist
only in target repos). Spec: templates/guides/standards/working-with-agents.md
§ Rule provenance markers.

Deterministic and offline. `--self-test` proves each failure class fires."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TPL = ROOT / "plugins/agentic-os/templates"

OPEN_RE = re.compile(
    r"<!--\s*agentic-os:rules\b([^>]*?)-->")
CLOSE_RE = re.compile(r"<!--\s*/agentic-os:rules\s*-->")
ATTR_RE = re.compile(r'(\w+)="([^"]*)"')
TOPIC_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
STRICT_PREFIXES = (".agentic/guides/standards/", ".agentic/guides/policy/")

fail = 0


def err(path, msg):
    global fail
    print("  FAIL %s: %s" % (path, msg))
    fail = 1


def shipped_template_exists(source):
    """A standards/policy source must ship as a template (.md or .md.tmpl)."""
    name = source.rsplit("/", 1)[-1]
    if source.startswith(".agentic/guides/standards/"):
        base = TPL / "guides/standards" / name
    else:  # .agentic/guides/policy/
        base = TPL / "policy" / (name + ".tmpl")
        return base.exists() or (TPL / "policy" / name).exists()
    return base.exists() or base.with_suffix(base.suffix + ".tmpl").exists()


def check_text(path, text):
    """Validate all marker pairs in one file's text. `path` is a label."""
    events = sorted(
        [(m.start(), "open", m) for m in OPEN_RE.finditer(text)]
        + [(m.start(), "close", m) for m in CLOSE_RE.finditer(text)])
    depth = 0
    for _, kind, m in events:
        if kind == "open":
            if depth:
                err(path, "nested or unclosed marker before offset %d" % m.start())
                return
            depth = 1
            attrs = dict(ATTR_RE.findall(m.group(1)))
            source, topic = attrs.get("source", ""), attrs.get("topic", "")
            if not source:
                err(path, "marker missing source attribute")
            elif not source.startswith(".agentic/guides/"):
                err(path, "source %r not under .agentic/guides/" % source)
            elif source.startswith(STRICT_PREFIXES) and not shipped_template_exists(source):
                err(path, "source %r maps to no shipped template" % source)
            if not topic:
                err(path, "marker missing topic attribute")
            elif not TOPIC_RE.match(topic):
                err(path, "topic %r is not a lowercase-hyphen slug" % topic)
        else:
            if not depth:
                err(path, "close marker with no open at offset %d" % m.start())
                return
            depth = 0
    if depth:
        err(path, "marker opened but never closed")


def self_test():
    ok_pair = ('<!-- agentic-os:rules source=".agentic/guides/standards/code-quality.md"'
               ' topic="verification-evidence" -->\nx\n<!-- /agentic-os:rules -->')
    cases = [  # (label, text, should_fail)
        ("clean", ok_pair, False),
        ("no-markers", "plain text, even a grep for agentic-os:rules", False),
        ("unclosed", '<!-- agentic-os:rules source=".agentic/guides/standards/code-quality.md" topic="a" -->', True),
        ("nested", '<!-- agentic-os:rules source=".agentic/guides/standards/code-quality.md" topic="a" -->'
                   '<!-- agentic-os:rules source=".agentic/guides/standards/code-quality.md" topic="b" -->'
                   '<!-- /agentic-os:rules -->', True),
        ("orphan-close", "<!-- /agentic-os:rules -->", True),
        ("no-source", '<!-- agentic-os:rules topic="a" -->x<!-- /agentic-os:rules -->', True),
        ("no-topic", '<!-- agentic-os:rules source=".agentic/guides/standards/code-quality.md" -->x<!-- /agentic-os:rules -->', True),
        ("bad-topic", '<!-- agentic-os:rules source=".agentic/guides/standards/code-quality.md" topic="Bad_Slug" -->x<!-- /agentic-os:rules -->', True),
        ("bad-prefix", '<!-- agentic-os:rules source="docs/foo.md" topic="a" -->x<!-- /agentic-os:rules -->', True),
        ("ghost-guide", '<!-- agentic-os:rules source=".agentic/guides/standards/no-such-guide.md" topic="a" -->x<!-- /agentic-os:rules -->', True),
        ("generated-prefix-ok", '<!-- agentic-os:rules source=".agentic/guides/data/database-patterns.md" topic="a" -->x<!-- /agentic-os:rules -->', False),
    ]
    global fail
    bad = 0
    for label, text, should_fail in cases:
        fail = 0
        check_text("<self-test:%s>" % label, text)
        if bool(fail) != should_fail:
            print("  SELF-TEST FAIL %s: expected %s"
                  % (label, "failure" if should_fail else "pass"))
            bad = 1
    fail = bad
    print("  ok   self-test (%d cases)" % len(cases) if not bad else "  self-test failed")


if "--self-test" in sys.argv:
    self_test()
    sys.exit(fail)

files = sorted(p for p in ROOT.glob("plugins/**/*.md*")
               if p.suffix in (".md",) or p.name.endswith(".md.tmpl"))
if not files:
    print("  FAIL no markdown files found under plugins/"); sys.exit(1)

marked = 0
for f in files:
    text = f.read_text(encoding="utf-8")
    if "agentic-os:rules" not in text:
        continue
    marked += 1
    check_text(f.relative_to(ROOT), text)

print("  ok   rule markers: %d file(s) with markers scanned, %s"
      % (marked, "0 errors" if not fail else "errors above"))
sys.exit(fail)
