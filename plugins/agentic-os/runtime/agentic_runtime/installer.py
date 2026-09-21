"""Deterministic, journal-aware file installation primitives.

The installer owns mechanical file application only. Interviews, rendering
decisions, and stack-specific generation remain in skills; they pass the
resulting relative-path/content manifest to these operations.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping


JOURNAL_RELATIVE = Path(".agentic/agentic-os/install.json")


def _target(target: str | os.PathLike[str]) -> Path:
    path = Path(target).expanduser().resolve()
    if not path.is_dir():
        raise ValueError("installation target must be an existing directory")
    return path


def _relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("installation paths must be non-empty POSIX-relative strings")
    path = Path(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError("installation path escapes the target")
    if value == JOURNAL_RELATIVE.as_posix():
        raise ValueError("the install journal is owned by the installer")
    return path.as_posix()


def _manifest(files: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(files, Mapping) or not files:
        raise ValueError("installation files must be a non-empty object")
    result: dict[str, dict[str, Any]] = {}
    for raw_path, raw_spec in files.items():
        path = _relative_path(raw_path)
        if isinstance(raw_spec, str):
            spec = {"content": raw_spec}
        elif isinstance(raw_spec, Mapping):
            spec = dict(raw_spec)
        else:
            raise ValueError("installation file spec must be a string or object")
        content = spec.get("content")
        if not isinstance(content, str):
            raise ValueError("installation file content must be text")
        owner = spec.get("owner", "managed")
        if owner not in {"managed", "user", "generated"}:
            raise ValueError("unknown installation owner")
        result[path] = {
            "content": content,
            "owner": owner,
            "template": spec.get("template", "derived"),
            "origin": spec.get("origin", "plugin"),
        }
    return dict(sorted(result.items()))


def _sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _journal(target: Path) -> tuple[dict[str, Any], Path]:
    path = target / JOURNAL_RELATIVE
    if not path.exists():
        return {}, path
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError("install journal is unreadable") from exc
    if not isinstance(value, dict):
        raise RuntimeError("install journal must be an object")
    if value.get("files") is not None and not isinstance(value["files"], dict):
        raise RuntimeError("install journal files must be an object")
    return value, path


def plan_install(target: str | os.PathLike[str], files: Mapping[str, Any]) -> dict[str, Any]:
    """Return deterministic create/replace/preserve actions without writing."""
    root = _target(target)
    manifest = _manifest(files)
    journal, journal_path = _journal(root)
    journal_files = journal.get("files", {})
    actions = []
    for relative, spec in manifest.items():
        destination = root / relative
        desired = hashlib.sha256(spec["content"].encode("utf-8")).hexdigest()
        current = _sha(destination)
        previous = journal_files.get(relative, {})
        managed_unchanged = (current is not None and isinstance(previous, Mapping) and
                             previous.get("sha256") == current and
                             previous.get("owner", "managed") == "managed")
        if current is None:
            action = "create"
        elif current == desired:
            action = "unchanged"
        elif managed_unchanged:
            action = "replace"
        else:
            action = "preserve_modified"
        actions.append({"path": relative, "action": action,
                        "current_sha256": current, "desired_sha256": desired,
                        "owner": spec["owner"]})
    return {"schema": 1, "target": str(root), "journal": str(journal_path),
            "actions": actions}


def apply_install(target: str | os.PathLike[str], files: Mapping[str, Any], *,
                  agentic_os_version: str | None = None) -> dict[str, Any]:
    """Apply safe actions atomically and update the install journal.

    The plan is recomputed immediately before writes, so a caller cannot apply
    a stale decision after a user changes a file.
    """
    root = _target(target)
    manifest = _manifest(files)
    plan = plan_install(root, manifest)
    journal, journal_path = _journal(root)
    journal_files = dict(journal.get("files", {}))
    applied = []
    preserved = []
    for action in plan["actions"]:
        relative = action["path"]
        spec = manifest[relative]
        destination = root / relative
        if action["action"] in {"create", "replace"}:
            destination.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    stream.write(spec["content"])
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, destination)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            applied.append(relative)
        elif action["action"] == "preserve_modified":
            preserved.append(relative)
        if action["action"] != "preserve_modified":
            journal_files[relative] = {
                "sha256": action["desired_sha256"], "template": spec["template"],
                "owner": spec["owner"], "origin": spec["origin"],
            }
        elif relative not in journal_files:
            journal_files[relative] = {
                "sha256": action["current_sha256"], "template": "adopted",
                "owner": "user", "origin": "adopted-existing",
            }
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    updated = dict(journal)
    if agentic_os_version is not None:
        if not isinstance(agentic_os_version, str) or not agentic_os_version:
            raise ValueError("agentic_os_version must be a non-empty string")
        updated["agentic_os_version"] = agentic_os_version
    updated["phase"] = updated.get("phase", "scaffold")
    updated["files"] = dict(sorted(journal_files.items()))
    fd, temporary = tempfile.mkstemp(prefix=".install.", dir=journal_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(updated, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, journal_path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"schema": 1, "target": str(root), "journal": str(journal_path),
            "applied": applied, "preserved": preserved,
            "actions": plan["actions"]}


def remove_install(target: str | os.PathLike[str], paths: list[str] | None = None) -> dict[str, Any]:
    """Remove journaled files only when their bytes are still managed-owned."""
    root = _target(target)
    journal, journal_path = _journal(root)
    entries = journal.get("files", {})
    if not isinstance(entries, dict):
        raise RuntimeError("install journal files must be an object")
    if paths is not None and (not isinstance(paths, list) or
                              not all(isinstance(item, str) for item in paths)):
        raise ValueError("install.remove paths must be a list of strings")
    selected = sorted(entries) if paths is None else sorted({_relative_path(item) for item in paths})
    removed, preserved = [], []
    updated_files = dict(entries)
    for relative in selected:
        entry = entries.get(relative)
        if not isinstance(entry, Mapping):
            continue
        destination = root / relative
        current = _sha(destination)
        if current is not None and current == entry.get("sha256") and entry.get("owner", "managed") in {"managed", "generated"}:
            destination.unlink()
            removed.append(relative)
            updated_files.pop(relative, None)
        else:
            preserved.append(relative)
            retained = dict(entry)
            retained["owner"] = "user"
            retained["origin"] = retained.get("origin", "adopted-existing")
            updated_files[relative] = retained
    updated = dict(journal)
    updated["files"] = dict(sorted(updated_files.items()))
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".uninstall.", dir=journal_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(updated, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, journal_path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"schema": 1, "target": str(root), "journal": str(journal_path),
            "removed": removed, "preserved": preserved}
