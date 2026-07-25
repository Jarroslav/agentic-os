#!/usr/bin/env bash
#
# qa-e2e-smoke-test.sh — self-check for the qa-e2e-generator helper scripts.
#
# Exercises qa-append-event.sh and qa-assemble-meta.sh end-to-end inside a
# throwaway directory: appends two events, drops in the four fixture artifacts,
# assembles meta.json, and echoes both products for a human to eyeball. There
# are no assertions beyond exit status — strict mode means any failing sub-step
# aborts before "SMOKE TEST PASSED" is reached.
#
# Usage: qa-e2e-smoke-test.sh   (no arguments)
#
# Requires: bash + jq. Targets Git Bash / WSL on Windows and native macOS/Linux.
# Exit 0 when every step succeeds; nonzero (with no PASSED line) otherwise.

set -o errexit
set -o nounset
set -o pipefail

# Locate the sibling helper scripts relative to this file.
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
append_script="$script_dir/qa-append-event.sh"
assemble_script="$script_dir/qa-assemble-meta.sh"

# Disposable run directory, cleaned up on any exit.
sandbox=$(mktemp -d)
trap 'rm -rf "$sandbox"' EXIT

# Two appends: one bare, one carrying an extra field.
bash "$append_script" "$sandbox" 0 "smoke-test" "complete"
bash "$append_script" "$sandbox" 1 "smoke-test" "complete" '{"note":"ok"}'

printf '%s\n' '--- events.jsonl ---'
cat "$sandbox/events.jsonl"

# Fixture artifacts that qa-assemble-meta.sh folds into meta.json.
cat > "$sandbox/ac-check.json" <<'JSON'
{"ticket_id":"PROJ-1","title":"t"}
JSON
cat > "$sandbox/context-manifest.json" <<'JSON'
{"framework":{"tool":"playwright"}}
JSON
cat > "$sandbox/complexity-assessment.json" <<'JSON'
{"size":"M"}
JSON
cat > "$sandbox/execution-results.json" <<'JSON'
{"total":1,"passing":1,"failing":0,"fixes_applied":0,"test_files":[]}
JSON

bash "$assemble_script" "$sandbox"

printf '%s\n' '--- meta.json ---'
cat "$sandbox/meta.json"

printf '%s\n' 'SMOKE TEST PASSED'
