#!/usr/bin/env python3
"""Deterministic structural-contract checker for agent skills.

This is the code-based half of the two-part eval harness. It walks the
skills tree, treats every directory that contains a SKILL.md as a skill
root, and enforces:

  * universal limits (frontmatter shape, size caps), and
  * the per-skill contract declared in <skill>/eval/evals.json
    ("contracts" block of the spec).

The LLM-judge half (llm_eval_runner.py) reads the "evals" array of the
same spec file. Nothing here calls a model; this module is stdlib-only.

Expected placement: <repoRoot>/eval/runner.py — the repo root is derived
as the grandparent of this file. Skills are discovered under
<repoRoot>/.claude by default; set SKILLS_ROOT (interpreted relative to
the repo root) to point elsewhere.

CLI: `python -m eval.runner` (or run this file directly).
Exit codes: 0 when every skill passes, 1 on any violation.
"""

from __future__ import annotations

import json
import os
import py_compile
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Universal limits applied to every skill, contract or not.
MAX_SKILL_LINES = 500
MAX_DESCRIPTION_CHARS = 1000

# Spec file location, relative to each skill directory.
SPEC_RELPATH = Path("eval") / "evals.json"

# Recognized spec keys. Anything else is rejected — typo protection.
CONTRACT_KEYS = {"required_paths", "skill_md_includes", "skill_md_matches", "scripts"}
SCRIPT_KEYS = {"compile", "smoke", "includes", "matches"}
SMOKE_KEYS = {"argv", "exit", "output_includes"}

SMOKE_TIMEOUT_SECONDS = 60
SKIP_DIR_NAMES = {"node_modules"}


# ---------------------------------------------------------------------------
# Location and discovery
# ---------------------------------------------------------------------------

def skills_root() -> Path:
    """Directory under which skills are discovered.

    Defaults to <repoRoot>/.claude; the SKILLS_ROOT env var (relative to
    the repo root) overrides it.
    """
    override = os.environ.get("SKILLS_ROOT")
    if override:
        return (REPO_ROOT / override).resolve()
    return REPO_ROOT / ".claude"


def discover_skills(root: Path) -> list[Path]:
    """Depth-first walk: every dir holding a SKILL.md is a skill root.

    Does not recurse inside a skill (nested SKILL.md files belong to the
    outer skill's payload). Skips dot-directories and node_modules.
    Returns sorted paths for stable ordering.
    """
    found: list[Path] = []

    def walk(directory: Path) -> None:
        if (directory / "SKILL.md").is_file():
            found.append(directory)
            return
        try:
            children = sorted(directory.iterdir())
        except OSError:
            return
        for child in children:
            if not child.is_dir():
                continue
            if child.name.startswith(".") or child.name in SKIP_DIR_NAMES:
                continue
            walk(child)

    if root.is_dir():
        walk(root)
    return sorted(found)


# ---------------------------------------------------------------------------
# SKILL.md parsing (deliberately minimal — not a YAML parser)
# ---------------------------------------------------------------------------

def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict:
    """Read only the `name` and `description` simple scalars from the
    leading `---` fenced block. Surrounding quotes are stripped."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"^(name|description):\s*(.*)$", line)
        if match:
            fields[match.group(1)] = _unquote(match.group(2).strip())
    return fields


def extract_description(text: str):
    """Frontmatter description, including block-scalar (| or >) forms.

    Multi-line values are collapsed into one whitespace-normalized
    string. Returns None when the field is absent or empty.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    block: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        block.append(line)
    for index, line in enumerate(block):
        match = re.match(r"^description:\s*(.*)$", line)
        if not match:
            continue
        inline = match.group(1).strip()
        if inline and inline[0] in ("|", ">"):
            # Block scalar: gather the indented continuation lines.
            collected: list[str] = []
            for continuation in block[index + 1:]:
                if not continuation.strip():
                    continue
                if re.match(r"^\S", continuation):
                    break  # next top-level frontmatter key
                collected.append(continuation.strip())
            merged = re.sub(r"\s+", " ", " ".join(collected)).strip()
            return merged or None
        if inline:
            return re.sub(r"\s+", " ", _unquote(inline)).strip() or None
        return None
    return None


def count_lines(text: str) -> int:
    """Line count that forgives exactly one trailing newline."""
    if text.endswith("\n"):
        text = text[:-1]
    if not text:
        return 0
    return text.count("\n") + 1


# ---------------------------------------------------------------------------
# Spec schema validation
# ---------------------------------------------------------------------------

def _is_string_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _is_number_list(value) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, (int, float)) and not isinstance(item, bool) for item in value
    )


def _check_scripts_shape(scripts) -> tuple:
    """Validate the `scripts` contract block. Returns (errors, checks)
    where checks counts declared script entries."""
    errors: list[str] = []
    if not isinstance(scripts, dict):
        return ["scripts must be an object keyed by relative script path"], 0
    checks = 0
    for rel_path, entry in scripts.items():
        label = f"scripts[{rel_path!r}]"
        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue
        for key in sorted(set(entry) - SCRIPT_KEYS):
            errors.append(f"{label} has unknown key {key!r}")
        if "compile" in entry and not isinstance(entry["compile"], bool):
            errors.append(f"{label}.compile must be a boolean")
        for key in ("includes", "matches"):
            if key in entry and not _is_string_list(entry[key]):
                errors.append(f"{label}.{key} must be an array of strings")
        smoke = entry.get("smoke")
        if smoke is not None:
            if not isinstance(smoke, dict):
                errors.append(f"{label}.smoke must be an object")
            else:
                for key in sorted(set(smoke) - SMOKE_KEYS):
                    errors.append(f"{label}.smoke has unknown key {key!r}")
                if not _is_string_list(smoke.get("argv")):
                    errors.append(f"{label}.smoke.argv must be an array of strings")
                if "exit" in smoke and not _is_number_list(smoke["exit"]):
                    errors.append(f"{label}.smoke.exit must be an array of numbers")
                if "output_includes" in smoke and not _is_string_list(smoke["output_includes"]):
                    errors.append(f"{label}.smoke.output_includes must be an array of strings")
        checks += 1
    return errors, checks


def validate_spec_data(data) -> dict:
    """Schema-check one parsed spec. Returns {"valid": bool, "errors": [...]}."""
    if not isinstance(data, dict):
        return {"valid": False, "errors": ["spec root must be a JSON object"]}
    errors: list[str] = []
    name = data.get("skill_name")
    if not isinstance(name, str) or not name.strip():
        errors.append("skill_name must be a non-empty string")
    contracts = data.get("contracts")
    if not isinstance(contracts, dict):
        errors.append("contracts must be an object")
        contracts = {}
    for key in sorted(set(contracts) - CONTRACT_KEYS):
        errors.append(f"unknown contract key {key!r}")
    declared = 0
    for key in ("required_paths", "skill_md_includes", "skill_md_matches"):
        if key not in contracts:
            continue
        if not _is_string_list(contracts[key]):
            errors.append(f"{key} must be an array of strings")
        elif contracts[key]:
            declared += 1
    if "scripts" in contracts:
        script_errors, script_checks = _check_scripts_shape(contracts["scripts"])
        errors.extend(script_errors)
        declared += script_checks
    if not errors and declared == 0:
        errors.append("contracts must declare at least one non-empty check")
    return {"valid": not errors, "errors": errors}


def load_spec(spec_path: Path) -> tuple:
    """Read + schema-check a spec file. Returns (data, result) where
    result is the {"valid", "errors"} dict; data is None unless valid."""
    try:
        raw = spec_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, {"valid": False, "errors": [f"cannot read spec: {exc}"]}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, {"valid": False, "errors": [f"spec is not valid JSON: {exc}"]}
    result = validate_spec_data(data)
    return (data if result["valid"] else None), result


# ---------------------------------------------------------------------------
# Script contracts
# ---------------------------------------------------------------------------

def interpreter_command() -> str:
    """Python used for compile/smoke checks: $PYTHON, else the running
    interpreter, else a bare `python3`."""
    return os.environ.get("PYTHON") or sys.executable or "python3"


def _smoke_check(script_path: Path, rel_path: str, smoke: dict) -> list[str]:
    errors: list[str] = []
    argv = [interpreter_command(), str(script_path)] + list(smoke.get("argv", []))
    try:
        proc = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,  # no-arg CLIs hit EOF deterministically
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=SMOKE_TIMEOUT_SECONDS,
            text=True,
        )
    except subprocess.TimeoutExpired:
        return [f"{rel_path}: smoke run exceeded {SMOKE_TIMEOUT_SECONDS}s"]
    except OSError as exc:
        return [f"{rel_path}: smoke run could not start: {exc}"]
    allowed = [int(code) for code in (smoke.get("exit") or [0])]
    if proc.returncode not in allowed:
        errors.append(f"{rel_path}: smoke exit code {proc.returncode} not in {allowed}")
    combined = (proc.stdout or "") + (proc.stderr or "")
    for needle in smoke.get("output_includes", []):
        if needle not in combined:
            errors.append(f"{rel_path}: smoke output missing {needle!r}")
    return errors


def run_script_contracts(skill_dir: Path, scripts: dict) -> list[str]:
    """Enforce every per-script contract; returns error strings."""
    errors: list[str] = []
    for rel_path in sorted(scripts):
        entry = scripts[rel_path]
        script_path = skill_dir / rel_path
        if not script_path.is_file():
            errors.append(f"script missing: {rel_path}")
            continue
        if entry.get("compile", True):
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    py_compile.compile(
                        str(script_path),
                        cfile=os.path.join(tmp, "probe.pyc"),
                        doraise=True,
                    )
            except py_compile.PyCompileError as exc:
                errors.append(f"{rel_path}: does not byte-compile: {exc.msg}")
        source = script_path.read_text(encoding="utf-8", errors="replace")
        for needle in entry.get("includes", []):
            if needle not in source:
                errors.append(f"{rel_path}: source missing literal {needle!r}")
        for pattern in entry.get("matches", []):
            try:
                if not re.search(pattern, source, re.IGNORECASE):
                    errors.append(f"{rel_path}: source does not match /{pattern}/i")
            except re.error as exc:
                errors.append(f"{rel_path}: invalid regex {pattern!r}: {exc}")
        smoke = entry.get("smoke")
        if smoke:
            errors.extend(_smoke_check(script_path, rel_path, smoke))
    return errors


# ---------------------------------------------------------------------------
# Per-skill and whole-repo validation
# ---------------------------------------------------------------------------

def validate_skill(skill_dir: Path) -> list[str]:
    """Universal checks + the skill's declared contract. Returns errors."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return ["SKILL.md is missing"]
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []

    frontmatter = parse_frontmatter(text)
    name = frontmatter.get("name")
    if not name:
        errors.append("frontmatter name is missing")
    elif name != skill_dir.name:
        errors.append(
            f"frontmatter name {name!r} does not equal directory name {skill_dir.name!r}"
        )
    description = extract_description(text)
    if description is None:
        errors.append("frontmatter description is missing")
    elif len(description) > MAX_DESCRIPTION_CHARS:
        errors.append(
            f"description is {len(description)} chars (limit {MAX_DESCRIPTION_CHARS})"
        )
    lines = count_lines(text)
    if lines > MAX_SKILL_LINES:
        errors.append(f"SKILL.md is {lines} lines (limit {MAX_SKILL_LINES})")

    spec_path = skill_dir / SPEC_RELPATH
    if not spec_path.is_file():
        errors.append(f"spec missing: {SPEC_RELPATH}")
        return errors
    data, result = load_spec(spec_path)
    if not result["valid"]:
        errors.extend(f"spec: {message}" for message in result["errors"])
        return errors

    contracts = data["contracts"]
    for rel in contracts.get("required_paths", []):
        if not (skill_dir / rel).exists():
            errors.append(f"required path missing: {rel}")
    for needle in contracts.get("skill_md_includes", []):
        if needle not in text:
            errors.append(f"SKILL.md missing substring {needle!r}")
    for pattern in contracts.get("skill_md_matches", []):
        try:
            if not re.search(pattern, text, re.IGNORECASE):
                errors.append(f"SKILL.md does not match /{pattern}/i")
        except re.error as exc:
            errors.append(f"invalid regex {pattern!r}: {exc}")
    errors.extend(run_script_contracts(skill_dir, contracts.get("scripts") or {}))
    return errors


def run_validation(root=None) -> dict:
    """Validate every discovered skill.

    Returns {"rows": [...], "errors": [...], "passed": bool} where each
    row is {skill_name, dir, status, errors} and the flat error list is
    prefixed with the skill name.
    """
    root = root if root is not None else skills_root()
    rows: list[dict] = []
    flat: list[str] = []
    for skill_dir in discover_skills(root):
        skill_errors = validate_skill(skill_dir)
        rows.append(
            {
                "skill_name": skill_dir.name,
                "dir": str(skill_dir),
                "status": "pass" if not skill_errors else "fail",
                "errors": skill_errors,
            }
        )
        flat.extend(f"{skill_dir.name}: {message}" for message in skill_errors)
    return {"rows": rows, "errors": flat, "passed": not flat}


def format_summary(result: dict) -> str:
    """Plain-text table: PASS/FAIL per skill, error bullets, count line."""
    lines: list[str] = []
    width = max((len(row["skill_name"]) for row in result["rows"]), default=0)
    for row in result["rows"]:
        verdict = "PASS" if row["status"] == "pass" else "FAIL"
        lines.append(f"{verdict}  {row['skill_name']:<{width}}  {row['dir']}")
        for message in row["errors"]:
            lines.append(f"      - {message}")
    total = len(result["rows"])
    passing = sum(1 for row in result["rows"] if row["status"] == "pass")
    lines.append("")
    lines.append(
        f"{passing}/{total} skills pass; {len(result['errors'])} violation(s)"
    )
    return "\n".join(lines)


def main() -> int:
    result = run_validation()
    stream = sys.stdout if result["passed"] else sys.stderr
    print(format_summary(result), file=stream)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
