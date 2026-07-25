#!/usr/bin/env python3
"""T3: static role-matrix checks — every preset's template IDs resolve to a real
file via the VARIABLES.md mapping, union-safety, and QA-preset invariants."""
import json
import re
import sys
from pathlib import Path

PLUGIN = Path(sys.argv[1])
TPL = PLUGIN / "templates"
presets = {p.stem: json.loads(p.read_text()) for p in (PLUGIN / "presets/roles").glob("*.json")}

# ID -> file resolver mirroring VARIABLES.md § Template IDs mapping.
HOOK_FILE = {
    "hooks/precommit-review-gate": "hooks/claude/precommit_review_gate.py",
    "hooks/subagent-gate": "hooks/claude/subagent_gate.py.tmpl",
    "hooks/instruction-gate": "hooks/claude/instruction_gate.py.tmpl",
    "hooks/instruction-stale-notice": "hooks/claude/instruction_stale_notice.py",
    "hooks/write-scope-guard": "hooks/claude/write_scope_guard.py.tmpl",
    "hooks/session-bootstrap": "hooks/claude/session_start_bootstrap.py.tmpl",
    "hooks/precompact-checkpoint": "hooks/claude/precompact_checkpoint.py",
    "hooks/session-learnings-notice": "hooks/claude/session_learnings_notice.py",
    "hooks/lint-on-save": "hooks/claude/lint_on_save.py.tmpl",
    "hooks/context-monitor": "hooks/claude/context_monitor.py",
    "hooks/prompt-scan-guard": "hooks/claude/prompt_scan_guard.py",
    "hooks/human-gated-commands": "hooks/claude/human_gated_commands.py.tmpl",
    "hooks/guarded-write-paths": "hooks/claude/guarded_write_paths.py.tmpl",
    "hooks/migration-notice": "hooks/claude/migration_notice.py.tmpl",
    "hooks/settings-fragment": "hooks/settings-fragment.json.tmpl",
    "githooks/pre-commit": "githooks/pre-commit",
    "scripts/install-git-hooks": "scripts/install-git-hooks.sh",
    "governance/claude-section": "governance/CLAUDE.section.md.tmpl",
    "governance/agents": "governance/AGENTS.md.tmpl",
    "governance/patterns": "governance/PATTERNS.md.tmpl",
    "governance/agent-registry": "governance/agent-registry.md.tmpl",
    "commands/pipeline-orchestrator": "commands/core/pipeline-orchestrator.md.tmpl",
    "commands/dispatch": "commands/core/dispatch.md.tmpl",
    "sdlc/config": "sdlc/config.json.tmpl",
    "sdlc/project": "sdlc/project.md.tmpl",
}
CORE_AGENTS = {"dispatcher", "blind-code-reviewer", "security-reviewer",
               "instruction-auditor", "pr-pipeline-gate"}


def resolve(tid: str) -> Path | None:
    if tid in HOOK_FILE:
        return TPL / HOOK_FILE[tid]
    if tid.startswith("policy/"):
        return TPL / ("policy/%s.md.tmpl" % tid.split("/", 1)[1])
    if tid.startswith("guides/"):
        # A guide ships verbatim (`.md`) or as a template (`.md.tmpl`, e.g.
        # quality-gates renders GATE_ENTRIES). Accept whichever exists.
        base = TPL / ("guides/standards/%s.md" % tid.split("/", 1)[1])
        return base if base.exists() else base.with_suffix(".md.tmpl")
    if tid.startswith("agents/"):
        name = tid.split("/", 1)[1]
        sub = "core" if name in CORE_AGENTS else "qa"
        return TPL / ("agents/%s/%s.md.tmpl" % (sub, name))
    return None


fail = 0
# (1) every referenced template ID resolves to an existing file
for name, p in presets.items():
    for tid in p["templates"]:
        f = resolve(tid)
        if f is None or not f.exists():
            print("  MISSING file for %s -> %s (%s)" % (name, tid, f)); fail = 1

# (1b) no ORPHANED registered ID: every ID registered in VARIABLES.md must be
#      claimed by at least one preset's `templates` or `generated`. Check (1)
#      only proves ID -> file; without the reverse, a template can be registered
#      in VARIABLES.md and mapped in the SKILL.md Phase 4 table yet listed in no
#      preset, so Phase 4 -- which scaffolds the preset union -- never installs
#      it. `hooks/migration-notice` sat orphaned exactly this way: the settings
#      fragment registered its PostToolUse entry, the pruning rule then dropped
#      it on every install, and no migration-managed repo ever got a migration
#      notice. Read the registry from VARIABLES.md (the same source and regex
#      validate-presets.sh uses) rather than the HOOK_FILE mirror above: that
#      mirror holds only the ~21 non-prefix IDs, so an orphan under `policy/`,
#      `guides/`, `agents/`, or `gen/` would slip through unnoticed.
REGISTERED = set(re.findall(
    r"`((?:hooks|githooks|scripts|governance|policy|guides|agents|commands|sdlc|gen)"
    r"/[a-z0-9][a-z0-9-]*)`",
    (TPL / "VARIABLES.md").read_text(encoding="utf-8"),
))
claimed = {tid for p in presets.values() for tid in p["templates"] + p["generated"]}
for tid in sorted(REGISTERED - claimed):
    print("  ORPHANED registered ID (in VARIABLES.md, in no preset): %s" % tid); fail = 1

# (2) union-safety: shared IDs are identical strings (trivially true for strings,
#     but ensure no preset lists a malformed/dup ID)
for name, p in presets.items():
    if len(p["templates"]) != len(set(p["templates"])):
        print("  DUP template ID in", name); fail = 1

# (3) every sdlc_skills entry resolves to a shipped agentic-sdlc skill dir.
#     Nothing else validates these names — a typo'd skill would ship silently
#     and the installer would journal a skill /agentic-init can never surface.
SDLC_SKILLS = PLUGIN.parent / "agentic-sdlc" / "skills"
for name, p in presets.items():
    for skill in p.get("sdlc_skills", []):
        if not (SDLC_SKILLS / skill / "SKILL.md").is_file():
            print("  MISSING sdlc skill for %s -> %s" % (name, skill)); fail = 1

# (4) QA preset invariants
qa = presets["qa"]
if qa["default_hitl"] != "strict":
    print("  qa default_hitl != strict"); fail = 1
if qa["default_orchestration"] != "dispatcher":
    print("  qa default_orchestration != dispatcher"); fail = 1
for need in ("agents/test-failure-triage", "agents/work-item-creator"):
    if need not in qa["templates"]:
        print("  qa missing", need); fail = 1

sys.exit(fail)
