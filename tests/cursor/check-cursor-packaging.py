#!/usr/bin/env python3
"""Validate Cursor plugin packaging for agentic-os.

Checks the repo-root marketplace and per-plugin manifests resolve to real
skills/ and agents/ trees — the minimum Cursor needs to load the plugins.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def fail(msg: str) -> None:
    print(f"FAIL {msg}")
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"ok   {msg}")


def main() -> None:
    marketplace_path = ROOT / ".cursor-plugin" / "marketplace.json"
    if not marketplace_path.is_file():
        fail("missing .cursor-plugin/marketplace.json")

    marketplace = json.loads(marketplace_path.read_text())
    if marketplace.get("name") != "agentic-os":
        fail("marketplace name must be agentic-os")

    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or len(plugins) < 2:
        fail("marketplace must list at least two plugins")

    names = {p["name"] for p in plugins}
    if names != {"agentic-os", "agentic-sdlc", "agentic-qe"}:
        fail(f"unexpected plugin names: {sorted(names)}")

    for entry in plugins:
        name = entry["name"]
        source = ROOT / entry["source"].removeprefix("./")
        if not source.is_dir():
            fail(f"plugin source missing: {source}")

        manifest = source / ".cursor-plugin" / "plugin.json"
        if not manifest.is_file():
            fail(f"missing Cursor manifest for {name}: {manifest}")

        data = json.loads(manifest.read_text())
        if data.get("name") != name:
            fail(f"{name} manifest name mismatch")

        skills_rel = data.get("skills")
        if not skills_rel:
            fail(f"{name} manifest missing skills path")
        skills_dir = (source / skills_rel).resolve()
        if not skills_dir.is_dir():
            fail(f"{name} skills dir missing: {skills_dir}")

        skill_files = list(skills_dir.glob("*/SKILL.md"))
        if not skill_files:
            fail(f"{name} has no skills/*/SKILL.md files")

        ok(f"{name}: {len(skill_files)} skills under {skills_rel}")

        agents_rel = data.get("agents")
        if agents_rel:
            agents_dir = (source / agents_rel).resolve()
            if not agents_dir.is_dir():
                fail(f"{name} agents dir missing: {agents_dir}")
            agent_files = list(agents_dir.glob("*.md"))
            if not agent_files:
                fail(f"{name} has no agents/*.md files")
            ok(f"{name}: {len(agent_files)} agents under {agents_rel}")

    init_skill = ROOT / "plugins/agentic-os/skills/agentic-init/SKILL.md"
    if not init_skill.is_file():
        fail("agentic-init skill missing")
    ok("agentic-init skill present")

    print(f"CURSOR-PACKAGING: {len(plugins)} plugins validated")


if __name__ == "__main__":
    main()
