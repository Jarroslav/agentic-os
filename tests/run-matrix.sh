#!/usr/bin/env bash
# Acceptance matrix. Executes the deterministic parts of the agentic-init
# skill (via tests/lib/refinstall.py, the reference executor) against fixture
# repos and asserts T1–T8. Model-driven phases (interview, generation, live
# AskUserQuestion) are out of scope here — see tests/README.md.
set -uo pipefail
ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
PLUGIN="$ROOT/plugins/agentic-os"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
PASS=0; FAIL=0
ok()   { echo "ok   $1"; PASS=$((PASS+1)); }
bad()  { echo "FAIL $1"; FAIL=$((FAIL+1)); }
assert(){ if eval "$2"; then ok "$1"; else bad "$1"; fi; }

echo "== T1 fresh install =="
FRESH="$WORK/fresh"
bash "$ROOT/tests/fixtures/make-fresh.sh" "$FRESH" >/dev/null
python3 "$ROOT/tests/lib/refinstall.py" "$PLUGIN" "$FRESH" >/dev/null
( cd "$FRESH" && bash scripts/install-git-hooks.sh >/dev/null )

# py_compile every scaffolded hook
if python3 -m py_compile "$FRESH"/.claude/hooks/*.py 2>/dev/null; then ok "hooks py_compile"; else bad "hooks py_compile"; fi
# ...and every hook must *load*, not merely compile (agentic-doctor Check 2b).
# Asserted here, on the pristine scaffold: T5's check-upgrade.py appends to
# $FRESH/.claude/hooks/subagent_gate.py and never reverts it.
python3 "$ROOT/tests/lib/check-hooks-import.py" "$FRESH" && ok "scaffolded hooks import cleanly" || bad "scaffolded hooks import cleanly"
# settings wiring
assert "settings valid JSON" "python3 -c 'import json;json.load(open(\"$FRESH/.claude/settings.json\"))'"
assert "Stop gate wired"        "grep -q '\"Stop\"' '$FRESH/.claude/settings.json'"
assert "SubagentStop gate wired" "grep -q '\"SubagentStop\"' '$FRESH/.claude/settings.json'"
assert "PreToolUse Bash wired"  "grep -q 'precommit_review_gate.py' '$FRESH/.claude/settings.json'"
assert "secret deny present"    "grep -q 'Read(.env' '$FRESH/.claude/settings.json'"
# HUMAN_GATED_COMMANDS fixture (the interview-driven union itself is out of scope
# for this deterministic harness): both the generic default and the stack-profile-
# recommended addition the fixture supplies render through into the scaffolded hook.
assert "human-gated fixture renders (generic default)" "grep -q 'git push origin main' '$FRESH/.claude/hooks/human_gated_commands.py'"
assert "human-gated fixture renders (stack addition)"  "grep -q 'supabase db push' '$FRESH/.claude/hooks/human_gated_commands.py'"
# git hook installed + marker + no {{ leftovers
assert "git pre-commit installed" "test -f '$FRESH/.git/hooks/pre-commit'"
assert "local state gitignored" "grep -q 'review-stamp' '$FRESH/.gitignore' && grep -q 'agentic/state' '$FRESH/.gitignore'"
assert "git hook carries marker"  "grep -q 'agentic-os:' '$FRESH/.git/hooks/pre-commit'"
assert "no unresolved placeholders" "! grep -rlF '{{' '$FRESH/.claude' '$FRESH/.agentic' '$FRESH/AGENTS.md' '$FRESH/PATTERNS.md' '$FRESH/CLAUDE.md' 2>/dev/null | grep -q ."
# scorecard coverage: every canonical contract + pointer + governance has an entry
python3 - "$FRESH" <<'PY' && ok "scorecard covers fleet" || bad "scorecard covers fleet"
import json,sys,glob,os
t=sys.argv[1]
sc=json.load(open(t+"/docs/audits/instruction-scorecard.json"))["files"]
need=[]
for p in glob.glob(t+"/.agentic/agents/*.md")+glob.glob(t+"/.claude/agents/*.md"):
    need.append(os.path.relpath(p,t))
need+=["CLAUDE.md","AGENTS.md","PATTERNS.md"]
missing=[n for n in need if n not in sc]
sys.exit(1 if missing else 0)
PY
# agent-registry table integrity (deterministic half of agentic-doctor Check 8)
python3 "$ROOT/tests/lib/check-registry.py" "$FRESH" && ok "agent-registry table intact" || bad "agent-registry table intact"
# PATTERNS.md generated-guide append point is a real table row (same invariant, shared gfm.py)
python3 "$ROOT/tests/lib/check-patterns.py" "$FRESH" && ok "PATTERNS.md guide-row marker intact" || bad "PATTERNS.md guide-row marker intact"
# ai-policy carries the autonomy-override block (answers land somewhere,
# not discarded); --defaults renders the "no overrides" note.
python3 - "$FRESH" <<'PY' && ok "ai-policy autonomy-override block rendered" || bad "ai-policy autonomy-override block rendered"
import sys, pathlib
body = pathlib.Path(sys.argv[1], ".agentic/guides/policy/ai-policy.md").read_text()
problems = []
if "### Per-repository overrides" not in body:
    problems.append("override section missing")
if "{{AUTONOMY_OVERRIDES}}" in body or "{{" in body.split("### Per-repository")[-1].split("## Size")[0]:
    problems.append("override placeholder left unrendered")
if "No per-repository overrides" not in body:
    problems.append("--defaults should render the 'no overrides' note")
for p in problems:
    print("  " + p)
sys.exit(1 if problems else 0)
PY
# PATTERNS.md indexes no guide it did not install (the qa-only rows are conditional)
python3 - "$FRESH" <<'PY' && ok "PATTERNS.md guide links all resolve" || bad "PATTERNS.md guide links all resolve"
import re, sys, pathlib
t = pathlib.Path(sys.argv[1])
body = (t / "PATTERNS.md").read_text()
# Drop italic parentheticals — they document forward references (e.g. the
# `testing/qa-strategy.md` path that only exists "after /sdlc:qa-init"), not current
# index entries. Then every `.agentic/guides/**/*.md` file link that remains (not
# directory links like guides/policy/) must resolve — a dangling row anywhere in the
# index, not just under standards/.
current = re.sub(r'\*\([^)]*\)\*', '', body)
missing = sorted({m for m in re.findall(r'\.agentic/guides/[a-z0-9/-]+\.md', current)
                  if not (t / m).exists()})
for m in missing:
    print("  PATTERNS.md links a guide that was not installed: %s" % m)
sys.exit(1 if missing else 0)
PY
# quality-gates registry is populated from GATE_COMMANDS, not the shipped stub
python3 - "$FRESH" <<'PY' && ok "quality-gates registry populated" || bad "quality-gates registry populated"
import sys, pathlib
body = pathlib.Path(sys.argv[1], ".agentic/guides/standards/quality-gates.md").read_text()
problems = []
if "{{" in body:
    problems.append("unrendered placeholder remains")
if "Example: lint" in body or "(project lint command)" in body:
    problems.append("shipped stub example survived — GATE_ENTRIES not expanded")
# every detected gate command from the fixture must appear as a Run line
for cmd in ("npx tsc --noEmit", "npm run lint -- --max-warnings 0", "npm test"):
    if "**Run**: `%s`" % cmd not in body:
        problems.append("missing gate for %r" % cmd)
for p in problems:
    print("  " + p)
sys.exit(1 if problems else 0)
PY
# empty GATE_COMMANDS must render an "add a gate" note, never a blank registry
python3 - "$ROOT" <<'PY' && ok "quality-gates empty-list renders a note" || bad "quality-gates empty-list renders a note"
import sys
# refinstall runs an install at import time (needs argv), so lift just gate_entries
# and stub its one dependency. A broken slice raises (ValueError/SyntaxError/KeyError)
# and fails the check — it cannot pass vacuously.
src = open(sys.argv[1] + "/tests/lib/refinstall.py").read()
g = {"LISTS": {"GATE_COMMANDS": []}}
start = src.index("def gate_entries")
end = src.index("\n\n\n", start)
exec(src[start:end], g)
out = g["gate_entries"]()
problems = []
if "###" in out or "**Run**" in out:
    problems.append("empty list produced a gate block: %r" % out)
if not out.strip():
    problems.append("empty list produced a blank registry")
if "add" not in out.lower():
    problems.append("empty-list note does not tell the user to add a gate: %r" % out)
for p in problems:
    print("  " + p)
sys.exit(1 if problems else 0)
PY
# native commit blocked without review stamp
( cd "$FRESH" && echo x > f.txt && git add f.txt
  if git commit -qm try 2>/dev/null; then exit 1; else exit 0; fi ) \
  && ok "unreviewed commit blocked" || bad "unreviewed commit blocked"
# golden manifest
( cd "$FRESH" && git status --porcelain | awk '{print $2}' | sort ) > "$WORK/manifest.txt"
GOLDEN="$ROOT/tests/golden/fresh-developer-manifest.txt"
if [ -f "$GOLDEN" ]; then
  assert "golden manifest matches" "diff -q '$GOLDEN' '$WORK/manifest.txt' >/dev/null"
else
  mkdir -p "$ROOT/tests/golden"; cp "$WORK/manifest.txt" "$GOLDEN"; ok "golden manifest recorded (first run)"
fi

echo "== T2 mature non-destructive =="
MAT="$WORK/mature"
bash "$ROOT/tests/fixtures/make-mature.sh" "$MAT" >/dev/null
python3 "$ROOT/tests/lib/refinstall.py" "$PLUGIN" "$MAT" >/dev/null 2>"$WORK/mat.err"
( cd "$MAT" && bash scripts/install-git-hooks.sh >/dev/null )
assert "CLAUDE.md house rules survive" "grep -q 'House Rules' '$MAT/CLAUDE.md'"
assert "CLAUDE.md gained managed block" "grep -q 'agentic-os:begin' '$MAT/CLAUDE.md'"
# content outside markers unchanged: strip the managed block, compare to original
python3 - "$MAT" <<'PY' && ok "CLAUDE.md changed only in markers" || bad "CLAUDE.md changed only in markers"
import re,sys
t=sys.argv[1]
body=open(t+"/CLAUDE.md").read()
outside=re.sub(r"<!-- agentic-os:begin.*?agentic-os:end -->","",body,flags=re.S).strip()
sys.exit(0 if outside=="# House Rules\n\nThis is the team's own hand-written guidance. It must survive the install verbatim." else 1)
PY
assert "pre-existing settings hook preserved" "grep -q 'team_notify.py' '$MAT/.claude/settings.json'"
assert "agentic hooks merged in"  "grep -q 'subagent_gate.py' '$MAT/.claude/settings.json'"
assert "colliding agent NOT overwritten" "grep -q 'SENTINEL team security-reviewer' '$MAT/.agentic/agents/security-reviewer.md'"
assert "foreign pre-commit chained (.local)" "test -f '$MAT/.git/hooks/pre-commit.local'"
assert "foreign hook body preserved" "grep -q 'TEAM-PRECOMMIT-RAN' '$MAT/.git/hooks/pre-commit.local'"

echo "== T3 role matrix (static) =="
python3 "$ROOT/tests/lib/check-presets.py" "$PLUGIN" && ok "preset matrix + ID resolution" || bad "preset matrix + ID resolution"
python3 "$ROOT/tests/lib/check-discovery-priors.py" "$PLUGIN" && ok "Tier-1 marker-prior table" || bad "Tier-1 marker-prior table"
python3 "$ROOT/tests/lib/check-mature-adoption.py" && ok "mature .agents adoption detection" || bad "mature .agents adoption detection"

echo "== T3b explicit roles, additive union, and MCP states =="
ROLE_WORK="$WORK/role-composition"
for role_target in ba-po mixed mcp unavailable; do bash "$ROOT/tests/fixtures/make-fresh.sh" "$ROLE_WORK/$role_target" >/dev/null; done
python3 "$ROOT/tests/lib/refinstall.py" "$PLUGIN" "$ROLE_WORK/ba-po" \
  --presets ba-po --mcp-state without-mcp >/dev/null
python3 "$ROOT/tests/lib/refinstall.py" "$PLUGIN" "$ROLE_WORK/mixed" \
  --presets ba-po --mcp-state without-mcp >/dev/null
echo "user-owned dispatcher" > "$ROLE_WORK/mixed/.agentic/agents/dispatcher.md"
python3 "$ROOT/tests/lib/refinstall.py" "$PLUGIN" "$ROLE_WORK/mixed" \
  --presets ba-po,developer --mcp-state without-mcp --reinstall >/dev/null 2>&1
python3 "$ROOT/tests/lib/refinstall.py" "$PLUGIN" "$ROLE_WORK/mcp" \
  --presets ba-po --mcp-state configured >/dev/null
python3 "$ROOT/tests/lib/refinstall.py" "$PLUGIN" "$ROLE_WORK/unavailable" \
  --presets ba-po --mcp-state unavailable >/dev/null
python3 "$ROOT/tests/lib/check-role-composition.py" "$ROLE_WORK/ba-po" \
  "$ROLE_WORK/mixed" "$ROLE_WORK/mcp" "$ROLE_WORK/unavailable" && ok "role composition + MCP paths" || bad "role composition + MCP paths"

echo "== T3c ba-po operating model =="
python3 "$ROOT/tests/lib/check-ba-po-operating-model.py" "$ROLE_WORK/ba-po" \
  "$PLUGIN/presets/evals/ba-po.json" && ok "ba-po guide + eval scenarios" || bad "ba-po guide + eval scenarios"
DEV_ONLY="$WORK/developer-only"
bash "$ROOT/tests/fixtures/make-fresh.sh" "$DEV_ONLY" >/dev/null
python3 "$ROOT/tests/lib/refinstall.py" "$PLUGIN" "$DEV_ONLY" \
  --presets developer --mcp-state without-mcp >/dev/null
if test ! -e "$DEV_ONLY/.agentic/guides/standards/ba-po-operating-model.md"; then
  ok "ba-po guide isolated from developer-only install"
else
  bad "ba-po guide isolated from developer-only install"
fi

echo "== T3d devops incident triage =="
OPS_WORK="$WORK/devops-only"
bash "$ROOT/tests/fixtures/make-fresh.sh" "$OPS_WORK" >/dev/null
python3 "$ROOT/tests/lib/refinstall.py" "$PLUGIN" "$OPS_WORK" \
  --presets devops --mcp-state without-mcp >/dev/null
python3 "$ROOT/tests/lib/check-incident-triage.py" "$OPS_WORK" \
  "$PLUGIN/presets/evals/devops.json" && ok "devops triage pair + eval scenarios" || bad "devops triage pair + eval scenarios"
if test ! -e "$DEV_ONLY/.agentic/guides/standards/incident-triage.md"; then
  ok "incident-triage guide isolated from developer-only install"
else
  bad "incident-triage guide isolated from developer-only install"
fi

echo "== T3e minimal-union governance promises =="
# The blind role-grading baseline (2026-07-27) found the portfolio scaffold's
# governance docs mandating a pre-commit review gate the preset never installs.
# The CLAUDE/PATTERNS/registry conditionals must render a minimal install whose
# promises all resolve — and must NOT strip the mandate from full installs.
PORT_WORK="$WORK/portfolio-only"
bash "$ROOT/tests/fixtures/make-fresh.sh" "$PORT_WORK" >/dev/null
python3 "$ROOT/tests/lib/refinstall.py" "$PLUGIN" "$PORT_WORK" \
  --presets portfolio --mcp-state without-mcp >/dev/null
python3 "$ROOT/tests/lib/check-governance-promises.py" "$PORT_WORK" \
  && ok "portfolio-only governance promises all resolve" || bad "portfolio-only governance promises all resolve"
# with the core guide rows empty, the generated-guide marker must still be a real row
python3 "$ROOT/tests/lib/check-patterns.py" "$PORT_WORK" && ok "portfolio PATTERNS.md marker row intact" || bad "portfolio PATTERNS.md marker row intact"
assert "portfolio CLAUDE.md drops the review-gate mandate" "! grep -q 'precommit_review_gate' '$PORT_WORK/CLAUDE.md'"
assert "portfolio registry names no pipeline-orchestrator default" "! grep -q 'default to .pipeline-orchestrator' '$PORT_WORK/.agentic/guides/agent-registry.md'"
# the same check must hold on every other scaffold this harness produces …
python3 "$ROOT/tests/lib/check-governance-promises.py" "$FRESH" \
  && ok "developer governance promises all resolve" || bad "developer governance promises all resolve"
python3 "$ROOT/tests/lib/check-governance-promises.py" "$ROLE_WORK/ba-po" \
  && ok "ba-po governance promises all resolve" || bad "ba-po governance promises all resolve"
python3 "$ROOT/tests/lib/check-governance-promises.py" "$OPS_WORK" \
  && ok "devops governance promises all resolve" || bad "devops governance promises all resolve"
# … while full installs keep the mandate, and the devops variant keeps the gate
# without instructing a spawn of the uninstalled blind-code-reviewer agent.
assert "developer CLAUDE.md keeps the review-gate mandate" "grep -q 'Blind code review before every commit' '$FRESH/CLAUDE.md' && grep -q 'blind-code-reviewer' '$FRESH/CLAUDE.md'"
assert "devops CLAUDE.md keeps the gate, not the reviewer spawn" "grep -q 'precommit_review_gate' '$OPS_WORK/CLAUDE.md' && ! grep -q 'spawn' <(sed -n '/Blind code review/,/Human-gated/p' '$OPS_WORK/CLAUDE.md')"

echo "== T3f security threat modeling =="
SEC_WORK="$WORK/security-only"
bash "$ROOT/tests/fixtures/make-fresh.sh" "$SEC_WORK" >/dev/null
python3 "$ROOT/tests/lib/refinstall.py" "$PLUGIN" "$SEC_WORK" \
  --presets security --mcp-state without-mcp >/dev/null
python3 "$ROOT/tests/lib/check-threat-modeling.py" "$SEC_WORK" \
  "$PLUGIN/presets/evals/security.json" && ok "security threat-modeling pair + eval scenarios" || bad "security threat-modeling pair + eval scenarios"
if test ! -e "$DEV_ONLY/.agentic/guides/standards/threat-modeling.md"; then
  ok "threat-modeling guide isolated from developer-only install"
else
  bad "threat-modeling guide isolated from developer-only install"
fi

echo "== T3g strictest-HITL-wins =="
# The 2026-07-28 D4 re-grade: refinstall hardcoded gated-autonomous, so a
# qa-only / security-only scaffold rendered a policy of record contradicting
# the preset's declared `default_hitl: strict`. The union rule (SKILL.md
# Screen 1) is strictest-wins: strict > gated-autonomous > autonomous.
active_mode() { sed -n 's/^Active mode: \*\*.\([a-z-]*\).\*\*.*/\1/p' "$1/.agentic/guides/policy/ai-policy.md"; }
QA_WORK="$WORK/qa-only"
bash "$ROOT/tests/fixtures/make-fresh.sh" "$QA_WORK" >/dev/null
python3 "$ROOT/tests/lib/refinstall.py" "$PLUGIN" "$QA_WORK" \
  --presets qa --mcp-state without-mcp >/dev/null
assert "qa-only ai-policy active mode is strict"        "[ \"\$(active_mode '$QA_WORK')\" = strict ]"
assert "security-only ai-policy active mode is strict"  "[ \"\$(active_mode '$SEC_WORK')\" = strict ]"
assert "developer ai-policy stays gated-autonomous"     "[ \"\$(active_mode '$FRESH')\" = gated-autonomous ]"
# a strict role joining a gated-autonomous role must tighten the whole union
STRICT_MIX="$WORK/developer-qa"
bash "$ROOT/tests/fixtures/make-fresh.sh" "$STRICT_MIX" >/dev/null
python3 "$ROOT/tests/lib/refinstall.py" "$PLUGIN" "$STRICT_MIX" \
  --presets developer,qa --mcp-state without-mcp >/dev/null
assert "developer+qa union resolves strict"             "[ \"\$(active_mode '$STRICT_MIX')\" = strict ]"
# the enforcement-layer promises of these scaffolds must resolve too
python3 "$ROOT/tests/lib/check-governance-promises.py" "$QA_WORK" \
  && ok "qa-only governance promises all resolve" || bad "qa-only governance promises all resolve"
python3 "$ROOT/tests/lib/check-governance-promises.py" "$SEC_WORK" \
  && ok "security-only governance promises all resolve" || bad "security-only governance promises all resolve"

echo "== T3h data pipeline design =="
DATA_WORK="$WORK/data-only"
bash "$ROOT/tests/fixtures/make-fresh.sh" "$DATA_WORK" >/dev/null
python3 "$ROOT/tests/lib/refinstall.py" "$PLUGIN" "$DATA_WORK" \
  --presets data --mcp-state without-mcp >/dev/null
python3 "$ROOT/tests/lib/check-data-pipeline-design.py" "$DATA_WORK" \
  "$PLUGIN/presets/evals/data.json" && ok "data pipeline-design pair + eval scenarios" || bad "data pipeline-design pair + eval scenarios"
if test ! -e "$DEV_ONLY/.agentic/guides/standards/data-pipeline-design.md"; then
  ok "data guide isolated from developer-only install"
else
  bad "data guide isolated from developer-only install"
fi
assert "data-only ai-policy active mode is strict" "[ \"\$(active_mode '$DATA_WORK')\" = strict ]"
python3 "$ROOT/tests/lib/check-governance-promises.py" "$DATA_WORK" \
  && ok "data-only governance promises all resolve" || bad "data-only governance promises all resolve"

echo "== T3i design experience handoff =="
DESIGN_WORK="$WORK/design-only"
bash "$ROOT/tests/fixtures/make-fresh.sh" "$DESIGN_WORK" >/dev/null
python3 "$ROOT/tests/lib/refinstall.py" "$PLUGIN" "$DESIGN_WORK" \
  --presets design --mcp-state without-mcp >/dev/null
python3 "$ROOT/tests/lib/check-experience-design.py" "$DESIGN_WORK" \
  "$PLUGIN/presets/evals/design.json" && ok "design experience pair + eval scenarios" || bad "design experience pair + eval scenarios"
if test ! -e "$DEV_ONLY/.agentic/guides/standards/experience-design.md"; then
  ok "design guide isolated from developer-only install"
else
  bad "design guide isolated from developer-only install"
fi
assert "design-only ai-policy active mode is strict" "[ \"\$(active_mode '$DESIGN_WORK')\" = strict ]"
python3 "$ROOT/tests/lib/check-governance-promises.py" "$DESIGN_WORK" \
  && ok "design-only governance promises all resolve" || bad "design-only governance promises all resolve"

echo "== T4 idempotency =="
# Snapshot every scaffolded file's content hash, re-run the installer, compare.
# (The fixture never commits the scaffold, so `git status` is the wrong probe —
# idempotency = a re-run does not change already-scaffolded file *content*.)
# Exclude the install journal — it legitimately records each run (not scaffold churn).
snap() { find "$FRESH/.claude" "$FRESH/.agentic" "$FRESH/.githooks" "$FRESH/scripts" \
  "$FRESH/docs" "$FRESH/AGENTS.md" "$FRESH/PATTERNS.md" "$FRESH/CLAUDE.md" -type f 2>/dev/null \
  | grep -v '/install.json$' | sort | xargs shasum -a 256; }
snap > "$WORK/before.txt"
python3 "$ROOT/tests/lib/refinstall.py" "$PLUGIN" "$FRESH" --reinstall >/dev/null 2>&1
snap > "$WORK/after.txt"
if diff -q "$WORK/before.txt" "$WORK/after.txt" >/dev/null; then ok "re-run leaves scaffold byte-identical"; else
  bad "re-run leaves scaffold byte-identical"; diff "$WORK/before.txt" "$WORK/after.txt" | head; fi

echo "== T5 upgrade three-way =="
python3 "$ROOT/tests/lib/check-upgrade.py" "$PLUGIN" "$FRESH" && ok "upgrade classifies unmodified/modified" || bad "upgrade classifies unmodified/modified"

echo "== T6 dependency registration guard =="
python3 "$ROOT/tests/lib/check-deps.py" "$PLUGIN" && ok "pinned registered, OWNER/ skipped" || bad "pinned registered, OWNER/ skipped"

echo "== T7 output-contract parser =="
if bash "$ROOT/tests/t0/run-output-contract.sh" >/dev/null 2>&1; then ok "t0 output-contract suite"; else bad "t0 output-contract suite"; fi

echo "== T8 rendering is total =="
# T8a — `esc()` is lossless, no template single-quotes a placeholder, plain
# substitution still reproduces the silent bug class, and every template renders.
python3 "$ROOT/tests/lib/check-render-escaping.py" "$PLUGIN" && ok "templates render under adversarial answers" || bad "templates render under adversarial answers"
# T8b — the *installer* must apply the escaping rule, not merely be able to. The
# default scalar answers carry no quotes, so they render identically with or
# without `esc()`: dropping it leaves T1 green. Re-scaffold with answers a real
# interview produces, and require the hooks to load with their values intact, the
# JSON to parse, and the .md prose to stay unescaped.
ADV="$WORK/adversarial"
bash "$ROOT/tests/fixtures/make-fresh.sh" "$ADV" >/dev/null
REFINSTALL_ADVERSARIAL=1 python3 "$ROOT/tests/lib/refinstall.py" "$PLUGIN" "$ADV" >/dev/null
python3 "$ROOT/tests/lib/check-hooks-import.py" "$ADV" --round-trip && ok "quote-bearing answers scaffold loadable hooks (values round-trip)" || bad "quote-bearing answers scaffold loadable hooks (values round-trip)"
PYTHONPATH="$ROOT/tests/lib" python3 - "$ADV" <<'PY' && ok "quote-bearing answers scaffold round-trip json + unescaped md" || bad "quote-bearing answers scaffold round-trip json + unescaped md"
import json, pathlib, sys
from render_rule import JSON_ROUND_TRIP, md_over_escape_probes

target = pathlib.Path(sys.argv[1])
problems = []

# `json.loads` succeeding proves the render did not *break* the file. An escape that
# strips `"` also parses — `sh -c "npm run dev"` silently becomes a different command.
cfg_path = target / ".agentic/agentic-sdlc/config.json"
if not cfg_path.exists():
    problems.append("%s: not scaffolded" % cfg_path.name)
else:
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        for dotted, expected in JSON_ROUND_TRIP.items():
            node = cfg
            for part in dotted.split("."):
                node = node[part]
            if node != expected:
                problems.append("config.json %s: expected %r, got %r" % (dotted, expected, node))
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        problems.append("config.json: %s" % e)

# `.md.tmpl` prose takes the plain value (VARIABLES.md § Rendering). An installer that
# escaped markdown too would leave the *escaped* form of an answer in the rendered
# guides — `\n` where a fenced list needs real line breaks, `\"` inside a command.
# Probing for those exact strings, not for `\"` generally: this repo's own guides
# discuss escaping, and a blanket scan would false-positive on them.
probes = md_over_escape_probes()
for p in sorted(target.rglob("*.md")):
    if ".git" in p.parts:
        continue
    body = p.read_text(encoding="utf-8")
    for probe in probes:
        if probe in body:
            problems.append("%s: over-escaped markdown — found the escaped form %r; "
                            "escaping is for .py.tmpl/.json.tmpl only"
                            % (p.relative_to(target), probe[:48]))
            break
for b in problems:
    print("  " + b)
sys.exit(1 if problems else 0)
PY

echo
echo "MATRIX: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
