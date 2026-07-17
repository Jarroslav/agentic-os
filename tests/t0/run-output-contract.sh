#!/usr/bin/env bash
# t0 cases for the output-contract parser (subagent_gate.py.tmpl).
# Renders the template with the default section list, builds synthetic JSONL
# transcripts, pipes canned Stop/SubagentStop events, asserts exit codes.
set -euo pipefail

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
TMPL="$ROOT/plugins/agentic-os/templates/hooks/claude/subagent_gate.py.tmpl"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

GATE="$WORK/subagent_gate.py"
python3 - "$TMPL" "$GATE" <<'EOF'
import sys
s = open(sys.argv[1]).read()
s = s.replace("{{OUTPUT_CONTRACT_SECTIONS}}", "Summary,Why,Blocking,Non-blocking,Escalate to human")
open(sys.argv[2], "w").write(s)
EOF

PASS=0; FAIL=0
check() { # name expected_exit event_json transcript_text
  local name="$1" expected="$2" event="$3" text="$4"
  local tr="$WORK/t-$RANDOM.jsonl"
  python3 - "$tr" "$text" <<'EOF'
import json, sys
open(sys.argv[1], "w").write(json.dumps(
    {"message": {"role": "assistant", "content": [{"type": "text", "text": sys.argv[2]}]}}) + "\n")
EOF
  local ev; ev=$(python3 -c "import json,sys; e=json.loads(sys.argv[1]); e['transcript_path']=sys.argv[2]; print(json.dumps(e))" "$event" "$tr")
  set +e
  echo "$ev" | python3 "$GATE" 2>"$WORK/stderr.txt"
  local rc=$?
  set -e
  if [ "$rc" -eq "$expected" ]; then
    echo "ok   $name"; PASS=$((PASS+1))
  else
    echo "FAIL $name (expected exit $expected, got $rc)"; cat "$WORK/stderr.txt"; FAIL=$((FAIL+1))
  fi
}

STOP='{"hook_event_name":"Stop","stop_hook_active":false}'
SUB='{"hook_event_name":"SubagentStop","stop_hook_active":false}'

FULL_PASS='## Summary
PASS — all checks green.
## Why
- routine
## Blocking
None
## Non-blocking
None
## Escalate to human
None'

# (a) Summary FAIL => block
check "summary FAIL blocks" 2 "$SUB" '## Summary
FAIL — migration validator found drops.
## Why
- x
## Blocking
- drop column detected
## Non-blocking
None
## Escalate to human
None'

# (b) non-empty Blocking => block, items on stderr
check "non-empty Blocking blocks" 2 "$SUB" '## Summary
PASS with caveats.
## Why
- y
## Blocking
- secret committed in config
## Non-blocking
None
## Escalate to human
None'
grep -q "secret committed" "$WORK/stderr.txt" && { echo "ok     ...items on stderr"; PASS=$((PASS+1)); } || { echo "FAIL   ...items missing on stderr"; FAIL=$((FAIL+1)); }

# (c) non-empty Escalate to human => block with AskUserQuestion instruction
check "escalation demands AskUserQuestion" 2 "$SUB" '## Summary
PASS.
## Why
- z
## Blocking
None
## Non-blocking
None
## Escalate to human
- Existing coverage found for TICKET-42: maintenance / rewrite / refactor / mistake?'
grep -q "AskUserQuestion" "$WORK/stderr.txt" && { echo "ok     ...instructs AskUserQuestion"; PASS=$((PASS+1)); } || { echo "FAIL   ...no AskUserQuestion instruction"; FAIL=$((FAIL+1)); }

# (d) clean PASS => allow
check "clean PASS allows (SubagentStop)" 0 "$SUB" "$FULL_PASS"
check "clean PASS allows (Stop)" 0 "$STOP" "$FULL_PASS"

# (e) missing contract => fail-closed on SubagentStop, lenient on Stop
check "missing contract fail-closed (SubagentStop)" 2 "$SUB" 'Just some prose, no sections at all.'
check "partial contract fail-closed (SubagentStop)" 2 "$SUB" '## Summary
PASS but no other sections.'
check "missing contract lenient (Stop)" 0 "$STOP" 'Conversational answer, not a gate report.'

# lenient Stop still enforces a present contract (the branch plain-Stop wiring reaches)
check "Stop with Blocking items blocks" 2 "$STOP" '## Summary
PASS.
## Blocking
- unresolved secret in diff'

# re-entrancy guard
check "stop_hook_active short-circuits" 0 '{"hook_event_name":"SubagentStop","stop_hook_active":true}' 'irrelevant'

echo
echo "output-contract: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
