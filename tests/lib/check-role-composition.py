#!/usr/bin/env python3
"""Behavior checks for explicit role selection and additive composition."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def fail(message: str) -> None:
    print("FAIL:", message)
    raise SystemExit(1)


def load(target: Path) -> tuple[dict, set[str]]:
    journal = json.loads((target / ".agentic/agentic-os/install.json").read_text())
    files = set(journal["files"])
    return journal, files


def require(files: set[str], path: str) -> None:
    if path not in files:
        fail(f"expected installed asset: {path}")


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("usage: check-role-composition.py <ba-po> <mixed> <mcp-state> <unavailable>")

    ba_po = Path(sys.argv[1])
    mixed = Path(sys.argv[2])
    mcp_state = Path(sys.argv[3])
    unavailable = Path(sys.argv[4])

    journal, files = load(ba_po)
    answers = journal["answers"]
    if answers["presets"] != ["ba-po"]:
        fail(f"ba-po install recorded unexpected presets: {answers['presets']!r}")
    if answers["mcp_state"] != "without-mcp":
        fail("no-MCP path was not recorded")
    require(files, ".agentic/agents/dispatcher.md")
    require(files, ".agentic/guides/standards/ba-po-operating-model.md")
    if any(".agentic/agents/" in p and name in p for p in files for name in
           ("blind-code-reviewer", "security-reviewer", "schema-architect", "api-author")):
        fail("ba-po-only install contains developer/code-writing agents")
    if any(p.startswith(".githooks/") or p == "scripts/install-git-hooks.sh" for p in files):
        fail("ba-po-only install contains undeclared git-hook assets")
    readiness = (ba_po / ".agentic/guides/project.md").read_text()
    if "without MCP" not in readiness or "Power BI" not in readiness:
        fail("ba-po readiness guidance lacks no-MCP business path")

    journal, files = load(mixed)
    if journal["answers"]["presets"] != ["ba-po", "developer"]:
        fail("additive role re-run did not record the complete preset union")
    for path in (".agentic/agents/dispatcher.md", ".agentic/agents/security-reviewer.md"):
        require(files, path)
    registry = (mixed / ".agentic/guides/agent-registry.md").read_text()
    if registry.count("dispatcher.md") != 1:
        fail("shared dispatcher asset was duplicated")

    journal, files = load(mcp_state)
    if journal["answers"]["mcp_state"] != "configured":
        fail("configured MCP state was not recorded")
    mcp = (mcp_state / ".agentic/guides/project.md").read_text()
    mcp += (mcp_state / ".agentic/guides/standards/mcp-onboarding.md").read_text()
    for text in (".cursor/mcp.json", ".mcp.json", "cursor-agent mcp list", "claude mcp list"):
        if text not in mcp:
            fail(f"MCP guidance missing {text}")

    journal, _ = load(unavailable)
    if journal["answers"]["mcp_state"] != "unavailable":
        fail("unavailable MCP state was not recorded")
    unavailable_project = (unavailable / ".agentic/guides/project.md").read_text()
    if "do not block requirements work" not in unavailable_project:
        fail("unavailable MCP path does not provide a no-blocker fallback")

    print("role composition: ba-po isolation, additive union, and MCP states pass")


if __name__ == "__main__":
    main()
