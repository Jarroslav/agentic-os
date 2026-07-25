#!/usr/bin/env python3
"""Claude Code Stop hook — session-learnings capture notice.

stdin:  {"session_id": ..., "transcript_path": ..., "stop_hook_active": ...}
stdout: one advisory line when this session's user messages contain correction
        signals that haven't been noticed yet (same advisory channel as the
        other notice hooks), nothing otherwise
exit:   always 0 — this hook NEVER blocks.

A user who had to repeat an instruction, correct a wrong turn, or ask "did you
run it?" has just paid for a failed attempt. That lesson is worth more than the
turn it cost: captured into the durable memory store (`.agents/memory/<role>/`,
see the agentic-sdlc `role-memory` skill), it prevents the same re-payment on every
future run. This hook only *detects and nudges* — it writes no memory itself,
so capture stays a deliberate act.

Reads only the transcript tail (last 256 KB) and keeps a per-session signal
count in $TMPDIR so an unaddressed nudge doesn't repeat on every Stop — it
speaks again only when NEW signals appear. Set AGENTIC_LEARNINGS_DISABLED=1 to
turn it off. Fails open (exit 0, silent) on any parse or IO problem.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

TAIL_BYTES = 256 * 1024

# Conservative, org-neutral correction signals. Substring match, lowercased.
# Grouped by what the lesson usually is; the group name goes into the nudge.
SIGNALS = {
    "repeated instruction": [
        "i already told you", "i told you", "as i said", "like i said",
        "again, please", "for the second time",
    ],
    "correction": [
        "that's wrong", "that is wrong", "that's incorrect",
        "not what i asked", "you missed", "you forgot",
        "undo that", "revert that", "stop doing",
        "still broken", "still failing", "still doesn't work",
        "still not working",
    ],
    "unverified claim": [
        "did you run", "did you test", "did you check", "did you actually",
        "are you sure",
    ],
    "rework request": [
        "think harder", "read it again", "look again",
    ],
}


def user_texts(transcript_path: str) -> list[str]:
    """User-authored message texts from the transcript tail (JSONL, lenient)."""
    texts: list[str] = []
    try:
        with open(transcript_path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - TAIL_BYTES))
            raw = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return texts
    for line in raw.splitlines():
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict) or obj.get("isMeta"):
            continue
        msg = obj.get("message")
        if not isinstance(msg, dict) or msg.get("role") != "user":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(str(block.get("text", "")))
    return texts


def find_signals(texts: list[str]) -> list[tuple[str, str]]:
    hits = []
    for text in texts:
        low = text.lower()
        for group, phrases in SIGNALS.items():
            for phrase in phrases:
                if phrase in low:
                    hits.append((group, phrase))
    return hits


def state_path(session_id: str) -> str:
    d = os.path.join(tempfile.gettempdir(), "agentic-hooks")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "session-learnings-%s.json" % (session_id or "unknown"))


def main() -> None:
    if os.environ.get("AGENTIC_LEARNINGS_DISABLED"):
        sys.exit(0)
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)
    if not isinstance(event, dict) or event.get("stop_hook_active"):
        sys.exit(0)

    transcript = event.get("transcript_path") or ""
    if not transcript:
        sys.exit(0)

    hits = find_signals(user_texts(transcript))
    if not hits:
        sys.exit(0)

    # Speak only when new signals appeared since the last nudge this session.
    spath = state_path(str(event.get("session_id", "")))
    seen = 0
    try:
        with open(spath, encoding="utf-8") as fh:
            seen = int(json.load(fh).get("count", 0))
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    if len(hits) <= seen:
        sys.exit(0)
    try:
        with open(spath, "w", encoding="utf-8") as fh:
            json.dump({"count": len(hits)}, fh)
    except OSError:
        pass

    groups = sorted({g for g, _ in hits})
    example = hits[-1][1]
    sys.stdout.write(
        "[session-learnings] %d correction signal(s) this session (%s; e.g. \"%s\"). "
        "If there's a durable lesson, capture it with the role-memory skill "
        "(.agents/memory/<role>/) so the next run doesn't repay this turn.\n"
        % (len(hits), ", ".join(groups), example)
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
