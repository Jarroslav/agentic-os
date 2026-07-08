#!/usr/bin/env python3
"""Reference executor of agentic-init Phase 4 (deterministic scaffold only).

This is the WS-E test harness's stand-in for a human/agent following
plugins/agentic-os/skills/agentic-init/SKILL.md by hand: it renders + places
every template in the *developer* preset union with the `--defaults` answers for
the nextjs-supabase profile, deep-merges the settings fragment, installs the
git-hook chain, and seeds the instruction scorecard. It deliberately SKIPS
Phase 5 (generation) and Phase 3 side effects outside the target.

If a step here is impossible to derive from the SKILL.md spec, that is a WS-E
finding — this file is the executable proof that the spec is followable.

Usage: refinstall.py <PLUGIN_ROOT> <TARGET_REPO> [--reinstall]
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

PLUGIN = Path(sys.argv[1]).resolve()
TARGET = Path(sys.argv[2]).resolve()
REINSTALL = "--reinstall" in sys.argv[3:]
TPL = PLUGIN / "templates"

VERSION = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())["version"]

# The developer preset's template union. Which IDs are *installed* is read from
# the preset rather than restated here: a hardcoded copy silently diverges the
# moment a preset gains or loses an ID, which is exactly how
# `hooks/migration-notice` stayed orphaned (registered in VARIABLES.md and the
# SKILL.md Phase 4 map, listed in no preset) while this executor installed it
# anyway and the matrix stayed green. The (src, dest, id) rows below still
# restate the id -> filename mapping; only membership is preset-driven.
PRESET_TEMPLATE_IDS = set(
    json.loads((PLUGIN / "presets/roles/developer.json").read_text())["templates"]
)

# SKILL.md Phase 4 step 1, first installer-side conditional: these two are
# scaffolded whenever `hooks/settings-fragment` is in the union EVEN IF no preset
# lists them. The fragment unconditionally wires them as PreToolUse hooks, and a
# wired-but-missing PreToolUse script exits 2 and blocks every tool call. With
# empty lists they are safe no-ops. The union filter must not skip them.
ALWAYS_WITH_SETTINGS = {"hooks/human-gated-commands", "hooks/guarded-write-paths"}

# --- --defaults answers for the nextjs-supabase profile, developer preset ------
NEWLINE_VARS = {"GATE_COMMANDS", "HUMAN_GATED_COMMANDS", "GUARDED_WRITE_PATHS",
                "ENV_CHECK_COMMANDS", "SECRET_DENY_PATTERNS"}
LISTS = {
    "GATE_COMMANDS": ["npx tsc --noEmit", "npm run lint -- --max-warnings 0", "npm test"],
    "HUMAN_GATED_COMMANDS": ["git push origin main", "supabase db push --linked"],
    "GUARDED_WRITE_PATHS": [],
    "ENV_CHECK_COMMANDS": ["node --version"],
    "SECRET_DENY_PATTERNS": [],  # extras beyond the baked-in three
    "ESCALATE_ON": ["security", "breaking-change", "migration", "spend"],
}
SCALARS = {
    "AGENTIC_OS_VERSION": VERSION,
    "AGENTS_CANONICAL_DIR": ".agentic/agents/",
    "APP_START_COMMAND": "npm run dev",
    "BASE_URL": "http://localhost:3000",
    "DEFAULT_BRANCH": "main",
    "HITL_MODE": "gated-autonomous",
    "MAX_FILES": "10",
    "MAX_LOC": "250",
    "MIGRATIONS_DIR": "supabase/migrations/",
    "MIGRATION_DIFF_COMMAND": "npx supabase db diff",
    "MR_ADAPTER": "gh",
    "OUTPUT_CONTRACT_SECTIONS": "Summary,Why,Blocking,Non-blocking,Escalate to human",
    "PROJECT_NAME": TARGET.name,
    "ROLE_PRESETS_ACTIVE": "developer",
    "SCORECARD_PATH": "docs/audits/instruction-scorecard.json",
    "SCORE_THRESHOLD": "95",
    "STACK_SUMMARY": "Next.js + Supabase web app.",
    "STAGING_ENV_NAME": "staging",
    "TEST_FRAMEWORK": "playwright",
    "TICKET_ADAPTER": "GitHub",
    "TICKET_PREFIX": "GH",
}


def render(text: str, is_json: bool) -> str:
    for var in NEWLINE_VARS:
        text = text.replace("{{%s}}" % var, "\n".join(LISTS[var]))
    esc = LISTS["ESCALATE_ON"]
    text = text.replace("{{ESCALATE_ON}}",
                        ",".join('"%s"' % x for x in esc) if is_json else ",".join(esc))
    for k, v in SCALARS.items():
        text = text.replace("{{%s}}" % k, v)
    return text


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


JOURNAL = {"agentic_os_version": VERSION, "answers": {"preset": "developer", "defaults": True},
           "phase": "scaffold", "files": {}, "follow_ups": []}


# Files whose collision handling is bespoke (append/merge) — never blanket-skipped here.
MANAGED_APPEND = {"CLAUDE.md", ".claude/settings.json"}


def write(dest_rel: str, content: str, template: str, owner: str = "managed"):
    dest = TARGET / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if REINSTALL and dest.exists():
        cur = hashlib.sha256(dest.read_bytes()).hexdigest()
        rec = JOURNAL_PREV.get("files", {}).get(dest_rel)
        if rec and rec["sha256"] != cur:      # user-modified: skip + warn
            print("WARN skip user-modified", dest_rel, file=sys.stderr)
            JOURNAL["files"][dest_rel] = rec
            return
    elif not REINSTALL and dest.exists() and dest_rel not in MANAGED_APPEND:
        # Fresh install, pre-existing non-journaled file: collision default = skip.
        print("COLLISION skip (owner user)", dest_rel, file=sys.stderr)
        JOURNAL["files"][dest_rel] = {"sha256": sha(dest), "template": template, "owner": "user"}
        return
    dest.write_text(content)
    JOURNAL["files"][dest_rel] = {"sha256": sha(dest), "template": template, "owner": owner}


def copy_tpl(src_rel: str, dest_rel: str, template: str):
    src = TPL / src_rel
    is_json = src.name.endswith(".json.tmpl")
    content = render(src.read_text(), is_json) if src.name.endswith(".tmpl") else src.read_text()
    write(dest_rel, content, template)


JOURNAL_PREV = {}
jpath = TARGET / ".agentic/agentic-os/install.json"
if REINSTALL and jpath.exists():
    JOURNAL_PREV = json.loads(jpath.read_text())

# --- Phase 4 step 1: hooks -----------------------------------------------------
HOOKS = [
    ("precommit_review_gate.py", "precommit_review_gate.py", "hooks/precommit-review-gate"),
    ("subagent_gate.py.tmpl", "subagent_gate.py", "hooks/subagent-gate"),
    ("instruction_gate.py.tmpl", "instruction_gate.py", "hooks/instruction-gate"),
    ("instruction_stale_notice.py", "instruction_stale_notice.py", "hooks/instruction-stale-notice"),
    ("write_scope_guard.py.tmpl", "write_scope_guard.py", "hooks/write-scope-guard"),
    ("session_start_bootstrap.py.tmpl", "session_start_bootstrap.py", "hooks/session-bootstrap"),
    ("precompact_checkpoint.py", "precompact_checkpoint.py", "hooks/precompact-checkpoint"),
    ("human_gated_commands.py.tmpl", "human_gated_commands.py", "hooks/human-gated-commands"),
    ("guarded_write_paths.py.tmpl", "guarded_write_paths.py", "hooks/guarded-write-paths"),
    ("migration_notice.py.tmpl", "migration_notice.py", "hooks/migration-notice"),
]
settings_in_union = "hooks/settings-fragment" in PRESET_TEMPLATE_IDS
for src, dest, tid in HOOKS:
    forced = tid in ALWAYS_WITH_SETTINGS and settings_in_union
    if tid not in PRESET_TEMPLATE_IDS and not forced:
        continue  # not in this preset's union — Phase 4 scaffolds the union only
    # SKILL.md Phase 4: migration_notice is skipped when MIGRATIONS_DIR is empty.
    # Non-empty here (nextjs-supabase → supabase/migrations/), so it installs.
    if tid == "hooks/migration-notice" and not SCALARS["MIGRATIONS_DIR"]:
        continue
    copy_tpl("hooks/claude/" + src, ".claude/hooks/" + dest, tid)

# --- Phase 4 step 2: settings deep-merge --------------------------------------
frag = json.loads(render((TPL / "hooks/settings-fragment.json.tmpl").read_text(), True))
settings_path = TARGET / ".claude/settings.json"
settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}


def deep_merge(base, frag):
    for k, v in frag.items():
        if isinstance(v, dict):
            deep_merge(base.setdefault(k, {}), v)
        elif isinstance(v, list):
            arr = base.setdefault(k, [])
            for item in v:
                if item not in arr:
                    arr.append(item)
        else:
            base.setdefault(k, v)


deep_merge(settings, frag)
settings_path.parent.mkdir(parents=True, exist_ok=True)
settings_path.write_text(json.dumps(settings, indent=2) + "\n")
JOURNAL["files"][".claude/settings.json"] = {
    "sha256": sha(settings_path), "template": "hooks/settings-fragment", "owner": "managed"}

# --- Phase 4 step 3: git hooks (chaining installer) ---------------------------
copy_tpl("githooks/pre-commit", ".githooks/pre-commit", "githooks/pre-commit")
copy_tpl("scripts/install-git-hooks.sh", "scripts/install-git-hooks.sh", "scripts/install-git-hooks")

# --- Phase 4 step 4: governance -----------------------------------------------
BEGIN = "<!-- agentic-os:begin v%s -->" % VERSION
END = "<!-- agentic-os:end -->"
claude_block = render((TPL / "governance/CLAUDE.section.md.tmpl").read_text(), False)
claude_path = TARGET / "CLAUDE.md"
if claude_path.exists():
    body = claude_path.read_text()
    body = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), "", body, flags=re.S).rstrip()
    # Idempotent: a block-only file (no surrounding content) re-renders identically.
    claude_path.write_text((body + "\n\n" if body else "") + claude_block + "\n")
else:
    claude_path.write_text(claude_block + "\n")
JOURNAL["files"]["CLAUDE.md"] = {"sha256": sha(claude_path),
                                 "template": "governance/claude-section", "owner": "managed"}

copy_tpl("governance/AGENTS.md.tmpl", "AGENTS.md", "governance/agents")
copy_tpl("governance/PATTERNS.md.tmpl", "PATTERNS.md", "governance/patterns")
copy_tpl("governance/agent-registry.md.tmpl", ".agentic/guides/agent-registry.md",
         "governance/agent-registry")

# --- Phase 4 step 5: policies, guides, sdlc -----------------------------------
for name in ("ai-policy", "escalation-policy", "safety-policy"):
    copy_tpl("policy/%s.md.tmpl" % name, ".agentic/guides/policy/%s.md" % name, "policy/" + name)
GUIDES = ["git-workflow", "code-quality", "quality-gates", "instruction-quality-rubric",
          "working-with-agents", "qa-strategy-stub"]
for g in GUIDES:
    dest = ".agentic/guides/standards/%s.md" % g
    if (TARGET / dest).exists():  # existing-guide rule: skip + owner user
        JOURNAL["files"][dest] = {"sha256": sha(TARGET / dest), "template": "guides/" + g,
                                  "owner": "user"}
    else:
        copy_tpl("guides/standards/%s.md" % g, dest, "guides/" + g)
copy_tpl("sdlc/config.json.tmpl", ".agentic/agentic-sdlc/config.json", "sdlc/config")
copy_tpl("sdlc/project.md.tmpl", ".agentic/guides/project.md", "sdlc/project")

# --- Phase 4 step 7: core agents + pointers -----------------------------------
CORE_AGENTS = [("blind-code-reviewer", False), ("security-reviewer", True),
               ("instruction-auditor", True)]  # (name, readonly)
for name, ro in CORE_AGENTS:
    copy_tpl("agents/core/%s.md.tmpl" % name, ".agentic/agents/%s.md" % name, "agents/" + name)
    tools = "Read, Grep, Glob" if ro else "Read, Grep, Glob, Edit, Write, Bash"
    ptr = ("---\nname: %s\ndescription: Pointer to the canonical %s contract.\n"
           "tools: %s\nmodel: inherit\n---\n\nRead `.agentic/agents/%s.md` — the canonical "
           "contract — and follow it exactly.\n" % (name, name, tools, name))
    write(".claude/agents/%s.md" % name, ptr, "derived")
    cmd = ("---\nname: %s\ndescription: Run the %s agent.\n---\n\n"
           "Read `.agentic/agents/%s.md` and execute its contract on the current context.\n"
           % (name, name, name))
    write(".claude/commands/%s.md" % name, cmd, "derived")

# commands (canonical in .claude/commands)
copy_tpl("commands/core/pipeline-orchestrator.md.tmpl", ".claude/commands/pipeline-orchestrator.md",
         "commands/pipeline-orchestrator")

# --- Phase 4 step 8: seed instruction scorecard -------------------------------
scorecard = {"schema": 1, "threshold": 95, "files": {}}
for rel in list(JOURNAL["files"]):
    p = TARGET / rel
    if rel.endswith(".md") and (
        rel.startswith(".agentic/agents/") or rel.startswith(".claude/agents/")
        or rel in ("CLAUDE.md", "AGENTS.md", "PATTERNS.md")
        or rel == ".agentic/guides/agent-registry.md"
        or rel.startswith(".agentic/guides/")):
        scorecard["files"][rel] = {"content_sha256": sha(p), "composite_score": 100,
                                   "source": "template-inherited"}
sc_path = TARGET / "docs/audits/instruction-scorecard.json"
sc_path.parent.mkdir(parents=True, exist_ok=True)
sc_path.write_text(json.dumps(scorecard, indent=2) + "\n")

# --- flaky ledger only for qa preset (not developer) --------------------------

jpath.parent.mkdir(parents=True, exist_ok=True)
JOURNAL["phase"] = "scaffold"
jpath.write_text(json.dumps(JOURNAL, indent=2) + "\n")
print("refinstall: wrote %d files to %s" % (len(JOURNAL["files"]), TARGET))
