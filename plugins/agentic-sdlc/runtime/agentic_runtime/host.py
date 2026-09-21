"""Deterministic host capability discovery used by setup and run preflight."""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
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
