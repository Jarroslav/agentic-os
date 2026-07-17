#!/usr/bin/env python3
"""Claude Code PostToolUse hook — context-budget monitor.

stdin:  {"session_id": ..., "transcript_path": ...}
stdout: one advisory line when context usage crosses a threshold level it has
        not announced before in this session, nothing otherwise
exit:   always 0 — this hook NEVER blocks.

Context quality degrades well before the window is full, and the cheap
remedies (checkpoint at the plan→implementation seam, delegate to a
fresh-context subagent, compact) only help if they happen early. This hook is
the early warning; the PreCompact checkpoint hook remains the last-resort save.

Mechanics: every Nth tool call (default 5), parse the transcript tail (last
64 KB) for the most recent `usage` block and compute
(input + cache_read + cache_creation) / window. Announce WARN at 65% and
URGENT at 75% — once per level per session, so it never nags.

Env overrides: AGENTIC_CONTEXT_WARN_PCT, AGENTIC_CONTEXT_URGENT_PCT,
AGENTIC_CONTEXT_WINDOW_TOKENS (default 200000),
AGENTIC_CONTEXT_CHECK_INTERVAL, AGENTIC_CONTEXT_MONITOR_DISABLED=1.
Fails open (exit 0, silent) on any parse or IO problem.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

TAIL_BYTES = 64 * 1024


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, ""))
    except ValueError:
        return default


def latest_usage(transcript_path: str) -> dict | None:
    try:
        with open(transcript_path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - TAIL_BYTES))
            raw = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    for line in reversed(raw.splitlines()):
        if '"usage"' not in line:
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        usage = None
        if isinstance(obj, dict):
            msg = obj.get("message")
            if isinstance(msg, dict) and isinstance(msg.get("usage"), dict):
                usage = msg["usage"]
            elif isinstance(obj.get("usage"), dict):
                usage = obj["usage"]
        if usage and "input_tokens" in usage:
            return usage
    return None


def state_path(session_id: str) -> str:
    d = os.path.join(tempfile.gettempdir(), "agentic-hooks")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "context-monitor-%s.json" % (session_id or "unknown"))


def load_state(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            state = json.load(fh)
            return state if isinstance(state, dict) else {}
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def save_state(path: str, state: dict) -> None:
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(state, fh)
    except OSError:
        pass


def main() -> None:
    if os.environ.get("AGENTIC_CONTEXT_MONITOR_DISABLED"):
        sys.exit(0)
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)
    if not isinstance(event, dict):
        sys.exit(0)
    transcript = event.get("transcript_path") or ""
    if not transcript:
        sys.exit(0)

    spath = state_path(str(event.get("session_id", "")))
    state = load_state(spath)

    interval = max(1, env_int("AGENTIC_CONTEXT_CHECK_INTERVAL", 5))
    calls = int(state.get("calls", 0)) + 1
    state["calls"] = calls
    if calls % interval:
        save_state(spath, state)
        sys.exit(0)

    usage = latest_usage(transcript)
    if not usage:
        save_state(spath, state)
        sys.exit(0)

    window = max(1, env_int("AGENTIC_CONTEXT_WINDOW_TOKENS", 200000))
    used = 0
    for key in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
        v = usage.get(key)
        if isinstance(v, int):
            used += v
    pct = used * 100 // window

    warn = env_int("AGENTIC_CONTEXT_WARN_PCT", 65)
    urgent = env_int("AGENTIC_CONTEXT_URGENT_PCT", 75)
    level = 2 if pct >= urgent else 1 if pct >= warn else 0

    announced = int(state.get("announced_level", 0))
    if level > announced:
        state["announced_level"] = level
        if level == 2:
            sys.stdout.write(
                "[context-monitor] context ~%d%% of the window (URGENT, >=%d%%). "
                "Act now, cheapest first: checkpoint and continue in a fresh session "
                "(the plan->implementation seam if you are near it), or delegate the "
                "remaining work to a fresh-context subagent. PreCompact will save "
                "state as a last resort, but quality degrades before that.\n"
                % (pct, urgent)
            )
        else:
            sys.stdout.write(
                "[context-monitor] context ~%d%% of the window (>=%d%%). Prefer "
                "artifact summaries over full files, delegate self-contained work "
                "to subagents, and plan to checkpoint at the next phase boundary.\n"
                % (pct, warn)
            )
    save_state(spath, state)
    sys.exit(0)


if __name__ == "__main__":
    main()
