#!/usr/bin/env python3
"""Fixture checks for fresh, mature, collision, and idempotent detection."""

import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "plugins/agentic-os/scripts/detect-adoption.py"
spec = importlib.util.spec_from_file_location("adoption_probe", PROBE)
module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(module)


def touch(root: Path, relative: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x\n")


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    fresh = module.detect(root)
    assert fresh["mode"] == "fresh"
    assert fresh["canonical_agents_dir"] == ".agentic/agents/"
    touch(root, ".agents/agents/writer.md")
    touch(root, ".agents/skills/ship/SKILL.md")
    touch(root, ".codex/agents/writer.toml")
    mature = module.detect(root)
    assert mature["mode"] == "adopt-existing"
    assert mature["canonical_agents_dir"] == ".agents/agents/"
    assert mature["state_dir"] == ".agents/state/"
    assert mature == module.detect(root)
    touch(root, ".agentic/agents/other.md")
    assert module.detect(root)["conflicts"]

print("mature adoption fixtures: PASS")
