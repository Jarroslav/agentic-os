#!/usr/bin/env python3
"""Run-artifact schema checks — every schema under
plugins/agentic-sdlc/references/schemas/ parses, and the zero-dependency
validator (plugins/agentic-sdlc/scripts/validate-run-artifact.py) accepts a
known-good sample and rejects a known-bad mutation of each. Fixtures live
in-code so a schema can't drift from its validator without failing CI."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "plugins/agentic-sdlc/references/schemas"
VALIDATOR = ROOT / "plugins/agentic-sdlc/scripts/validate-run-artifact.py"

spec = importlib.util.spec_from_file_location("varun", VALIDATOR)
varun = importlib.util.module_from_spec(spec)
spec.loader.exec_module(varun)

fail = 0


def report(ok: bool, what: str) -> None:
    global fail
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok:
        fail = 1


# One (valid, break) pair per schema. `break` mutates the valid sample into
# something the schema must reject.
VALID = {
    "meta.schema.json": {
        "run_id": "20260713-1200-feature-x", "mode": "hitl",
        "started_at": "2026-07-13T12:00:00Z", "task_input": "add x",
        "branch": None, "current_phase": 0, "status": "running",
        "escalate_on": ["security"],
        "loops": {"spec.revision": {"count": 1, "cap": 3, "on_cap": "halt"}},
        "phases": {"0": {"status": "pending"}},
    },
    "event-line.schema.json": {
        "schema": 1, "ts": "2026-07-13T12:00:00Z", "event": "phase.started",
        "run_id": "r", "phase": 0, "actor": "sdlc-pipeline", "summary": "s",
        "artifacts": [], "data": {},
    },
    "decision-line.schema.json": {
        "ts": "2026-07-13T12:00:00Z", "gate_id": "spec.approved", "mode": "hitl",
        "verdict": {"decision": "approve", "rationale": "fine", "source": "hitl"},
        "escalated": False, "prior_context": {},
    },
    "evidence.schema.json": {
        "schema": 1, "task_id": "T1", "test_first": True,
        "failing_test_command": "npm test", "failure_excerpt": "FAIL x",
        "passing_command": "npm test", "passing_excerpt": "PASS x",
        "files_touched": ["a.ts"], "diff_lines_added": 3, "diff_lines_removed": 1,
    },
    "review-bundle.schema.json": {
        "schema": 1, "diff_base": "abc123", "changed_files": ["a.ts"],
        "diffstat": {"files": 1, "added": 3, "removed": 1},
        "risk_flags": [], "evidence_summaries": [], "artifact_refs": [],
    },
    "complexity.schema.json": {
        "score": 18, "routing": "brainstorming", "source": "agent",
        "breakdown": {"component_scope": 3}, "rationale": "medium",
    },
    "verification-evidence.schema.json": {
        "schema": 1, "applies": True, "result": "PASS",
        "feature_id": "login-form", "tool": "playwright",
        "console_errors": [], "network_failures": [],
    },
}
BREAK = {
    "meta.schema.json": lambda d: d.update(status="paused"),          # bad enum
    "event-line.schema.json": lambda d: d.pop("ts"),                  # missing required
    "decision-line.schema.json": lambda d: d["verdict"].update(source="oracle"),
    "evidence.schema.json": lambda d: d.update(test_first="yes"),     # bad type
    "review-bundle.schema.json": lambda d: d["diffstat"].pop("files"),
    "complexity.schema.json": lambda d: d.update(score=99),           # above maximum
    "verification-evidence.schema.json": lambda d: d.update(result="MAYBE"),
}

found = sorted(p.name for p in SCHEMAS.glob("*.schema.json"))
report(found == sorted(VALID), "schema set matches fixture set (%d schemas)" % len(found))

for name in found:
    try:
        schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        report(False, "%s unparseable: %s" % (name, e))
        continue
    if name not in VALID:
        continue
    doc = json.loads(json.dumps(VALID[name]))
    errs = varun.validate_document(doc, schema)
    report(not errs, "%s accepts valid sample %s" % (name, errs[:2] if errs else ""))
    BREAK[name](doc)
    errs = varun.validate_document(doc, schema)
    report(bool(errs), "%s rejects broken sample" % name)

# Loop-entry sub-schema: on_cap outside {halt,escalate} must fail (guards the
# WS2a loop registry contract specifically).
meta = json.loads((SCHEMAS / "meta.schema.json").read_text(encoding="utf-8"))
doc = json.loads(json.dumps(VALID["meta.schema.json"]))
doc["loops"]["spec.revision"]["on_cap"] = "retry-forever"
report(bool(varun.validate_document(doc, meta)), "meta.schema rejects unknown on_cap")

sys.exit(fail)
