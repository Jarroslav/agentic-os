#!/usr/bin/env python3
"""Every skill, agent or blueprint this repo names must be one that ships.

The package is held together by names. A preset claims skills by name, the agent
registry routes to them by name, `sdlc.html` draws them by name, the setup site
lists them by name, and one skill hands off to another by writing its name in
prose. Nothing checked that any of those names resolved. Renaming a skill left
every prose hand-off pointing at nothing, and the failure surfaced only when a
model went looking for a skill that was not there.

The design problem is telling a skill reference apart from ordinary English.
Backticked hyphenated words are not enough — `breaking-change` and `edge-case`
are prose. So only *marked* references count: an identifier next to the word
skill / agent / blueprint, or following call / invoke / delegate to, plus the
typed fields that are unambiguous by construction (preset arrays, registry rows,
frontmatter, the HTML inventory, the setup site, MCP prompt paths). That keeps
the allowlist to a handful of genuinely-external names instead of the ~150
entries a bare-token scan would need.

The inventory is read off disk, never listed here, so adding a skill needs no
edit and deleting one turns every surviving reference into a failure.

Usage:
  check-skill-refs.py               resolve every reference against what ships
  check-skill-refs.py --self-test   prove the extractors and the resolver work
  check-skill-refs.py --banned-names   retired names appear nowhere (rename gate)
  check-skill-refs.py --graph       emit the reference graph, one edge per line

Exit 0 clean, 1 on a dangling reference."""
from __future__ import annotations

import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = Path(__file__).resolve().parent / "skill-refs-policy.json"

fail = 0


def report(ok: bool, where: str, msg: str) -> None:
    global fail
    print("  %s %s %s" % ("ok  " if ok else "FAIL", where, msg))
    if not ok:
        fail = 1


# --------------------------------------------------------------------------
# extractors — pure functions, so the self-test can exercise them directly
# --------------------------------------------------------------------------

# An identifier: lowercase, at least one hyphen, optionally plugin-namespaced.
# The mandatory hyphen is what keeps single English words out.
ID = r"([a-z][a-z0-9]*(?:[-:][a-z0-9]+)+)"

# A reference is marked when the surrounding words say it names a component.
# The verb alternations are case-folded because prose starts sentences with them
# ("Call `gate-arbiter` ..."); the identifier itself stays strictly lowercase.
MARKED = [
    re.compile(r"`" + ID + r"`\s+(?i:skill|agent|blueprint)\b"),
    re.compile(r"\b(?i:skill|agent|blueprint)s?\s+`" + ID + r"`"),
    re.compile(r"\b(?i:call|calls|invoke|invokes|dispatch|dispatches|"
               r"delegate to|delegates to|hand off to|hands off to|"
               r"routes to|route to)\s+(?:the\s+)?`" + ID + r"`"),
]

# `the agentic-sdlc `name` skill` — the registry's routing contract, which
# `agentic-init`'s prune rule parses with this same shape.
REGISTRY_ROW = re.compile(r"the\s+(agentic-[a-z]+)\s+`([a-z0-9-]+)`\s+(skill|blueprint)")

# sdlc.html renders itself from one inventory array plus six mini-diagrams.
HTML_PAGES = ["plugins/agentic-sdlc/sdlc.html"]
HTML_ID = re.compile(r'\bid:\s*"([a-z0-9-]+)"')
HTML_ENTRY = re.compile(r'\bid:\s*"([a-z0-9-]+)"((?:[^{}]|\{[^{}]*\})*)')
HTML_SRC = re.compile(r'src:\s*\[(.*?)\]', re.DOTALL)
# Scoped to `edges:[...]` — an unscoped pair regex also matches the CSS-variable
# arrays elsewhere on the page and reports `--accent` as a dangling node.
HTML_EDGE_BLOCK = re.compile(r'edges:\s*\[((?:[^\[\]]|\[[^\[\]]*\])*)\]', re.DOTALL)
HTML_EDGE_PAIR = re.compile(r'\[\s*"([a-z0-9-]+)"\s*,\s*"([a-z0-9-]+)"')
QUOTED = re.compile(r'"([^"]+)"')

# docs/setup/app.js per-role lists.
APPJS_REF = re.compile(r"\b(?:skill|name):\s*'([a-z][a-z0-9]*(?:-[a-z0-9]+)+)'")

# Legacy slash commands. Namespaced to this package's own plugins so that
# credential-scanning patterns like `/user:password` are not mistaken for one.
SLASH_CMD = re.compile(r"(/(?:sdlc|agentic|qe):[a-z][a-z0-9-]*)")


def marked_refs(text: str) -> list[str]:
    """Identifiers the prose explicitly marks as naming a component.

    Deduped: two patterns legitimately match the same phrase ("call the `x`
    skill"), and a doubled count would quietly inflate the shape guard."""
    out = []
    for rx in MARKED:
        for name in rx.findall(text):
            if name not in out:
                out.append(name)
    return out


def registry_rows(text: str) -> list[tuple[str, str, str]]:
    """(plugin, name, kind) for each agent-registry routing row."""
    return [(p, n, k) for p, n, k in REGISTRY_ROW.findall(text)]


def html_ids(text: str) -> list[str]:
    """Every id declared on the page — inventory entries and diagram nodes."""
    out = []
    for node_id in HTML_ID.findall(text):
        if node_id not in out:
            out.append(node_id)
    return out


def html_entries(text: str) -> list[tuple[str, list[str]]]:
    """(id, [src paths]) for each inventory entry on an HTML page."""
    out = []
    for node_id, body in HTML_ENTRY.findall(text):
        srcs = []
        for block in HTML_SRC.findall(body):
            srcs.extend(QUOTED.findall(block))
        out.append((node_id, srcs))
    return out


def html_edges(text: str) -> list[tuple[str, str]]:
    """Directed edges between diagram nodes, from `edges:[...]` blocks only."""
    out = []
    for block in HTML_EDGE_BLOCK.findall(text):
        out.extend(HTML_EDGE_PAIR.findall(block))
    return out


def appjs_refs(text: str) -> list[str]:
    """Skill names hand-listed by the setup site."""
    return APPJS_REF.findall(text)


# --------------------------------------------------------------------------
# inventory — derived from disk
# --------------------------------------------------------------------------

def build_inventory(root: Path) -> dict:
    skills, agents, blueprints = {}, set(), set()
    for d in sorted(root.glob("plugins/*/skills/*")):
        if d.is_dir() and (d / "SKILL.md").is_file():
            skills[d.name] = d.parent.parent.name
    for f in sorted(root.glob("plugins/*/agents/*.md")):
        agents.add(f.stem)
    # agentic-os ships its agents as templates rendered at install time.
    for f in sorted(root.glob("plugins/agentic-os/templates/agents/**/*.md.tmpl")):
        agents.add(f.name[: -len(".md.tmpl")])
    # A skill's own subagent briefs are referenceable by name from its prose.
    for f in sorted(root.glob("plugins/*/skills/*/references/subagents/*.md")):
        agents.add(f.stem)
    catalog = root / "plugins/agentic-qe/skills/qe-blueprints/references/catalog"
    for f in sorted(catalog.rglob("*.md")):
        blueprints.add(f.stem)
    return {"skills": skills, "agents": agents, "blueprints": blueprints}


def resolves(name: str, inv: dict, external: set) -> bool:
    """A reference resolves if it names something that ships, or is declared
    external. `plugin:skill` must additionally agree about the plugin."""
    if name in external:
        return True
    if ":" in name:
        plugin, _, bare = name.partition(":")
        return inv["skills"].get(bare) == plugin
    return (name in inv["skills"] or name in inv["agents"]
            or name in inv["blueprints"])


def scan_files(root: Path, policy: dict) -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True,
                         text=True, check=True).stdout.split("\n")
    suffixes = set(policy["scan"]["suffixes"])
    excludes = policy["scan"]["exclude_globs"]
    keep = []
    for rel in out:
        if not rel:
            continue
        if any(fnmatch.fnmatch(rel, g) for g in excludes):
            continue
        p = root / rel
        if not p.is_file() or p.suffix not in suffixes:
            continue
        keep.append(p)
    return keep


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------

def run_checks(root: Path, policy: dict, emit_graph: bool = False) -> None:
    inv = build_inventory(root)
    known = set(inv["skills"]) | inv["agents"] | inv["blueprints"]
    external = set(policy["known_external_refs"])
    legacy = policy["legacy_commands"]
    guards = policy["shape_guards"]

    files = scan_files(root, policy)
    graph: list[tuple[str, str, str]] = []
    unresolved: list[tuple[str, str, str]] = []
    marked_total = 0

    for p in files:
        rel = str(p.relative_to(root))
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for name in marked_refs(text):
            marked_total += 1
            if resolves(name, inv, external):
                graph.append((rel, name, "marked"))
            else:
                unresolved.append((rel, name, "marked reference"))

        for plugin, name, kind in registry_rows(text):
            want = inv["skills"].get(name)
            if kind == "skill" and want == plugin:
                graph.append((rel, name, "registry"))
            elif kind == "blueprint" and name in inv["blueprints"]:
                graph.append((rel, name, "registry"))
            elif kind == "skill" and want:
                unresolved.append((rel, name,
                                   "registry row claims plugin %s but the skill "
                                   "ships from %s" % (plugin, want)))
            else:
                unresolved.append((rel, name, "registry row names no shipped %s" % kind))

        for cmd in set(SLASH_CMD.findall(text)):
            if cmd not in legacy:
                unresolved.append((rel, cmd, "slash command is not declared in "
                                             "legacy_commands"))

        if rel.endswith("docs/setup/app.js"):
            for name in appjs_refs(text):
                if resolves(name, inv, external):
                    graph.append((rel, name, "setup-site"))
                else:
                    unresolved.append((rel, name, "setup site lists a skill that "
                                                  "does not ship"))

        if rel in HTML_PAGES:
            entries = html_entries(text)
            ids = set(html_ids(text))
            if len(ids) < guards["min_html_ids"]:
                report(False, rel, "only %d inventory ids found (expected >= %d) "
                                   "— has the page changed shape? this check "
                                   "would pass blindly"
                       % (len(ids), guards["min_html_ids"]))
            for node_id, srcs in entries:
                for src in srcs:
                    m = re.match(r"skills/([a-z0-9-]+)/SKILL\.md$", src)
                    if m and m.group(1) != node_id:
                        unresolved.append((rel, node_id,
                                           "inventory id disagrees with its source "
                                           "path skills/%s/" % m.group(1)))
                    if not (p.parent / src).exists():
                        unresolved.append((rel, src, "inventory src path does not exist"))
            for a, b in html_edges(text):
                for endpoint in (a, b):
                    if endpoint not in ids:
                        unresolved.append((rel, endpoint,
                                           "diagram edge points at an id that is "
                                           "not on the page"))

    # Preset arrays and skill frontmatter — typed, so parsed structurally.
    for f in sorted(root.glob("plugins/agentic-os/presets/**/*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rel = str(f.relative_to(root))
        for name in data.get("sdlc_skills", []) or []:
            if name in inv["skills"]:
                graph.append((rel, name, "preset"))
            else:
                unresolved.append((rel, name, "preset claims a skill that does not ship"))
        for name in data.get("qe_blueprints", []) or []:
            if name in inv["blueprints"]:
                graph.append((rel, name, "preset"))
            else:
                unresolved.append((rel, name, "preset claims a blueprint that does not ship"))

    for value in legacy.values():
        if value not in inv["skills"]:
            unresolved.append(("skill-refs-policy.json", value,
                               "legacy_commands maps to a skill that does not ship"))

    banned = policy.get("banned_names", {})
    frozen = set(policy.get("frozen_literals", {}))
    overlap = sorted(set(banned) & frozen)
    report(not overlap, "policy",
           "no frozen literal is also banned" if not overlap
           else "frozen literals listed as banned: %s" % ", ".join(overlap))

    registry = root / "plugins/agentic-os/templates/governance/agent-registry.md.tmpl"
    if registry.is_file():
        rows = registry_rows(registry.read_text(encoding="utf-8"))
        report(len(rows) >= guards["min_registry_rows"], "agent-registry.md.tmpl",
               "%d routing rows parsed (>= %d expected)"
               % (len(rows), guards["min_registry_rows"]))

    report(marked_total >= guards["min_marked_refs"], "scan",
           "%d marked references found across %d files (>= %d expected)"
           % (marked_total, len(files), guards["min_marked_refs"]))

    if emit_graph:
        for rel, name, form in sorted(set(graph)):
            print("%s\t%s\t%s" % (rel, name, form))
        return

    if unresolved:
        for rel, name, why in sorted(set(unresolved)):
            hint = did_you_mean(name, known)
            report(False, rel, "%s: %s%s" % (why, name, hint))
    else:
        report(True, "cross-references",
               "%d references across %d files all resolve (%d skills, %d agents, "
               "%d blueprints on disk)"
               % (len(graph), len(files), len(inv["skills"]), len(inv["agents"]),
                  len(inv["blueprints"])))


def did_you_mean(name: str, known: set) -> str:
    best = [k for k in known if _edit_distance(name, k) <= 2]
    return "  (did you mean: %s?)" % ", ".join(sorted(best)[:3]) if best else ""


def _edit_distance(a: str, b: str) -> int:
    if abs(len(a) - len(b)) > 2:
        return 99
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def check_banned(root: Path, policy: dict) -> None:
    """Retired names must appear nowhere — bare substrings, not just marked refs.

    Deliberately blunter than the main check: a rename is complete only when the
    old name is gone from prose too, and prose is exactly where the main check
    is designed not to look."""
    banned = policy.get("banned_names", {})
    if not banned:
        return report(True, "banned-names", "no names are retired right now")
    hits = []
    for p in scan_files(root, policy):
        rel = str(p.relative_to(root))
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name in banned:
            for i, line in enumerate(text.splitlines(), 1):
                if name in line:
                    hits.append((rel, i, name))
    if hits:
        for rel, line, name in hits[:40]:
            report(False, "%s:%d" % (rel, line), "retired name still present: %s "
                                                 "(%s)" % (name, banned[name]))
        if len(hits) > 40:
            report(False, "banned-names", "... and %d more" % (len(hits) - 40))
    else:
        report(True, "banned-names",
               "all %d retired names are gone" % len(banned))


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------

def self_test() -> None:
    # Every fixture below uses a deliberately synthetic name. A fixture that
    # names a real skill is rewritten by any repo-wide rename sweep, and because
    # this file is exempt from the scan, nothing would catch the damage — an
    # earlier draft had `_edit_distance("qa-planner", ...)` silently rewritten
    # into a comparison of a string with itself, which passes vacuously.
    got = marked_refs("hand off to the `example-skill` skill when ready")
    report(got.count("example-skill") >= 1, "self-test",
           "extracts a marked skill reference (%r)" % got)

    report(marked_refs("this is a `breaking-change` in the API") == [],
           "self-test", "ordinary hyphenated prose is not a reference")

    report(marked_refs("the `code` block and `status` field") == [],
           "self-test", "single words without a hyphen are never extracted")

    report(marked_refs("Call `other-example` with the gate id") == ["other-example"],
           "self-test", "an imperative hand-off is a reference")

    rows = registry_rows("| x | the agentic-sdlc `example-skill` skill | y |")
    report(rows == [("agentic-sdlc", "example-skill", "skill")], "self-test",
           "registry row yields (plugin, name, kind) (%r)" % rows)

    entries = html_entries('{id:"a", src:["skills/a/SKILL.md"]}, {id:"b"}')
    report(entries == [("a", ["skills/a/SKILL.md"]), ("b", [])], "self-test",
           "html inventory yields ids with their sources (%r)" % entries)

    report(html_edges('edges:[["a", "b", "why"], ["b", "c", "how"]]')
           == [("a", "b"), ("b", "c")], "self-test",
           "diagram edges yield their endpoints")

    report(appjs_refs("{ say: 'x', skill: 'example-skill' },\n{ name: 'other-example' }")
           == ["example-skill", "other-example"], "self-test",
           "setup-site entries yield their skill names")

    report(SLASH_CMD.findall("run /sdlc:example now") == ["/sdlc:example"],
           "self-test", "legacy slash commands are extracted")

    report(_edit_distance("example-skill", "other-example") > 2
           and _edit_distance("example-skill", "example-skil") == 1,
           "self-test", "edit distance drives the did-you-mean hint")

    # The shape guard: an extractor that stops matching must fail, not pass.
    report(marked_refs("") == [], "self-test", "empty input yields nothing")
    inv = build_inventory(ROOT)
    report(len(inv["skills"]) >= 25 and len(inv["blueprints"]) >= 10, "self-test",
           "inventory reads %d skills and %d blueprints off disk"
           % (len(inv["skills"]), len(inv["blueprints"])))
    report("definitely-not-a-real-skill" not in inv["skills"], "self-test",
           "resolver reports a made-up name as absent")


def main() -> None:
    args = sys.argv[1:]
    if "--self-test" in args:
        self_test()
        sys.exit(fail)
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if "--banned-names" in args:
        check_banned(ROOT, policy)
        sys.exit(fail)
    run_checks(ROOT, policy, emit_graph="--graph" in args)
    sys.exit(fail)


if __name__ == "__main__":
    main()
