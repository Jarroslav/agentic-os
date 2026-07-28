#!/usr/bin/env python3
"""Generic shape check for preset-level eval fixtures: every
presets/evals/<role>.json names its role, matches a real preset, and carries
at least eight complete counted scenarios with contiguous ids. The bespoke
per-role checkers (check-incident-triage.py etc.) keep their literal and
frontmatter checks; this one guarantees every role has a well-formed fixture
at all."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def fail(message: str) -> None:
    print("FAIL:", message)
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: check-preset-evals.py <PLUGIN_ROOT>")
    plugin = Path(sys.argv[1]).resolve()
    evals_dir = plugin / "presets/evals"
    roles_dir = plugin / "presets/roles"
    fixtures = sorted(evals_dir.glob("*.json"))
    if not fixtures:
        fail(f"no eval fixtures under {evals_dir}")

    roles = {p.stem for p in roles_dir.glob("*.json")}
    missing = sorted(roles - {f.stem for f in fixtures})
    if missing:
        fail(f"presets without an eval fixture: {', '.join(missing)}")

    for path in fixtures:
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            fail(f"{path.name} unparseable: {e}")
        if data.get("role") != path.stem:
            fail(f"{path.name}: role {data.get('role')!r} != filename stem")
        if path.stem not in roles:
            fail(f"{path.name}: no preset roles/{path.stem}.json")
        cases = data.get("evals", [])
        if len(cases) < 8:
            fail(f"{path.name}: must cover at least eight scenarios")
        ids = {case.get("id") for case in cases}
        if ids != set(range(1, len(cases) + 1)):
            fail(f"{path.name}: ids must be exactly 1..{len(cases)}, got {sorted(ids)}")
        for case in cases:
            for key in ("prompt", "expected_output"):
                if not isinstance(case.get(key), str) or not case[key].strip():
                    fail(f"{path.name} eval {case.get('id')}: missing {key}")

    print(f"preset evals: {len(fixtures)} fixtures cover all {len(roles)} presets")


if __name__ == "__main__":
    main()
