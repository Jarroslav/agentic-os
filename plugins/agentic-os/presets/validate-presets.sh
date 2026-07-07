#!/usr/bin/env bash
# Validates role presets: valid JSON, required keys, allowed enum values, and
# every templates/generated entry registered in templates/VARIABLES.md.
# Self-contained (bash + python3). Exit 0 = OK, 1 = findings.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
VARS="$HERE/../templates/VARIABLES.md"
[ -f "$VARS" ] || { echo "VARIABLES.md not found at $VARS" >&2; exit 2; }

python3 - "$VARS" "$HERE"/roles/*.json <<'PY'
import json, re, sys

vars_md = open(sys.argv[1], encoding="utf-8").read()
# Registered IDs are backticked prefix/name tokens in VARIABLES.md
# (placeholder forms like `hooks/<name>` don't match the name charset).
registered = set(re.findall(
    r"`((?:hooks|githooks|scripts|governance|policy|guides|agents|commands|sdlc|gen)"
    r"/[a-z0-9][a-z0-9-]*)`", vars_md))

REQUIRED = ("name", "description", "templates", "generated",
            "default_hitl", "default_orchestration", "sdlc_skills")
HITL = {"strict", "gated-autonomous", "autonomous"}
ORCH = {"pipeline", "dispatcher"}

fail = 0
def err(msg):
    global fail
    print(f"FAIL: {msg}")
    fail = 1

for path in sys.argv[2:]:
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        err(f"{path}: invalid JSON — {e}")
        continue
    for k in REQUIRED:
        if k not in d:
            err(f"{path}: missing key '{k}'")
    if d.get("default_hitl") not in HITL:
        err(f"{path}: default_hitl '{d.get('default_hitl')}' not in {sorted(HITL)}")
    if d.get("default_orchestration") not in ORCH:
        err(f"{path}: default_orchestration '{d.get('default_orchestration')}' not in {sorted(ORCH)}")
    for field in ("templates", "generated"):
        for ref in d.get(field, []):
            if ref not in registered:
                err(f"{path}: {field} entry '{ref}' not registered in VARIABLES.md")

print("validate-presets: " + ("FAIL" if fail else f"OK ({len(sys.argv) - 2} presets, {len(registered)} registered IDs)"))
sys.exit(fail)
PY
