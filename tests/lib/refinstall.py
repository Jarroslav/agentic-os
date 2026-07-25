#!/usr/bin/env python3
"""Reference executor of agentic-init Phase 4 (deterministic scaffold only).

This is the acceptance harness's stand-in for a human/agent following
plugins/agentic-os/skills/agentic-init/SKILL.md by hand: it renders + places
every template in the *developer* preset union with the `--defaults` answers for
the nextjs-supabase profile, deep-merges the settings fragment, installs the
git-hook chain, and seeds the instruction scorecard. It deliberately SKIPS
Phase 5 (generation) and Phase 3 side effects outside the target.

If a step here is impossible to derive from the SKILL.md spec, that is a harness
finding — this file is the executable proof that the spec is followable.

Usage: refinstall.py <PLUGIN_ROOT> <TARGET_REPO> [--reinstall]
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

# The escaping rule and the adversarial answers live in one place so a mutation to
# either fails every check that depends on it, not just the copy that was edited.
from render_rule import ANSWERS as ADVERSARIAL_ANSWERS
from render_rule import LIST_ANSWERS as ADVERSARIAL_LISTS
from render_rule import esc

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
    "LINT_FIX_COMMAND": "npx eslint --fix",
    "LINT_CHECK_COMMAND": "npx eslint",
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

# None of the scalar answers above contains a quote, backslash, or newline, so for
# them `render()` emits the same bytes escaped or not. The newline-list answers are
# different: `"\n".join(...)` *introduces* a newline before `esc` sees it, so those
# constants do change — `X = """a\nb"""` on one source line, where they used to span
# two. Same value, same `.splitlines()`; less readable scaffold, uniform rule, and
# no dependence on "this only ever lands inside triple quotes", which is the
# reasoning that produced the bug. `/agentic-doctor` Check 3 reads these constants
# by importing the hook rather than scraping its text, for exactly this reason.
#
# What that leaves untestable is the *scalar* path: drop `esc` and every check above
# still passes. `REFINSTALL_ADVERSARIAL=1` swaps in the quote-bearing answers a real
# interview would produce, so T8b's round-trip fails when the rule is dropped, made
# lossy, or applied twice. Off by default: T1's golden manifest pins the defaults.
if os.environ.get("REFINSTALL_ADVERSARIAL"):
    unknown = set(ADVERSARIAL_ANSWERS) - set(SCALARS)
    if unknown:  # a silent skip here would quietly narrow T8b's coverage
        sys.exit("refinstall: adversarial answers not in SCALARS: %s" % sorted(unknown))
    SCALARS.update(ADVERSARIAL_ANSWERS)
    LISTS.update(ADVERSARIAL_LISTS)


def render_path(src: Path) -> str:
    """Render a template, deriving both flags from its name.

    The single place the file-type rule is applied. Passing `escape` by hand at each
    call site meant `CLAUDE.section.md.tmpl` could be — and was — rendered under a
    different rule than every other `.md.tmpl`, with nothing to catch it.
    """
    is_json = src.name.endswith(".json.tmpl")
    # Only these two file types embed variables in string literals; `.md.tmpl` prose
    # must stay unescaped or a path's backslash renders as `\\` and a newline-joined
    # fenced block collapses to one `\n`-separated line.
    escape = is_json or src.name.endswith(".py.tmpl")
    return render(src.read_text(encoding="utf-8"), is_json, escape)


def gate_entries() -> str:
    """Expand GATE_COMMANDS into one gate block each (SKILL.md Phase 4, step 5).

    Markdown, so no escaping — this only ever lands in `quality-gates.md.tmpl`. The
    command is both the gate name and the `Run` line; Pass/Fail/Skip are conservative
    defaults the human refines. Empty list ⇒ an instruction to add gates, never a
    blank registry (the guide forbids relying on an empty one)."""
    cmds = [c.strip() for c in LISTS["GATE_COMMANDS"] if c.strip()]
    if not cmds:
        return ("_No gate commands were detected. Add at least one — a project with "
                "no gate cannot enforce one._")
    return "\n\n".join(
        "### %s\n**Run**: `%s`\n**Pass**: exits 0.\n"
        "**Fail**: non-zero exit — fix the cause, never the symptom.\n"
        "**Skip if**: never." % (c, c) for c in cmds)


# The QA-only guide rows in the PATTERNS index. Emitted iff the guides are actually
# installed (the qa preset), so the developer scaffold does not index files that
# aren't there. Trailing newline per row so the following table row stays on its own
# line; empty string when absent, which collapses cleanly (a blank line would end the
# GFM table). Keyed off the preset union, the same signal that installs the guides.
QA_GUIDE_ROWS_TEXT = (
    "| Test design (deterministic, isolated, framework conventions) | "
    "[`.agentic/guides/standards/test-design-pattern.md`]"
    "(.agentic/guides/standards/test-design-pattern.md) |\n"
    "| Flaky-test protocol (classify → ledger → root-cause → burn-in) | "
    "[`.agentic/guides/standards/flaky-protocol.md`]"
    "(.agentic/guides/standards/flaky-protocol.md) |\n"
)
QA_GUIDE_ROWS = QA_GUIDE_ROWS_TEXT if {
    "guides/test-design-pattern", "guides/flaky-protocol"} <= PRESET_TEMPLATE_IDS else ""

# Screen 3's per-capability autonomy answers. `--defaults` accepts every mode
# default, so nothing is tightened — the block is the "no overrides" note. A real
# interview emits one bullet per capability the user set stricter than its mode row.
AUTONOMY_OVERRIDES = (
    "_No per-repository overrides — every capability follows the active mode's row "
    "above._")


def render(text: str, is_json: bool, escape: bool) -> str:
    q = esc if escape else (lambda v: v)
    # Derived, not raw variables: built by the installer from interview answers or
    # what it installs. Only in markdown templates, so never escaped.
    text = text.replace("{{GATE_ENTRIES}}", gate_entries())
    text = text.replace("{{QA_GUIDE_ROWS}}", QA_GUIDE_ROWS)
    # --defaults accepts each capability's mode default, so no Screen-3 tightening.
    text = text.replace("{{AUTONOMY_OVERRIDES}}", AUTONOMY_OVERRIDES)
    for var in NEWLINE_VARS:
        text = text.replace("{{%s}}" % var, q("\n".join(LISTS[var])))
    # Not a scalar: JSON array elements carry their own quotes; the comma-joined
    # prose form (`.md.tmpl`) sits outside any literal. Neither takes `esc`.
    escalate = LISTS["ESCALATE_ON"]
    text = text.replace("{{ESCALATE_ON}}",
                        ",".join(json.dumps(x) for x in escalate) if is_json
                        else ",".join(escalate))
    for k, v in SCALARS.items():
        text = text.replace("{{%s}}" % k, q(v))
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
    content = render_path(src) if src.name.endswith(".tmpl") else src.read_text()
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
    ("session_learnings_notice.py", "session_learnings_notice.py", "hooks/session-learnings-notice"),
    ("context_monitor.py", "context_monitor.py", "hooks/context-monitor"),
    ("prompt_scan_guard.py", "prompt_scan_guard.py", "hooks/prompt-scan-guard"),
    ("human_gated_commands.py.tmpl", "human_gated_commands.py", "hooks/human-gated-commands"),
    ("guarded_write_paths.py.tmpl", "guarded_write_paths.py", "hooks/guarded-write-paths"),
    ("migration_notice.py.tmpl", "migration_notice.py", "hooks/migration-notice"),
    ("lint_on_save.py.tmpl", "lint_on_save.py", "hooks/lint-on-save"),
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
    # Same rule for lint-on-save when no check command was configured.
    if tid == "hooks/lint-on-save" and not SCALARS["LINT_CHECK_COMMAND"]:
        continue
    copy_tpl("hooks/claude/" + src, ".claude/hooks/" + dest, tid)

# --- Phase 4 step 2: settings deep-merge --------------------------------------
frag = json.loads(render_path(TPL / "hooks/settings-fragment.json.tmpl"))
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

# Local hook/session state must never be committed to the host repo: the review
# stamp would make a fresh clone believe a diff was already approved, and the
# prompt-scan audit log is per-machine noise. Append-if-absent, idempotent.
LOCAL_STATE_IGNORES = [".claude/.review-stamp", ".claude/checkpoints/", ".agentic/state/"]
gi = TARGET / ".gitignore"
existing = gi.read_text().splitlines() if gi.exists() else []
additions = [line for line in LOCAL_STATE_IGNORES if line not in existing]
if additions:
    text = "\n".join(existing) if existing else ""
    if text and not text.endswith("\n"):
        text += "\n"
    gi.write_text((text + "\n".join(additions) + "\n") if text else "\n".join(additions) + "\n")

# --- Phase 4 step 4: governance -----------------------------------------------
BEGIN = "<!-- agentic-os:begin v%s -->" % VERSION
END = "<!-- agentic-os:end -->"
claude_block = render_path(TPL / "governance/CLAUDE.section.md.tmpl")
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
    # Prefer a `.tmpl` source when one exists (quality-gates renders GATE_ENTRIES);
    # the rest are copied verbatim. Dest is always the bare `.md`.
    src = "guides/standards/%s.md" % g
    if not (TPL / src).exists():
        src += ".tmpl"
    if (TARGET / dest).exists():  # existing-guide rule: skip + owner user
        JOURNAL["files"][dest] = {"sha256": sha(TARGET / dest), "template": "guides/" + g,
                                  "owner": "user"}
    else:
        copy_tpl(src, dest, "guides/" + g)
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
