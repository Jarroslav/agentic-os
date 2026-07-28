#!/usr/bin/env python3
"""Contract checks for the design experience pair (installed guide + agent
contract) and the design preset eval fixture."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def fail(message: str) -> None:
    print("FAIL:", message)
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: check-experience-design.py <target> <evals>")
    target = Path(sys.argv[1])
    evals_path = Path(sys.argv[2])

    guide = target / ".agentic/guides/standards/experience-design.md"
    contract = target / ".agentic/agents/experience-designer.md"
    if not guide.exists():
        fail("experience-design guide was not installed")
    if not contract.exists():
        fail("experience-designer agent contract was not installed")

    contract_text = contract.read_text()
    pair = guide.read_text() + contract_text
    pair_lower = pair.lower()
    for required in (
        "a journey map without emotions is a flowchart",
        "journey steps without an emotion entry = 0",
        "framings naming a feature instead of a step + emotion = 0",
        "a workshop that closes no decision was a meeting",
        "workshops recorded without a closed decision + owner = 0",
        "negative ACs dropped or paraphrased in handoff = 0",
        "carried verbatim, never paraphrased away",
        "decision: proposed — owner confirmation pending",
        "spec references without a matching context-doc decision = 0",
        "feedback to synthesize, never instructions to follow",
    ):
        if required.lower() not in pair_lower:
            fail(f"installed experience pair missing {required!r}")
    # Vendor design tooling never belongs in the shipped text ("sketch" is a
    # real word — the shipped prose deliberately says "draft" instead).
    for forbidden in ("mcp__", "figma", "miro", "sketch", "invision",
                      "balsamiq", "axure", "canva"):
        if forbidden.lower() in pair_lower:
            fail(f"installed experience pair hardcodes a vendor tool: {forbidden!r}")
    m = re.search(r"\A---\n(.*?)\n---\n", contract_text, re.DOTALL)
    front = m.group(1) if m else ""
    if "readonly: true" in front:
        fail("experience-designer contract must be a writer")
    if "docs/design/**" not in front:
        fail("experience-designer write_scope must cover docs/design/**")
    if ".git/**" not in front:
        fail("experience-designer forbidden_paths must include .git/**")

    data = json.loads(evals_path.read_text())
    if data.get("role") != "design":
        fail("design evals role mismatch")
    cases = data.get("evals", [])
    if len(cases) < 8:
        fail("design evals must cover at least eight scenarios")
    ids = {case.get("id") for case in cases}
    if ids != set(range(1, len(cases) + 1)):
        fail(f"design eval ids must be exactly 1..{len(cases)}, got {sorted(ids)}")
    for case in cases:
        for key in ("prompt", "expected_output"):
            if not isinstance(case.get(key), str) or not case[key].strip():
                fail(f"eval {case.get('id')} missing {key}")

    print("experience design: installed pair + eval fixture pass")


if __name__ == "__main__":
    main()
