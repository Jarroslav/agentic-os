#!/usr/bin/env python3
"""Contract checks for the ba-po-only operating model and adapter safety."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def fail(message: str) -> None:
    print("FAIL:", message)
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: check-ba-po-operating-model.py <target> <evals>")
    target = Path(sys.argv[1])
    evals_path = Path(sys.argv[2])
    guide = target / ".agentic/guides/standards/ba-po-operating-model.md"
    if not guide.exists():
        fail("ba-po operating guide was not installed")
    body = guide.read_text()
    body_lower = body.lower()
    for required in (
        "pasted Excel/Power BI material",
        "read-only MCP data",
        "existing external ticket",
        "input → clarify → local story → local work item → review → approval",
        "product-owner",
        "requirements-intake",
        "prepare_story",
        "read-back",
        "without MCP",
        "Power BI insight",
        "Excel analysis",
        "customer/team clarification",
        "Never call provider-specific APIs",
        "Never create or update an external ticket before explicit approval",
    ):
        if required.lower() not in body_lower:
            fail(f"operating guide missing {required!r}")
    for forbidden in ("mcp__jira", "mcp__github", "mcp__linear", "Jira API", "GitHub API"):
        if forbidden.lower() in body_lower:
            fail(f"operating guide hardcodes provider-specific integration: {forbidden}")

    data = json.loads(evals_path.read_text())
    cases = data.get("evals", [])
    if len(cases) < 10:
        fail("ba-po evals must cover all ten acceptance scenarios")
    ids = {case.get("id") for case in cases}
    if ids != set(range(1, 11)):
        fail(f"ba-po eval ids must be exactly 1..10, got {sorted(ids)}")
    print("ba-po operating model: guide and ten integration scenarios pass")


if __name__ == "__main__":
    main()
