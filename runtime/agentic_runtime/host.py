"""Deterministic host capability discovery used by setup and run preflight."""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
import base64
import hashlib
import hmac
import json
import time
from typing import Any, Mapping
from pathlib import Path


def _version(command: str) -> str | None:
    executable = shutil.which(command)
    if not executable:
        return None
    try:
        result = subprocess.run([executable, "--version"], check=True, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or result.stderr.strip() or "present"


def preflight(root: str | Path) -> dict:
    """Report observed capabilities; never claims unsupported sandbox guarantees."""
    root = Path(root)
    return {
        "python": {"available": sys.version_info >= (3, 10), "version": sys.version.split()[0]},
        "sqlite": {"available": sqlite3.sqlite_version_info >= (3, 24, 0), "version": sqlite3.sqlite_version},
        "git": {"available": _version("git") is not None, "version": _version("git")},
        "hosts": {name: {"available": _version(name) is not None, "version": _version(name)} for name in ("claude", "codex", "cursor")},
        "repository": {"root": str(root.resolve()), "git_worktree": (root / ".git").exists()},
        "enforcement": {
            "sqlite_protocol": "enforced",
            "host_identity": "reported_only",
            "os_sandbox": "unsupported",
            "external_effects": "adapter_required",
        },
    }


def _canonical(record: Mapping[str, Any]) -> bytes:
    payload = {key: value for key, value in record.items() if key != "signature"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_dispatch(record: Mapping[str, Any], key: bytes | str) -> dict[str, Any]:
    """Create a deterministic host-issued record using an adapter-held key."""
    secret = key.encode("utf-8") if isinstance(key, str) else bytes(key)
    if not secret:
        raise ValueError("host signing key is required")
    result = dict(record)
    result["signature"] = base64.urlsafe_b64encode(hmac.new(secret, _canonical(result), hashlib.sha256).digest()).decode("ascii")
    return result


def verify_dispatch(record: Mapping[str, Any], key: bytes | str, *, purpose: str,
                    now: float | None = None) -> dict[str, Any]:
    """Verify a short-lived host dispatch record and return its claims."""
    if not isinstance(record, Mapping) or record.get("purpose") != purpose:
        raise ValueError("host dispatch purpose mismatch")
    signature = record.get("signature")
    secret = key.encode("utf-8") if isinstance(key, str) else bytes(key)
    if not secret or not isinstance(signature, str):
        raise ValueError("host dispatch signature is missing")
    try:
        supplied = base64.urlsafe_b64decode(signature.encode("ascii"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("host dispatch signature is malformed") from exc
    expected = hmac.new(secret, _canonical(record), hashlib.sha256).digest()
    if not hmac.compare_digest(supplied, expected):
        raise ValueError("host dispatch signature is invalid")
    issued = record.get("issued_at")
    expires = record.get("expires_at")
    if not isinstance(issued, (int, float)) or not isinstance(expires, (int, float)) or expires <= issued:
        raise ValueError("host dispatch lifetime is invalid")
    current = time.time() if now is None else now
    if current > expires:
        raise ValueError("host dispatch record expired")
    if not isinstance(record.get("record_id"), str) or not record["record_id"]:
        raise ValueError("host dispatch record_id is required")
    if not isinstance(record.get("identity"), str) or not record["identity"]:
        raise ValueError("host dispatch identity is required")
    return dict(record)
