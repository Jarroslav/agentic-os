#!/usr/bin/env python3
"""T3: static role-matrix checks — every preset's template IDs resolve to a real
file via the VARIABLES.md mapping, union-safety, and QA-preset invariants."""
import json
import re
import sys
from pathlib import Path

if len(sys.argv) < 2:
    sys.exit("usage: check-presets.py <PLUGIN_ROOT>")
PLUGIN = Path(sys.argv[1]).resolve()
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
               "instruction-auditor", "pr-pipeline-gate", "incident-triage",
               "threat-modeler", "pipeline-designer",
               "experience-designer"}


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

# (2b) settings baseline: every preset must carry the settings fragment and the
#      two hooks the installer force-scaffolds alongside it. The fragment is
#      preset-independent (no placeholders), which is what lets a role *removal*
#      compute its settings subtraction from the pruning rule alone rather than
#      from a per-union re-render. If some future preset omitted the fragment,
#      that reasoning silently breaks and the subtraction would drop entries a
#      remaining role still needs.
SETTINGS_BASELINE = (
    "hooks/settings-fragment",
    "hooks/human-gated-commands",
    "hooks/guarded-write-paths",
)
for name, p in presets.items():
    for need in SETTINGS_BASELINE:
        if need not in p["templates"]:
            print("  preset %s missing settings-baseline ID %s" % (name, need)); fail = 1

# (2c) git-layer co-occurrence: the tracked hook, the gate script it invokes, and
#      the installer that places it are one indivisible unit. `.githooks/pre-commit`
#      runs `python3 .claude/hooks/precommit_review_gate.py precommit || exit $?`
#      as its FIRST action, and chains the repo's own `pre-commit.local` only
#      afterwards. So a preset carrying the hook without the gate script would
#      install a hook that exits non-zero on every commit -- blocking every
#      `git commit` in the repo, out of tree, and silencing the team's own hook
#      too. Splitting the trio across presets makes that state reachable through
#      an ordinary role removal, so assert all-or-nothing per preset.
GIT_LAYER = ("githooks/pre-commit", "hooks/precommit-review-gate", "scripts/install-git-hooks")
for name, p in presets.items():
    present = [t for t in GIT_LAYER if t in p["templates"]]
    if present and len(present) != len(GIT_LAYER):
        missing = [t for t in GIT_LAYER if t not in p["templates"]]
        print("  preset %s splits the git layer: has %s, missing %s"
              % (name, present, missing)); fail = 1

# (3) every cross-plugin asset a preset names must resolve to a real file in the
#     sibling plugin that ships it. Nothing else validates these names — a typo'd
#     entry would ship silently and the installer would journal an asset
#     /agentic-init can never surface. One resolver for both fields, so a third
#     composition axis is a table row rather than another hardcoded sibling path.
#
#     `qe_blueprints` entries are blueprint ids: the filename stem under the
#     catalog, whose stage directory is not part of the id (the id is unique
#     across stages, which the duplicate check below enforces).
def _blueprint_files(root):
    return {p.stem: p for p in root.rglob("*.md")} if root.is_dir() else {}


CROSS_PLUGIN = {
    "sdlc_skills": (
        "agentic-sdlc skill",
        lambda: {d.name: d for d in (PLUGIN.parent / "agentic-sdlc" / "skills").iterdir()
                 if (d / "SKILL.md").is_file()}
        if (PLUGIN.parent / "agentic-sdlc" / "skills").is_dir() else {},
    ),
    "qe_blueprints": (
        "agentic-qe blueprint",
        lambda: _blueprint_files(
            PLUGIN.parent / "agentic-qe" / "skills" / "qe-blueprints"
            / "references" / "catalog"),
    ),
}

for field, (label, resolve) in CROSS_PLUGIN.items():
    available = resolve()
    for name, p in presets.items():
        for entry in p.get(field, []):
            if entry not in available:
                print("  MISSING %s for %s -> %s" % (label, name, entry)); fail = 1
        if len(p.get(field, [])) != len(set(p.get(field, []))):
            print("  DUP %s entry in %s" % (field, name)); fail = 1

# (3b) blueprint ids must be unique across catalog stages, since a preset names
#      the stem alone. Two stages shipping the same stem would make a preset
#      entry ambiguous and the registry-row prune non-deterministic.
_catalog = (PLUGIN.parent / "agentic-qe" / "skills" / "qe-blueprints"
            / "references" / "catalog")
if _catalog.is_dir():
    _stems = [p.stem for p in _catalog.rglob("*.md")]
    _dupes = sorted({s for s in _stems if _stems.count(s) > 1})
    if _dupes:
        print("  AMBIGUOUS blueprint id(s) across stages: %s" % ", ".join(_dupes)); fail = 1

# (3c) REVERSE orphan check for sdlc_skills: a shipped skill a user could ask
#      for by name, that no preset claims, never surfaces at install — the user
#      cannot discover it without already knowing it exists. This is check (1b)
#      pointed the other way, and it needs a different opt-out.
#
#      (1b) reads its registry from VARIABLES.md, so an ID opts OUT of the check
#      by simply not being registered. Skills resolve from the filesystem, so
#      every new skill is orphaned-by-default the moment it lands and there is
#      no "just don't register it" escape. That is why the exemption has to be
#      DECLARED, and why it keys on frontmatter rather than a hardcoded list
#      here — a list in this file would drift from the skills it describes,
#      which is the failure (1b)'s own comment records for hooks/migration-notice.
#
#      The predicate is "allowed to be unclaimed", NOT "forbidden from being
#      claimed": qa-scoping declares itself internal AND is claimed by qa, which
#      is fine. An exclusion rule would fail it.
#
#      Keying on `discoverable: false` (not on the "Not for: direct user
#      invocation" prose) is deliberate: descriptions are YAML-folded, so that
#      clause line-wraps mid-phrase and a naive match finds only one of the
#      three internal skills.
SDLC_SKILL_DIR = PLUGIN.parent / "agentic-sdlc" / "skills"
if SDLC_SKILL_DIR.is_dir():
    claimed_skills = {s for p in presets.values() for s in p.get("sdlc_skills", [])}
    for d in sorted(SDLC_SKILL_DIR.iterdir()):
        skill_md = d / "SKILL.md"
        if not skill_md.is_file() or d.name in claimed_skills:
            continue
        head = skill_md.read_text(encoding="utf-8").split("---")
        frontmatter = head[1] if len(head) > 2 else ""
        if re.search(r"^discoverable:\s*false\s*$", frontmatter, re.M):
            continue                       # declared internal — may be unclaimed
        print("  ORPHANED skill (shipped, in no preset, not declared internal): "
              "%s — add it to a preset's sdlc_skills, or declare "
              "`discoverable: false` if the pipeline invokes it rather than a "
              "user" % d.name)
        fail = 1

# (4) QA preset invariants
qa = presets["qa"]
if qa["default_hitl"] != "strict":
    print("  qa default_hitl != strict"); fail = 1
if qa["default_orchestration"] != "dispatcher":
    print("  qa default_orchestration != dispatcher"); fail = 1
for need in ("agents/test-failure-triage", "agents/work-item-creator"):
    if need not in qa["templates"]:
        print("  qa missing", need); fail = 1

# (5) devops preset invariants — incident triage ships as a pair (agent + guide),
# and the agent contract stays read-only with the no-padding literal intact.
devops = presets["devops"]
for need in ("agents/incident-triage", "guides/incident-triage"):
    if need not in devops["templates"]:
        print("  devops missing", need); fail = 1
triage_tpl = TPL / "agents/core/incident-triage.md.tmpl"
triage_text = triage_tpl.read_text() if triage_tpl.is_file() else ""
if "readonly: true" not in triage_text:
    print("  incident-triage template not readonly"); fail = 1
if "speculative — no direct evidence" not in triage_text:
    print("  incident-triage template lost the no-padding literal"); fail = 1

# (6) security preset invariants — threat modeling ships as a pair, strict HITL,
# and the writer stays scoped to docs/security/ with proposed-only severities.
sec = presets["security"]
for need in ("agents/threat-modeler", "guides/threat-modeling"):
    if need not in sec["templates"]:
        print("  security missing", need); fail = 1
if sec["default_hitl"] != "strict":
    print("  security default_hitl != strict"); fail = 1
tm_tpl = TPL / "agents/core/threat-modeler.md.tmpl"
tm_text = tm_tpl.read_text() if tm_tpl.is_file() else ""
if "readonly: true" in tm_text:
    print("  threat-modeler template must be a writer"); fail = 1
if 'docs/security/**' not in tm_text:
    print("  threat-modeler template lost its docs/security write scope"); fail = 1
if "proposed — owner confirmation pending" not in tm_text:
    print("  threat-modeler template lost the proposed-severity literal"); fail = 1

# (7) data preset invariants — pipeline design ships as a pair, strict HITL,
# and the writer stays scoped to docs/data/ with proposed-only classifications
# and force-tested checks.
dat = presets["data"]
for need in ("agents/pipeline-designer", "guides/data-pipeline-design"):
    if need not in dat["templates"]:
        print("  data missing", need); fail = 1
if dat["default_hitl"] != "strict":
    print("  data default_hitl != strict"); fail = 1
pd_tpl = TPL / "agents/core/pipeline-designer.md.tmpl"
pd_text = pd_tpl.read_text() if pd_tpl.is_file() else ""
if "readonly: true" in pd_text:
    print("  pipeline-designer template must be a writer"); fail = 1
if 'docs/data/**' not in pd_text:
    print("  pipeline-designer template lost its docs/data write scope"); fail = 1
if "classification: proposed — owner confirmation pending" not in pd_text:
    print("  pipeline-designer template lost the proposed-classification literal"); fail = 1
if "a check that has never failed has never been tested" not in pd_text:
    print("  pipeline-designer template lost the force-tested-checks literal"); fail = 1

# (8) design preset invariants — the experience pair ships together, strict
# HITL, and the writer stays scoped to docs/design/ with proposed-only
# decisions and the journey-emotion rule.
des = presets["design"]
for need in ("agents/experience-designer", "guides/experience-design"):
    if need not in des["templates"]:
        print("  design missing", need); fail = 1
if des["default_hitl"] != "strict":
    print("  design default_hitl != strict"); fail = 1
xd_tpl = TPL / "agents/core/experience-designer.md.tmpl"
xd_text = xd_tpl.read_text() if xd_tpl.is_file() else ""
if "readonly: true" in xd_text:
    print("  experience-designer template must be a writer"); fail = 1
if 'docs/design/**' not in xd_text:
    print("  experience-designer template lost its docs/design write scope"); fail = 1
if "decision: proposed — owner confirmation pending" not in xd_text:
    print("  experience-designer template lost the proposed-decision literal"); fail = 1
if "a journey map without emotions is a flowchart" not in xd_text:
    print("  experience-designer template lost the journey-emotion literal"); fail = 1

# (1c) every preset-declared sdlc_skill must be ROUTABLE or explicitly hidden:
#      it needs a row in the agent-registry template, or `discoverable: false`
#      in its own SKILL.md. (1b) proves a shipped skill is claimed by some
#      preset; it says nothing about whether an agent can find the owner once
#      installed. Blind D6 grading caught the gap behaviourally: asked to
#      remember a fact for next quarter, a portfolio-preset agent ran the
#      ownership check CLAUDE.md now mandates, found no registry row owning
#      durable memory, and escalated -- while `role-memory` sat installed and
#      unroutable. 17 of 23 declared skills were in that state, none of them
#      marked non-discoverable. The ownership cue makes an unrouted skill worse
#      than an absent one: a compliant agent escalates instead of using it.
REGISTRY_TMPL = (TPL / "governance/agent-registry.md.tmpl").read_text()
SDLC_SKILLS = PLUGIN.parent / "agentic-sdlc/skills"
declared_skills: dict[str, set[str]] = {}
for _role, _p in presets.items():
    for _s in _p.get("sdlc_skills", []):
        declared_skills.setdefault(_s, set()).add(_role)
for name, prs in sorted(declared_skills.items()):
    if "`%s` skill" % name in REGISTRY_TMPL:
        continue
    skill_md = SDLC_SKILLS / name / "SKILL.md"
    head = skill_md.read_text()[:2000] if skill_md.is_file() else ""
    if re.search(r"^discoverable:\s*false", head, re.M):
        continue
    print("  sdlc_skill %r (presets: %s) has no agent-registry row and is not "
          "discoverable: false -- an installed agent cannot route to it"
          % (name, ",".join(sorted(prs))))
    fail = 1

sys.exit(fail)
