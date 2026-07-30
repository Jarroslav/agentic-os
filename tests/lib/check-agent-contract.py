#!/usr/bin/env python3
"""Agent-contract checks — every shipped agent contract carries the required
contract blocks from `guides/standards/instruction-quality-rubric.md`
§ Required contract blocks.

Sibling to check-skill-contract.py, which enforces the same routing-negative-space
rule (`Not for:`) on skills. Before this checker existed the rubric's block list
was normative prose enforced on nothing, which is how five QA contracts shipped
without `## Stop and ask when` and five agentic-sdlc agents without `Not for:`.

Covered (no grandfather list):
  plugins/agentic-os/templates/agents/*/*.tmpl   scaffolded contracts
  plugins/agentic-sdlc/agents/*.md               dispatchable sdlc agents
  plugins/agentic-os/generators/exemplars/*.md   what generated contracts copy

Asserted per contract:
  1 `Not for:`            routing negative space, in the YAML frontmatter
  2 `## Decision rules`   present, holding a two-column DO / DON'T table
  3 escalate-never        an escalation section, or a cite of escalation-policy.md
  4 `## Stop and ask when` pre-verdict halt triggers, distinct from escalation

The rubric's fifth block — counted verification criteria — is deliberately NOT
asserted here. It is not mechanically decidable: security-reviewer's
`PASS — N files audited. 0 blocking, K non-blocking.` is a counted criterion no
reasonable pattern separates from prose, and a checker that guesses fails correct
contracts. It stays model-graded by the instruction-auditor.

Deterministic and offline — structure only, no model calls."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

TARGETS = (
    "plugins/agentic-os/templates/agents/*/*.tmpl",
    "plugins/agentic-sdlc/agents/*.md",
    "plugins/agentic-os/generators/exemplars/*.md",
)

# Headings are matched case-insensitively: the exemplars historically used Title
# Case where the templates use sentence case. Normalising the text is the fix;
# tolerating both here keeps this checker from being the only thing holding the
# two conventions apart.
DECISION_RULES = re.compile(r"^##\s+Decision rules\s*$", re.M | re.I)
STOP_AND_ASK = re.compile(r"^##\s+Stop and ask when\s*$", re.M | re.I)
# Two accepted spellings of the rubric's escalate-never-decide list. The
# `## Escalate, never decide` form exists for agents that are contractually
# forbidden from escalating themselves — the sdlc proxies hand the decision to
# gate-arbiter, which owns any human contact. Forcing them to carry an
# `## Escalate to human` section would make the contract contradict itself.
ESCALATION = re.compile(
    r"^##\s+(?:(?:When to )?[Ee]scalat\w*(?: to)?(?: the)? human"
    r"|Escalate, never decide)\s*$",
    re.M | re.I)
# A GFM header row whose two label cells are DO and DON'T (straight or curly
# apostrophe), with or without leading/trailing pipes.
DO_DONT_ROW = re.compile(r"\|?\s*\*{0,2}DO\*{0,2}\s*\|\s*\*{0,2}DON['’]?T\*{0,2}\s*\|",
                         re.I)

# A count, not a 0/1 flag: the per-file `before` comparison below needs it to
# keep rising, or every file after the first failure reports itself ok.
fail = 0


def err(path: Path, msg: str) -> None:
    global fail
    print("  FAIL %s: %s" % (path.relative_to(ROOT), msg))
    fail += 1


def frontmatter(text: str) -> str | None:
    """The raw YAML block between the leading fences, or None.

    Returned whole rather than parsed: descriptions appear as block scalars
    (`description: >`), as double-quoted single lines carrying \\n escapes, and
    as plain single lines. Searching the whole block covers all three without a
    YAML dependency.
    """
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    return m.group(1) if m else None


def section(text: str, heading: re.Pattern) -> str:
    """Body of the first section matching `heading`, up to the next `## `."""
    m = heading.search(text)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = re.search(r"^##\s", rest, re.M)
    return rest[:nxt.start()] if nxt else rest


def check(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    front = frontmatter(text)
    if front is None:
        return err(path, "no YAML frontmatter")
    # A bare unquoted description is a YAML trap: these run to paragraphs and
    # routinely contain `<example>Context:` or `user:`, which a real parser reads
    # as a nested mapping and rejects. story-proxy.md shipped unloadable that way
    # until 2026-07-28. Block scalars and quoted scalars are both safe; asserting
    # the *style* catches the whole class without a pyyaml dependency CI lacks.
    desc = re.search(r"^description:[ \t]*(.*)$", front, re.M)
    if not desc:
        err(path, "frontmatter has no description")
    elif not desc.group(1).lstrip().startswith((">", "|", '"', "'")):
        err(path, "description must be a block (>, |) or quoted scalar — a bare "
                  "value breaks YAML on the first embedded 'word:'")
    # Block 1 — routing negative space. A description that only says what the
    # agent does leaves the router to guess what it doesn't.
    if "Not for:" not in front:
        err(path, "description lacks a 'Not for:' routing clause")

    # Block 2 — judgment calls as a table, not prose.
    if not DECISION_RULES.search(text):
        err(path, "missing '## Decision rules'")
    elif not DO_DONT_ROW.search(section(text, DECISION_RULES)):
        err(path, "'## Decision rules' has no DO / DON'T table")

    # Block 3 — the decisions that are always human-owned.
    if not ESCALATION.search(text) and "escalation-policy.md" not in text:
        err(path, "no escalation section and no escalation-policy.md citation")

    # Block 4 — halts before an artifact exists, unlike escalation which
    # resolves after the verdict.
    if not STOP_AND_ASK.search(text):
        err(path, "missing '## Stop and ask when'")


contracts = sorted(p for pattern in TARGETS for p in ROOT.glob(pattern))
if not contracts:
    print("  FAIL no agent contracts found under %s" % ", ".join(TARGETS))
    sys.exit(1)

for contract in contracts:
    before = fail
    check(contract)
    if fail == before:
        print("  ok   %s" % contract.relative_to(ROOT))

print("agent contracts: %d checked, %d violation(s)" % (len(contracts), fail))
sys.exit(1 if fail else 0)
