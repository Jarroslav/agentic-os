#!/usr/bin/env python3
"""Detect whether agentic-init should scaffold or adopt an existing fleet."""

from __future__ import annotations
import json
import sys
from pathlib import Path


def files_under(root: Path, relative: str, pattern: str) -> list[str]:
    directory = root / relative
    if not directory.is_dir():
        return []
    return sorted(str(path.relative_to(root)) for path in directory.glob(pattern))


def detect(root: Path) -> dict:
    neutral_agents = files_under(root, ".agents/agents", "*.md")
    legacy_agents = files_under(root, ".agentic/agents", "*.md")
    adopted = {
        "agents": neutral_agents,
        "skills": files_under(root, ".agents/skills", "*/SKILL.md"),
        "shared_hooks": files_under(root, ".agents/hooks", "*.py"),
        "codex_agents": files_under(root, ".codex/agents", "*.toml"),
        "codex_rules": files_under(root, ".codex/rules", "*.rules"),
        "claude_adapters": files_under(root, ".claude/agents", "*.md"),
        "cursor_adapters": files_under(root, ".cursor/agents", "*.md"),
    }
    conflicts = []
    if neutral_agents and legacy_agents:
        conflicts.append("both .agents/agents and .agentic/agents contain contracts")
    mode = "adopt-existing" if any(adopted.values()) else "fresh"
    return {
        "schema": 1,
        "mode": mode,
        "canonical_agents_dir": ".agents/agents/" if neutral_agents else ".agentic/agents/",
        "canonical_skills_dir": ".agents/skills/" if adopted["skills"] else None,
        "state_dir": ".agents/state/" if (root / ".agents").exists() else ".agentic/state/",
        "adopted": adopted,
        "conflicts": conflicts,
    }


def main() -> int:
    result = detect(Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result["conflicts"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
