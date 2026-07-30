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
    # Collapse runs of whitespace before matching: these literals are rule
    # statements, not fixed-width strings, and a required sentence must not
    # start failing because the paragraph around it was rewrapped.
    body_lower = " ".join(body.lower().split())
    for required in (
        "pasted Excel/Power BI material",
        "read-only MCP data",
        "existing external ticket",
        "input → clarify → local story → local work item → review → approval",
        "story-author",
        "story-intake",
        "prepare_story",
        "read-back",
        "without MCP",
        "Power BI insight",
        "Excel analysis",
        "customer/team clarification",
        "Never call provider-specific APIs",
        "Never create or update an external ticket before explicit approval",
        # The counted self-checks. Without these the guide states rules a run
        # can claim to have followed but nothing can recompute — the gap that
        # kept the ba-po eval fixture ungradeable against its own guide.
        "external tickets created or updated before explicit approval = 0",
        "adapter syncs recorded as successful without a read-back verification = 0",
        "acceptance criteria invented from missing business context = 0",
        "adapter payloads passed as conversation-only references = 0",
        "provider-specific API calls made outside the declared adapter = 0",
        "local stories discarded on adapter failure = 0",
        "requirements tasks blocked on MCP availability = 0",
        # Shared shape with the other role-behavior guides.
        "## Escalation",
        "## How to propose a change",
    ):
        if " ".join(required.lower().split()) not in body_lower:
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
    by_id = {case["id"]: case for case in cases}
    for case_id, expected_status in ((5, "succeeded"), (6, "failed")):
        receipt = by_id[case_id].get("adapter_receipt")
        if not isinstance(receipt, dict) or receipt.get("schema") != 1:
            fail(f"eval {case_id} is missing a structured normalized receipt")
        if receipt.get("status") != expected_status:
            fail(f"eval {case_id} has wrong receipt status")
        for field in ("work_item", "actions", "state", "assignee", "audit_url", "warnings"):
            if field not in receipt:
                fail(f"eval {case_id} receipt missing {field}")
    if by_id[5].get("read_back", {}).get("acceptance_criteria") is None:
        fail("successful adapter eval is missing read-back verification data")
    if by_id[6].get("read_back") is not None:
        fail("failed adapter eval must not claim a successful read-back")
    lookup = by_id[4].get("lookup_receipt")
    if not isinstance(lookup, dict) or lookup.get("status") != "succeeded":
        fail("external-ticket eval is missing a successful lookup receipt")
    for field in ("external_id", "title", "body", "acceptance_criteria"):
        if field not in lookup:
            fail(f"external-ticket lookup receipt missing {field}")
    print("ba-po operating model: guide and ten integration scenarios pass")


if __name__ == "__main__":
    main()
