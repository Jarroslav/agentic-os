#!/usr/bin/env python3
"""Claude Code UserPromptSubmit hook — secret/PII prompt guard.

stdin:  {"session_id": ..., "prompt": "..."}
stdout: an advisory note (warn mode / PII class), nothing when clean
stderr: the block reason (block mode only)
exit:   0 allow — 2 block the prompt (block mode, secret-class finding only)

The file-read deny rules in .claude/settings.json keep agents out of .env
files; this guard covers the other leak path — a credential pasted straight
into the prompt — BEFORE it is sent anywhere. Detection is by GENERIC shape
classes only (no vendor pattern catalog to maintain):

  private_key            -----BEGIN ... PRIVATE KEY----- block headers
  jwt                    three dot-separated base64url segments (eyJ...)
  credential_assignment  key/secret/token/password = <16+ char value>
  basic_auth_url         scheme://user:password@host
  card_number            13-19 digit runs that pass the Luhn check
  high_entropy_secret    24+ char base64-ish token near a credential keyword
  nl_disclosure          "my/the password|api key|token is <value>"
  email (PII, warn-only) non-example-domain email addresses

Modes via AGENTIC_PROMPT_SCAN_MODE: "warn" (default — advisory, never blocks),
"block" (secret-class findings exit 2), "audit" (silent; findings logged).
Findings are also appended, best-effort and with values MASKED, to
.agentic/state/prompt-scan-audit.jsonl. The hook never echoes a matched value
back in full. Fails open (exit 0) on any internal error.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys

SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    "credential_assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|passwd|password|credential)s?\b"
        r"\s*[:=]\s*[\"']?(?![<$({\[])[A-Za-z0-9+/_.\-]{16,}"),
    "basic_auth_url": re.compile(r"(?i)\bhttps?://[^/\s:@]+:[^/\s:@]{6,}@"),
    "nl_disclosure": re.compile(
        r"(?i)\b(?:my|the|our)\s+(?:password|api[ _-]?key|secret|token|passphrase)\s+is\s+:?\s*"
        r"(?!expired\b|invalid\b|missing\b|wrong\b|empty\b|null\b|undefined\b|broken\b|"
        r"not\b|no\b|gone\b|stale\b|revoked\b|rotated\b|the\b|in\b|stored\b|set\b|fine\b|"
        r"ok\b|okay\b|correct\b|working\b|different\b|unchanged\b|hidden\b)\S{6,}"),
}
PII_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
}
EMAIL_ALLOW = re.compile(r"(?i)@example\.(?:com|org|net)$|^noreply@|@users\.noreply\.github\.com$")
CARD_CANDIDATE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
ENTROPY_TOKEN = re.compile(r"\b[A-Za-z0-9+/=_-]{24,}\b")
CRED_KEYWORD = re.compile(r"(?i)\b(?:api[ _-]?key|secret|token|password|credential|bearer|auth)\b")


def luhn_ok(digits: str) -> bool:
    if len(set(digits)) == 1:
        return False
    total, alt = 0, False
    for ch in reversed(digits):
        d = ord(ch) - 48
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def shannon_bits(token: str) -> float:
    counts: dict[str, int] = {}
    for ch in token:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(token)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def mask(value: str) -> str:
    return value[:4] + "…" + ("%d chars" % len(value))


def find(prompt: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    secrets, pii = [], []
    for name, rx in SECRET_PATTERNS.items():
        for m in rx.finditer(prompt):
            secrets.append((name, mask(m.group(0))))
    for m in CARD_CANDIDATE.finditer(prompt):
        digits = re.sub(r"[ -]", "", m.group(0))
        if 13 <= len(digits) <= 19 and luhn_ok(digits):
            secrets.append(("card_number", mask(digits)))
    if CRED_KEYWORD.search(prompt):
        for m in ENTROPY_TOKEN.finditer(prompt):
            tok = m.group(0)
            if shannon_bits(tok) > 4.5:
                secrets.append(("high_entropy_secret", mask(tok)))
    for name, rx in PII_PATTERNS.items():
        for m in rx.finditer(prompt):
            if name == "email" and EMAIL_ALLOW.search(m.group(0)):
                continue
            pii.append((name, mask(m.group(0))))
    return secrets, pii


def audit(session_id: str, findings: list[tuple[str, str]], mode: str) -> None:
    try:
        os.makedirs(".agentic/state", exist_ok=True)
        with open(".agentic/state/prompt-scan-audit.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "session_id": session_id, "mode": mode,
                "findings": [{"class": c, "masked": v} for c, v in findings],
            }) + "\n")
    except OSError:
        pass


def main() -> None:
    mode = os.environ.get("AGENTIC_PROMPT_SCAN_MODE", "warn").strip().lower()
    if mode not in ("warn", "block", "audit"):
        mode = "warn"
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)
    prompt = event.get("prompt") if isinstance(event, dict) else None
    if not isinstance(prompt, str) or not prompt:
        sys.exit(0)

    try:
        secrets, pii = find(prompt)
    except Exception:
        sys.exit(0)  # fail open — scanning must never break prompting
    if not secrets and not pii:
        sys.exit(0)

    audit(str(event.get("session_id", "")), secrets + pii, mode)
    if mode == "audit":
        sys.exit(0)

    summary = ", ".join(sorted({c for c, _ in secrets})) or ", ".join(sorted({c for c, _ in pii}))
    if secrets and mode == "block":
        sys.stderr.write(
            "[prompt-scan] BLOCKED: the prompt appears to contain secret material "
            "(%s). Remove the value (reference it by env var or file path instead) "
            "and resend. Set AGENTIC_PROMPT_SCAN_MODE=warn to downgrade this guard.\n"
            % summary
        )
        sys.exit(2)
    sys.stdout.write(
        "[prompt-scan] heads-up: the prompt looks like it contains %s (%s). "
        "Prefer env-var or file-path references over pasted values.\n"
        % ("secret material" if secrets else "personal data", summary)
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
