#!/usr/bin/env python3
"""Pytest driver for runner.py, the deterministic half of the harness.

Two layers:

  1. Unit tests — exercise runner primitives against throwaway skills
     built in temp directories.
  2. Repository tests — parametrized over the real skills discovered at
     import time under SKILLS_ROOT; every skill must ship a schema-valid
     spec and satisfy its own contract.

Nothing here is specific to any one skill: when a skill's guarantees
change, edit that skill's eval/evals.json — never this file.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runner  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

PASSING_SPEC = {
    "skill_name": "fixture",
    "contracts": {"skill_md_includes": ["# Overview"]},
}


def make_skill(root, name, description="Checks a fixture behaves.", body=None,
               spec=None, fm_name=None):
    """Create a throwaway skill directory and return its path."""
    skill = Path(root) / name
    skill.mkdir(parents=True)
    body = body if body is not None else "# Overview\n\nFixture body.\n"
    text = f"---\nname: {fm_name or name}\ndescription: {description}\n---\n\n{body}"
    (skill / "SKILL.md").write_text(text, encoding="utf-8")
    if spec is not None:
        (skill / "eval").mkdir()
        (skill / "eval" / "evals.json").write_text(json.dumps(spec), encoding="utf-8")
    return skill


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def test_discovery_finds_nested_skill_without_recursing_inside(tmp_path):
    outer = tmp_path / "group" / "sub" / "alpha"
    outer.mkdir(parents=True)
    (outer / "SKILL.md").write_text("x")
    inner = outer / "payload"
    inner.mkdir()
    (inner / "SKILL.md").write_text("x")  # belongs to alpha, not a new skill
    assert runner.discover_skills(tmp_path) == [outer]


def test_discovery_skips_node_modules_and_dot_dirs(tmp_path):
    for noisy in ("node_modules", ".hidden"):
        buried = tmp_path / noisy / "thing"
        buried.mkdir(parents=True)
        (buried / "SKILL.md").write_text("x")
    real = tmp_path / "real"
    real.mkdir()
    (real / "SKILL.md").write_text("x")
    assert runner.discover_skills(tmp_path) == [real]


def test_discovery_results_are_sorted(tmp_path):
    for name in ("zeta", "alpha", "mid"):
        skill = tmp_path / name
        skill.mkdir()
        (skill / "SKILL.md").write_text("x")
    names = [path.name for path in runner.discover_skills(tmp_path)]
    assert names == sorted(names)


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

def test_frontmatter_plain_scalars():
    text = "---\nname: alpha\ndescription: does one thing\n---\nbody\n"
    assert runner.parse_frontmatter(text) == {
        "name": "alpha",
        "description": "does one thing",
    }


def test_frontmatter_quoted_scalars():
    text = "---\nname: \"alpha\"\ndescription: 'does one thing'\n---\n"
    parsed = runner.parse_frontmatter(text)
    assert parsed["name"] == "alpha"
    assert parsed["description"] == "does one thing"


def test_frontmatter_absent():
    assert runner.parse_frontmatter("# heading only\n") == {}


# ---------------------------------------------------------------------------
# Description extraction
# ---------------------------------------------------------------------------

def test_description_plain():
    text = "---\nname: a\ndescription: plain value\n---\n"
    assert runner.extract_description(text) == "plain value"


def test_description_quoted():
    text = '---\nname: a\ndescription: "quoted value"\n---\n'
    assert runner.extract_description(text) == "quoted value"


@pytest.mark.parametrize("marker", ["|", ">", "|-", ">-"])
def test_description_block_scalar_collapses_whitespace(marker):
    text = (
        f"---\nname: a\ndescription: {marker}\n"
        "  first part\n"
        "  second part\n"
        "name2: unrelated\n"
        "---\n"
    )
    assert runner.extract_description(text) == "first part second part"


def test_description_absent_returns_none():
    assert runner.extract_description("---\nname: a\n---\n") is None
    assert runner.extract_description("no frontmatter\n") is None


# ---------------------------------------------------------------------------
# Line counting
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text,expected",
    [("", 0), ("a", 1), ("a\n", 1), ("a\nb", 2), ("a\nb\n", 2), ("a\n\n", 2)],
)
def test_count_lines_ignores_single_trailing_newline(text, expected):
    assert runner.count_lines(text) == expected


# ---------------------------------------------------------------------------
# Spec schema validation
# ---------------------------------------------------------------------------

def test_schema_accepts_minimal_valid_spec():
    result = runner.validate_spec_data(
        {"skill_name": "x", "contracts": {"required_paths": ["SKILL.md"]}}
    )
    assert result == {"valid": True, "errors": []}


def test_schema_accepts_scripts_only_contract():
    result = runner.validate_spec_data(
        {"skill_name": "x", "contracts": {"scripts": {"a.py": {"compile": False}}}}
    )
    assert result["valid"], result["errors"]


@pytest.mark.parametrize(
    "spec",
    [
        {"contracts": {"required_paths": ["SKILL.md"]}},          # missing skill_name
        {"skill_name": "", "contracts": {"required_paths": ["x"]}},
        {"skill_name": "x"},                                       # missing contracts
        {"skill_name": "x", "contracts": {}},                      # nothing declared
        {"skill_name": "x", "contracts": {"required_paths": []}},  # empty check only
        {"skill_name": "x", "contracts": {"requird_paths": ["x"]}},  # typo key
        {"skill_name": "x", "contracts": {"skill_md_includes": ["ok", 3]}},
        {"skill_name": "x", "contracts": {"required_paths": "SKILL.md"}},
        {"skill_name": "x", "contracts": {"scripts": []}},
        {"skill_name": "x", "contracts": {"scripts": {"a.py": {"weird": True}}}},
        {"skill_name": "x", "contracts": {"scripts": {"a.py": {"compile": "yes"}}}},
        {"skill_name": "x", "contracts": {"scripts": {"a.py": {"smoke": {}}}}},
        {
            "skill_name": "x",
            "contracts": {"scripts": {"a.py": {"smoke": {"argv": [], "exit": ["zero"]}}}},
        },
    ],
)
def test_schema_rejects_bad_specs(spec):
    result = runner.validate_spec_data(spec)
    assert not result["valid"]
    assert result["errors"]


def test_schema_rejects_invalid_json_file(tmp_path):
    spec_path = tmp_path / "evals.json"
    spec_path.write_text("{ this is not json")
    data, result = runner.load_spec(spec_path)
    assert data is None
    assert not result["valid"]
    assert any("JSON" in message for message in result["errors"])


def test_load_spec_returns_data_when_valid(tmp_path):
    spec_path = tmp_path / "evals.json"
    spec_path.write_text(json.dumps(PASSING_SPEC))
    data, result = runner.load_spec(spec_path)
    assert result["valid"]
    assert data["skill_name"] == "fixture"


# ---------------------------------------------------------------------------
# Contract enforcement (validate_skill)
# ---------------------------------------------------------------------------

def test_validate_skill_pass_case(tmp_path):
    skill = make_skill(tmp_path, "clean", spec=PASSING_SPEC)
    assert runner.validate_skill(skill) == []


def test_validate_skill_name_mismatch(tmp_path):
    skill = make_skill(tmp_path, "clean", spec=PASSING_SPEC, fm_name="other")
    errors = runner.validate_skill(skill)
    assert any("does not equal directory name" in message for message in errors)


def test_validate_skill_missing_required_path(tmp_path):
    spec = {"skill_name": "clean", "contracts": {"required_paths": ["docs/absent.md"]}}
    skill = make_skill(tmp_path, "clean", spec=spec)
    errors = runner.validate_skill(skill)
    assert any("docs/absent.md" in message for message in errors)


def test_validate_skill_missing_substring(tmp_path):
    spec = {"skill_name": "clean", "contracts": {"skill_md_includes": ["zebra-token"]}}
    skill = make_skill(tmp_path, "clean", spec=spec)
    errors = runner.validate_skill(skill)
    assert any("zebra-token" in message for message in errors)


def test_validate_skill_missing_spec(tmp_path):
    skill = make_skill(tmp_path, "clean", spec=None)
    errors = runner.validate_skill(skill)
    assert any("spec missing" in message for message in errors)


def test_validate_skill_over_line_limit(tmp_path):
    body = "\n".join(f"filler {i}" for i in range(runner.MAX_SKILL_LINES + 10))
    skill = make_skill(tmp_path, "clean", body=body, spec=PASSING_SPEC)
    errors = runner.validate_skill(skill)
    assert any("lines" in message and "limit" in message for message in errors)


def test_validate_skill_over_description_limit(tmp_path):
    long_description = "d" * (runner.MAX_DESCRIPTION_CHARS + 50)
    skill = make_skill(tmp_path, "clean", description=long_description, spec=PASSING_SPEC)
    errors = runner.validate_skill(skill)
    assert any("description" in message and "limit" in message for message in errors)


# ---------------------------------------------------------------------------
# Script contracts (needs a working interpreter for smoke runs)
# ---------------------------------------------------------------------------

_INTERPRETER = runner.interpreter_command()
_HAVE_INTERPRETER = bool(
    _INTERPRETER
    and (shutil.which(_INTERPRETER) or Path(_INTERPRETER).exists())
)

HEALTHY_CLI = (
    "import sys\n"
    "def main():\n"
    "    print('probe ok')\n"
    "    return 0\n"
    "if __name__ == '__main__':\n"
    "    sys.exit(main())\n"
)


@pytest.mark.skipif(not _HAVE_INTERPRETER, reason="no python interpreter for smoke runs")
class TestScriptContracts:
    @staticmethod
    def _scripted_skill(tmp_path, source):
        skill = make_skill(tmp_path, "scripted", spec=None)
        (skill / "tool.py").write_text(source)
        return skill

    def test_healthy_cli_passes(self, tmp_path):
        skill = self._scripted_skill(tmp_path, HEALTHY_CLI)
        contract = {
            "includes": ["probe ok"],
            "smoke": {"argv": [], "output_includes": ["probe ok"]},
        }
        assert runner.run_script_contracts(skill, {"tool.py": contract}) == []

    def test_syntax_error_caught(self, tmp_path):
        skill = self._scripted_skill(tmp_path, "def broken(:\n    pass\n")
        errors = runner.run_script_contracts(skill, {"tool.py": {}})
        assert any("compile" in message for message in errors)

    def test_disallowed_exit_code(self, tmp_path):
        skill = self._scripted_skill(tmp_path, "import sys\nsys.exit(3)\n")
        errors = runner.run_script_contracts(
            skill, {"tool.py": {"smoke": {"argv": []}}}
        )
        assert any("exit code 3" in message for message in errors)

    def test_allowed_nonzero_exit(self, tmp_path):
        skill = self._scripted_skill(tmp_path, "import sys\nsys.exit(3)\n")
        errors = runner.run_script_contracts(
            skill, {"tool.py": {"smoke": {"argv": [], "exit": [3]}}}
        )
        assert errors == []

    def test_missing_smoke_output(self, tmp_path):
        skill = self._scripted_skill(tmp_path, HEALTHY_CLI)
        errors = runner.run_script_contracts(
            skill,
            {"tool.py": {"smoke": {"argv": [], "output_includes": ["unicorn-token"]}}},
        )
        assert any("unicorn-token" in message for message in errors)

    def test_missing_source_phrase(self, tmp_path):
        skill = self._scripted_skill(tmp_path, HEALTHY_CLI)
        errors = runner.run_script_contracts(
            skill, {"tool.py": {"includes": ["unicorn-token"]}}
        )
        assert any("unicorn-token" in message for message in errors)

    def test_absent_script(self, tmp_path):
        skill = make_skill(tmp_path, "scripted", spec=None)
        errors = runner.run_script_contracts(skill, {"nowhere.py": {}})
        assert any("script missing" in message for message in errors)


# ---------------------------------------------------------------------------
# Whole-repo run
# ---------------------------------------------------------------------------

def test_run_validation_mixed_results(tmp_path):
    make_skill(tmp_path, "good", spec=PASSING_SPEC)
    make_skill(tmp_path, "bad", spec=None)  # no spec -> fail
    result = runner.run_validation(tmp_path)
    statuses = {row["skill_name"]: row["status"] for row in result["rows"]}
    assert statuses == {"good": "pass", "bad": "fail"}
    assert not result["passed"]
    assert any(message.startswith("bad: ") for message in result["errors"])
    summary = runner.format_summary(result)
    assert "PASS" in summary and "FAIL" in summary


def test_run_validation_all_pass(tmp_path):
    make_skill(tmp_path, "good", spec=PASSING_SPEC)
    result = runner.run_validation(tmp_path)
    assert result["passed"]
    assert result["errors"] == []


# ---------------------------------------------------------------------------
# Repository layer: every real skill under SKILLS_ROOT must hold its contract
# ---------------------------------------------------------------------------

_ROOT = runner.skills_root()
REAL_SKILLS = runner.discover_skills(_ROOT) if _ROOT.is_dir() else []


@pytest.mark.skipif(
    not _ROOT.is_dir(),
    reason="skills root not present (harness asset running outside a host repo)",
)
def test_at_least_one_skill_discovered():
    assert REAL_SKILLS, f"no skills found under {_ROOT}"


@pytest.mark.parametrize("skill_dir", REAL_SKILLS, ids=lambda p: p.name)
def test_every_skill_ships_a_spec(skill_dir):
    assert (skill_dir / runner.SPEC_RELPATH).is_file(), (
        f"{skill_dir.name} has no {runner.SPEC_RELPATH}"
    )


@pytest.mark.parametrize("skill_dir", REAL_SKILLS, ids=lambda p: p.name)
def test_every_spec_is_schema_valid(skill_dir):
    _, result = runner.load_spec(skill_dir / runner.SPEC_RELPATH)
    assert result["valid"], result["errors"]


@pytest.mark.parametrize("skill_dir", REAL_SKILLS, ids=lambda p: p.name)
def test_every_skill_satisfies_its_contract(skill_dir):
    assert runner.validate_skill(skill_dir) == []
