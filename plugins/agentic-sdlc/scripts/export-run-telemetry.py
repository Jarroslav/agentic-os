#!/usr/bin/env python3
"""Project a run's governance ledgers into redacted NDJSON telemetry records.

Reads `events.jsonl` and `decisions.jsonl` from a run directory and writes one
NDJSON line per source line to stdout, shaped to
`references/schemas/telemetry-record.schema.json`. Writes nothing to disk —
delivery to a backend is the caller's job (see `skills/telemetry-export/` and
`references/observability-adapters.md`).

Deny-by-default: only the fields named in `observability-adapters.md`'s
allowlist tables are ever forwarded. Free-form text (`summary`,
`verdict.rationale`, `prior_context`, `artifacts[]` paths) is dropped, never
truncated or scrubbed — there is no default path for it to reach a backend.

Cursor: this script is idempotent across runs against a growing ledger. It
scans `events.jsonl` for the last `telemetry.export_receipt` line, reads the
raw-line offsets it recorded, and only projects lines strictly after those
offsets. Lines whose `event` starts with `telemetry.` are never themselves
projected (excluding them is what stops export from re-triggering itself on
every turn-end). The final line count consumed from each ledger is printed to
stderr as `CURSOR {"events_offset": N, "decisions_offset": M}` so the caller
can record it in the next receipt.

Usage:
  export-run-telemetry.py --run <run_dir> [--extra-fields a,b,c]

Exit codes: 0 on success (including "nothing new to export", which prints no
stdout lines) · 2 on usage/IO error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Narrow allowlist for events.jsonl's free-form `data{}` object. Values must
# also be scalar and match VALUE_PATTERN — anything else is dropped silently.
DATA_ALLOWLIST = {"status", "state", "kind", "count", "loop", "attempt"}
VALUE_PATTERN = re.compile(r"^[A-Za-z0-9_.:/-]{1,64}$")

EVENT_FIELDS = ("schema", "event", "run_id", "phase", "actor")
DECISION_FIELDS = ("gate_id", "mode", "escalated")


def read_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_line(line: str) -> dict | None:
    try:
        doc = json.loads(line)
    except json.JSONDecodeError:
        return None
    return doc if isinstance(doc, dict) else None


def find_cursor(event_lines: list[str]) -> tuple[int, int]:
    """Last `telemetry.export_receipt`'s recorded offsets, or (0, 0)."""
    events_offset = 0
    decisions_offset = 0
    for line in event_lines:
        doc = parse_line(line)
        if not doc or doc.get("event") != "telemetry.export_receipt":
            continue
        data = doc.get("data") or {}
        eo = data.get("events_offset")
        do = data.get("decisions_offset")
        if isinstance(eo, int):
            events_offset = eo
        if isinstance(do, int):
            decisions_offset = do
    return events_offset, decisions_offset


def project_data(data: dict, extra_fields: set[str]) -> dict:
    allowed = DATA_ALLOWLIST | extra_fields
    out = {}
    if not isinstance(data, dict):
        return out
    for key, value in data.items():
        if key not in allowed:
            continue
        if not isinstance(value, str) or not VALUE_PATTERN.match(value):
            continue
        out[key] = value
    return out


def project_events(all_lines: list[str], new_from: int, extra_fields: set[str]) -> list[dict]:
    # Build a phase -> started-ts map across the WHOLE ledger (not just the
    # new slice) so duration_ms is correct even when phase.started landed in
    # an already-exported batch.
    phase_started: dict[int, str] = {}
    out: list[dict] = []
    for idx, line in enumerate(all_lines):
        doc = parse_line(line)
        if not doc:
            continue
        event = doc.get("event", "")
        phase = doc.get("phase")
        if event == "phase.started" and isinstance(phase, int):
            phase_started[phase] = doc.get("ts", "")

        if idx < new_from:
            continue
        if event.startswith("telemetry."):
            continue  # never project our own export events

        record = {"_time": doc.get("ts", ""), "stream": "events"}
        for field in EVENT_FIELDS:
            if field in doc:
                record[field] = doc[field]
        artifacts = doc.get("artifacts")
        if isinstance(artifacts, list):
            record["artifact_count"] = len(artifacts)
        projected_data = project_data(doc.get("data", {}), extra_fields)
        if projected_data:
            record["data"] = projected_data
        if event == "phase.completed" and isinstance(phase, int) and phase in phase_started:
            dur = duration_ms(phase_started[phase], doc.get("ts", ""))
            if dur is not None:
                record["duration_ms"] = dur
        out.append(record)
    return out


def duration_ms(start_ts: str, end_ts: str) -> int | None:
    try:
        from datetime import datetime

        def parse(ts: str) -> datetime:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))

        delta = parse(end_ts) - parse(start_ts)
        ms = int(delta.total_seconds() * 1000)
        return ms if ms >= 0 else None
    except (ValueError, TypeError):
        return None


def project_decisions(lines: list[str], run_id: str) -> list[dict]:
    out = []
    for line in lines:
        doc = parse_line(line)
        if not doc:
            continue
        record = {"_time": doc.get("ts", ""), "stream": "decisions", "run_id": run_id}
        for field in DECISION_FIELDS:
            if field in doc:
                record[field] = doc[field]
        verdict = doc.get("verdict") or {}
        if "decision" in verdict:
            record["decision"] = verdict["decision"]
        if "source" in verdict:
            record["source"] = verdict["source"]
        if "confidence" in verdict:
            record["confidence"] = verdict["confidence"]
        if "risk_flags" in verdict:
            record["risk_flags"] = verdict["risk_flags"]
        follow_ups = verdict.get("follow_ups")
        if isinstance(follow_ups, list):
            record["follow_up_count"] = len(follow_ups)
        out.append(record)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="run directory containing events.jsonl / decisions.jsonl")
    parser.add_argument("--extra-fields", default="", help="comma-separated additions to the data{} allowlist")
    args = parser.parse_args()

    run_dir = Path(args.run)
    if not run_dir.is_dir():
        sys.stderr.write("export-run-telemetry: %s is not a directory\n" % run_dir)
        sys.exit(2)

    run_id = run_dir.name
    extra_fields = {f.strip() for f in args.extra_fields.split(",") if f.strip()}

    event_lines = read_lines(run_dir / "events.jsonl")
    decision_lines = read_lines(run_dir / "decisions.jsonl")

    events_offset, decisions_offset = find_cursor(event_lines)

    events_out = project_events(event_lines, events_offset, extra_fields)
    decisions_out = project_decisions(decision_lines[decisions_offset:], run_id)

    for record in events_out:
        print(json.dumps(record, sort_keys=True))
    for record in decisions_out:
        print(json.dumps(record, sort_keys=True))

    cursor = {"events_offset": len(event_lines), "decisions_offset": len(decision_lines)}
    sys.stderr.write("CURSOR %s\n" % json.dumps(cursor, sort_keys=True))


if __name__ == "__main__":
    main()
