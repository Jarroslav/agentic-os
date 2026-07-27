#!/usr/bin/env python3
"""Contract checks for the devops incident-triage pair (installed guide +
agent contract) and the devops preset eval fixture."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def fail(message: str) -> None:
    print("FAIL:", message)
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: check-incident-triage.py <target> <evals>")
    target = Path(sys.argv[1])
    evals_path = Path(sys.argv[2])

    guide = target / ".agentic/guides/standards/incident-triage.md"
    contract = target / ".agentic/agents/incident-triage.md"
    if not guide.exists():
        fail("incident-triage guide was not installed")
    if not contract.exists():
        fail("incident-triage agent contract was not installed")

    pair = guide.read_text() + contract.read_text()
    pair_lower = pair.lower()
    for required in (
        "speculative — no direct evidence",
        "of 3 slots evidence-backed",
        "allowlist",
        "AGENTIC_INCIDENT_TRIAGE_DISABLED=1",
        "a bound without a unit is not a bound",
        "never mutates cluster",
    ):
        if required.lower() not in pair_lower:
            fail(f"installed triage pair missing {required!r}")
    # Vendor-specific integrations never belong in the shipped triage text —
    # allowlists are recorded per-repo by the owner, not hardcoded here.
    for forbidden in ("mcp__", "kubectl", "terraform", "gcloud"):
        if forbidden.lower() in pair_lower:
            fail(f"installed triage pair hardcodes a vendor tool: {forbidden!r}")
    if "readonly: true" not in contract.read_text():
        fail("incident-triage contract is not readonly")

    data = json.loads(evals_path.read_text())
    if data.get("role") != "devops":
        fail("devops evals role mismatch")
    cases = data.get("evals", [])
    if len(cases) < 8:
        fail("devops evals must cover at least eight scenarios")
    ids = {case.get("id") for case in cases}
    if ids != set(range(1, len(cases) + 1)):
        fail(f"devops eval ids must be exactly 1..{len(cases)}, got {sorted(ids)}")
    for case in cases:
        for key in ("prompt", "expected_output"):
            if not isinstance(case.get(key), str) or not case[key].strip():
                fail(f"eval {case.get('id')} missing {key}")

    print("incident triage: installed pair + eval fixture pass")


if __name__ == "__main__":
    main()
