#!/usr/bin/env python3
"""Skill-contract checks — every shipped skill (plugins/*/skills/*/) carries
the three-file contract and each file holds its shape:

  SKILL.md         agent-facing: frontmatter `name` matches the dir,
                   non-empty `description` (the trigger contract)
  README.md        user-facing: "Use It For" / "How To Ask" / "What It Needs"
  evals/evals.json eval metadata: skill_name matches the dir; every eval has
                   id, prompt, expected_output, files[], and >=1 assertion
                   with name + description

Deterministic and offline — schema/structure only, no model calls."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README_HEADINGS = ("## Use It For", "## How To Ask", "## What It Needs")

fail = 0


def err(skill: Path, msg: str) -> None:
    global fail
    print("  FAIL %s: %s" % (skill.relative_to(ROOT), msg))
    fail = 1


def check_skill_md(skill: Path) -> None:
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return err(skill, "SKILL.md has no YAML frontmatter")
    front = m.group(1)
    name = re.search(r"^name:\s*(\S+)\s*$", front, re.MULTILINE)
    if not name or name.group(1) != skill.name:
        return err(skill, "frontmatter name %r != dir %r"
                   % (name and name.group(1), skill.name))
    desc = re.search(r"^description:\s*(.+)$", front, re.MULTILINE)
    if not desc or not desc.group(1).strip():
        return err(skill, "frontmatter description missing or empty")


def check_readme(skill: Path) -> None:
    text = (skill / "README.md").read_text(encoding="utf-8")
    for h in README_HEADINGS:
        if h not in text:
            err(skill, "README.md missing %r section" % h)


def check_evals(skill: Path) -> None:
    path = skill / "evals" / "evals.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return err(skill, "evals.json unparseable: %s" % e)
    if data.get("skill_name") != skill.name:
        err(skill, "evals skill_name %r != dir %r" % (data.get("skill_name"), skill.name))
    evals = data.get("evals")
    if not isinstance(evals, list) or not evals:
        return err(skill, "evals.json has no evals[]")
    for e in evals:
        eid = e.get("id")
        where = "eval id=%r" % eid
        if not isinstance(eid, (int, float)):
            err(skill, "%s: id is not a number" % where)
        for key in ("prompt", "expected_output"):
            if not isinstance(e.get(key), str) or not e[key].strip():
                err(skill, "%s: %s missing or empty" % (where, key))
        if not isinstance(e.get("files"), list):
            err(skill, "%s: files is not an array" % where)
        assertions = e.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            err(skill, "%s: assertions[] missing or empty" % where)
            continue
        for a in assertions:
            for key in ("name", "description"):
                if not isinstance(a.get(key), str) or not a[key].strip():
                    err(skill, "%s: assertion %s missing or empty" % (where, key))


skills = sorted(ROOT.glob("plugins/*/skills/*/"))
if not skills:
    print("  FAIL no skills found under plugins/*/skills/"); sys.exit(1)

for skill in skills:
    missing = [f for f in ("SKILL.md", "README.md", "evals/evals.json")
               if not (skill / f).is_file()]
    if missing:
        err(skill, "missing %s" % ", ".join(missing))
        continue
    before = fail
    check_skill_md(skill)
    check_readme(skill)
    check_evals(skill)
    if fail == before:
        print("  ok   %s" % skill.relative_to(ROOT))

sys.exit(fail)
