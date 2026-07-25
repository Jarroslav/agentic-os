#!/usr/bin/env bash
# scaffold.sh -- qe-blueprints skill helper (skills/qe-blueprints).
#
# Lays down the empty directory skeleton for an agentic QE framework inside a
# tool configuration directory (.claude, .cursor, or .github). This script
# only creates directories; the invoking assistant writes file contents into
# them afterward.
#
# Usage: scaffold.sh [tool-dir]   (default: .claude)
#
# Windows hosts should use the sibling scaffold.ps1, which implements the
# identical contract.

set -euo pipefail

root="${1:-.claude}"

mkdir -p "${root}/agents" "${root}/skills"

# Cursor auto-loads its pointer file only when it lives inside a rules
# directory, so that tool gets one extra folder. The comparison is done on a
# lowercased copy so it stays case-insensitive, matching PowerShell's string
# equality semantics in scaffold.ps1.
root_lc="$(printf '%s' "${root}" | tr '[:upper:]' '[:lower:]')"
if [ "${root_lc}" = ".cursor" ]; then
  mkdir -p "${root}/rules"
fi

echo "Created:"
echo "  ${root}"
echo "  ${root}/agents"
echo "  ${root}/skills"
if [ "${root_lc}" = ".cursor" ]; then
  echo "  ${root}/rules"
fi
