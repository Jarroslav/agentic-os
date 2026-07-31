#!/usr/bin/env python3
"""Telemetry allowlist checks — the deny-by-default field lists in
`observability-adapters.md`, the projector's own constants, and the emitted
schema must all agree, and a real projector run against a fixture carrying
free-form text must never leak that text.

Why this exists: the projector's safety property is "nothing forwards unless
it's named on the allowlist." That property is only real if the allowlist the
doc promises is the allowlist the code enforces — a doc that says one thing
while the script does another is worse than no doc at all, because it reads
as a guarantee. This check parses the three `<!-- allowlist:X -->` blocks in
`plugins/agentic-sdlc/references/observability-adapters.md` and diffs them
against the projector's constants, then runs the projector against an in-code
fixture containing free text and asserts none of it survives.

Usage:
  check-telemetry-allowlist.py               run the checks
  check-telemetry-allowlist.py --self-test   prove the block extractor works

Exit 0 clean (or self-test pass), 1 on any finding."""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "plugins/agentic-sdlc/references/observability-adapters.md"
SCHEMA = ROOT / "plugins/agentic-sdlc/references/schemas/telemetry-record.schema.json"
PROJECTOR = ROOT / "plugins/agentic-sdlc/scripts/export-run-telemetry.py"

fail = 0


def report(ok: bool, what: str) -> None:
    global fail
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok:
        fail = 1


BLOCK_RE_TMPL = r"<!-- allowlist:%s -->\n(.*?)\n<!-- /allowlist:%s -->"


def extract_block(text: str, name: str) -> set[str]:
    m = re.search(BLOCK_RE_TMPL % (name, name), text, re.DOTALL)
    if not m:
        return set()
    return {tok.strip() for tok in m.group(1).split(",") if tok.strip()}


def load_projector():
    spec = importlib.util.spec_from_file_location("ert", PROJECTOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DENIED_FIELD_NAMES = {"summary", "rationale", "verdict", "prior_context", "artifacts"}


def check_doc_matches_code() -> None:
    text = DOC.read_text(encoding="utf-8")
    ert = load_projector()

    events_doc = extract_block(text, "events")
    decisions_doc = extract_block(text, "decisions")
    data_doc = extract_block(text, "data")

    events_code = {"_time", "stream"} | set(ert.EVENT_FIELDS) | {"artifact_count", "duration_ms"}
    decisions_code = ({"_time", "stream", "run_id"} | set(ert.DECISION_FIELDS)
                       | {"decision", "source", "confidence", "risk_flags", "follow_up_count"})
    data_code = set(ert.DATA_ALLOWLIST)

    report(events_doc == events_code, "events allowlist: doc matches code (%s)"
           % (events_doc ^ events_code or "exact match"))
    report(decisions_doc == decisions_code, "decisions allowlist: doc matches code (%s)"
           % (decisions_doc ^ decisions_code or "exact match"))
    report(data_doc == data_code, "data{} allowlist: doc matches code (%s)"
           % (data_doc ^ data_code or "exact match"))


def check_schema_excludes_denied_names() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    props = set(schema.get("properties", {}))
    overlap = props & DENIED_FIELD_NAMES
    report(not overlap, "telemetry-record.schema.json declares no denied field (%s)"
           % (sorted(overlap) or "clean"))


def check_projector_drops_free_text() -> None:
    ert = load_projector()
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp) / "20260713-1200-fixture"
        run_dir.mkdir()
        secret_summary = "ticket contains a customer name and internal notes"
        secret_rationale = "approved because the linked spec section covers it"
        secret_prior_context = {"embedded_secret": "do-not-forward-this-value"}

        events_line = json.dumps({
            "schema": 1, "ts": "2026-07-13T12:00:00Z", "event": "phase.completed",
            "run_id": "r1", "phase": 1, "actor": "sdlc-engine",
            "summary": secret_summary, "artifacts": ["docs/superpowers/spec.md"],
            "data": {"status": "ok", "unlisted_key": "should-be-dropped"},
        })
        decisions_line = json.dumps({
            "ts": "2026-07-13T12:01:00Z", "gate_id": "spec.approved", "mode": "autonomous",
            "verdict": {"decision": "approve", "rationale": secret_rationale,
                        "source": "deterministic", "confidence": "high", "risk_flags": []},
            "escalated": False, "prior_context": secret_prior_context,
        })
        (run_dir / "events.jsonl").write_text(events_line + "\n", encoding="utf-8")
        (run_dir / "decisions.jsonl").write_text(decisions_line + "\n", encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, str(PROJECTOR), "--run", str(run_dir)],
            capture_output=True, text=True, check=False,
        )
        report(proc.returncode == 0, "projector exits 0 against the fixture")
        stdout = proc.stdout

        for leak, label in (
            (secret_summary, "summary text"),
            (secret_rationale, "verdict.rationale text"),
            ("do-not-forward-this-value", "prior_context value"),
            ("docs/superpowers/spec.md", "artifacts[] path"),
            ("should-be-dropped", "unlisted data{} key value"),
        ):
            report(leak not in stdout, "projector output does not leak %s" % label)

        out_lines = [json.loads(line) for line in stdout.splitlines() if line.strip()]
        report(all(rec.get("run_id") for rec in out_lines),
               "every emitted record carries run_id (%d records)" % len(out_lines))


def self_test() -> None:
    sample = "<!-- allowlist:x -->\na, b, c\n<!-- /allowlist:x -->"
    report(extract_block(sample, "x") == {"a", "b", "c"}, "self-test",)
    report(extract_block(sample, "y") == set(), "self-test: missing block yields empty set")


def main() -> None:
    if "--self-test" in sys.argv[1:]:
        self_test()
        sys.exit(fail)
    check_doc_matches_code()
    check_schema_excludes_denied_names()
    check_projector_drops_free_text()
    sys.exit(fail)


if __name__ == "__main__":
    main()
