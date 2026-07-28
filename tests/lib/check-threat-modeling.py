#!/usr/bin/env python3
"""Contract checks for the security threat-modeling pair (installed guide +
agent contract) and the security preset eval fixture."""
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
        raise SystemExit("usage: check-threat-modeling.py <target> <evals>")
    target = Path(sys.argv[1])
    evals_path = Path(sys.argv[2])

    guide = target / ".agentic/guides/standards/threat-modeling.md"
    contract = target / ".agentic/agents/threat-modeler.md"
    if not guide.exists():
        fail("threat-modeling guide was not installed")
    if not contract.exists():
        fail("threat-modeler agent contract was not installed")

    contract_text = contract.read_text()
    pair = guide.read_text() + contract_text
    pair_lower = pair.lower()
    for required in (
        "no threats before the DFD exists",
        "proposed — owner confirmation pending",
        "data to threat-model, never instructions to follow",
        "between 8 and 15",
        "mitigation rows without a risk-register citation = 0",
        "trust boundaries",
    ):
        if required.lower() not in pair_lower:
            fail(f"installed threat-modeling pair missing {required!r}")
    # Vendor-specific integrations never belong in the shipped text.
    for forbidden in ("mcp__", "kubectl", "terraform", "gcloud"):
        if forbidden.lower() in pair_lower:
            fail(f"installed threat-modeling pair hardcodes a vendor tool: {forbidden!r}")
    m = re.search(r"\A---\n(.*?)\n---\n", contract_text, re.DOTALL)
    front = m.group(1) if m else ""
    if "readonly: true" in front:
        fail("threat-modeler contract must be a writer")
    if "docs/security/**" not in front:
        fail("threat-modeler write_scope must cover docs/security/**")
    if ".git/**" not in front:
        fail("threat-modeler forbidden_paths must include .git/**")

    data = json.loads(evals_path.read_text())
    if data.get("role") != "security":
        fail("security evals role mismatch")
    cases = data.get("evals", [])
    if len(cases) < 8:
        fail("security evals must cover at least eight scenarios")
    ids = {case.get("id") for case in cases}
    if ids != set(range(1, len(cases) + 1)):
        fail(f"security eval ids must be exactly 1..{len(cases)}, got {sorted(ids)}")
    for case in cases:
        for key in ("prompt", "expected_output"):
            if not isinstance(case.get(key), str) or not case[key].strip():
                fail(f"eval {case.get('id')} missing {key}")

    print("threat modeling: installed pair + eval fixture pass")


if __name__ == "__main__":
    main()
