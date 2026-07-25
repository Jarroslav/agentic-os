# scaffold.ps1 -- qe-blueprints skill helper (skills/qe-blueprints).
#
# Lays down the empty directory skeleton for an agentic QE framework inside a
# tool configuration directory (.claude, .cursor, or .github). This script
# only creates directories; the invoking assistant writes file contents into
# them afterward.
#
# Usage: .\scaffold.ps1 [-ToolDir <path>]   (default: .claude)
#
# POSIX hosts should use the sibling scaffold.sh, which implements the
# identical contract.

param(
    [string]$ToolDir = ".claude"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path "$ToolDir\agents" | Out-Null
New-Item -ItemType Directory -Force -Path "$ToolDir\skills" | Out-Null

# Cursor auto-loads its pointer file only when it lives inside a rules
# directory, so that tool gets one extra folder. PowerShell's -eq on strings
# is already case-insensitive, matching the lowercased comparison in
# scaffold.sh.
$needsRules = $ToolDir -eq ".cursor"
if ($needsRules) {
    New-Item -ItemType Directory -Force -Path "$ToolDir\rules" | Out-Null
}

Write-Host "Created:"
Write-Host "  $ToolDir"
Write-Host "  $ToolDir\agents"
Write-Host "  $ToolDir\skills"
if ($needsRules) {
    Write-Host "  $ToolDir\rules"
}
