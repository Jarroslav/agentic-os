#!/usr/bin/env bash
# WS-E acceptance matrix. Executes the deterministic parts of the agentic-init
# skill (via tests/lib/refinstall.py, the reference executor) against fixture
# repos and asserts T1–T7. Model-driven phases (interview, generation, live
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

echo
echo "MATRIX: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
