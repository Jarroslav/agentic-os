#!/usr/bin/env python3
"""Governance docs promise only what the install delivers.

The blind role-grading baseline (2026-07-27) found that presets which skip the
git layer install governance text mandating enforcement they don't ship: a
CLAUDE.md block citing `precommit_review_gate.py` / `.githooks/pre-commit` /
`install-git-hooks.sh` none of which the union scaffolds, and a PATTERNS.md
index linking guides the preset never installs. This check runs against any
scaffolded target and asserts, on the rendered output rather than the
templates:

1. Every enforcement artifact the CLAUDE.md managed block cites —
   `.claude/hooks/*.py`, `.githooks/*`, `scripts/*.sh` — exists in the target.
2. Every `.agentic/guides/**/*.md` file link in PATTERNS.md resolves (italic
   parentheticals are forward references, e.g. the post-`/sdlc:qa-init` path,
   and are excluded — same rule as the T1 inline check).
3. The agent-registry orchestration-rules bullet names no orchestration
   command whose `.claude/commands/<name>.md` file is absent.
4. `AGENTS.md` and the rendered `ai-policy.md` cite no uninstalled enforcement
   artifact either — the 2026-07-28 D4 re-grade found the PR #33 conditionals
   covered CLAUDE/PATTERNS/registry while a portfolio-only install still
   promised `write_scope_guard.py` / `instruction_gate.py` /
   `precommit_review_gate.py` in these two files.

Usage: check-governance-promises.py <TARGET_REPO>
"""
import re
import sys
from pathlib import Path

TARGET = Path(sys.argv[1])
problems = []

# Every way a governance doc can name an enforcement artifact by path.
CITATION = re.compile(
    r"(?:\.claude/hooks/[\w-]+\.py|\.githooks/[\w-]+|scripts/[\w-]+\.sh)")

# --- 1. CLAUDE.md managed block cites no uninstalled enforcement artifact ----
claude = (TARGET / "CLAUDE.md").read_text(encoding="utf-8")
block = re.search(r"<!-- agentic-os:begin.*?agentic-os:end -->", claude, re.S)
if not block:
    problems.append("CLAUDE.md: managed agentic-os block missing")
else:
    for rel in sorted(set(CITATION.findall(block.group(0)))):
        if not (TARGET / rel).exists():
            problems.append(
                "CLAUDE.md cites an enforcement artifact that was not installed: %s" % rel)

# --- 2. PATTERNS.md file links all resolve -----------------------------------
patterns_path = TARGET / "PATTERNS.md"
if not patterns_path.exists():
    problems.append("PATTERNS.md not scaffolded")
else:
    body = patterns_path.read_text(encoding="utf-8")
    current = re.sub(r"\*\([^)]*\)\*", "", body)  # drop forward references
    for rel in sorted({m for m in re.findall(r"\.agentic/guides/[a-z0-9/-]+\.md",
                                             current)}):
        if not (TARGET / rel).exists():
            problems.append("PATTERNS.md links a guide that was not installed: %s" % rel)

# --- 3. registry names no absent orchestration command -----------------------
# Scan the WHOLE file, not just the section after "## Orchestration rules" —
# the preamble used to enumerate both commands unconditionally, and the old
# heading-split scan was blind to it (found by the 2026-07-28 grading refuter).
registry_path = TARGET / ".agentic/guides/agent-registry.md"
if registry_path.exists():
    rules = registry_path.read_text(encoding="utf-8")
    for name in ("pipeline-orchestrator", "dispatch"):
        if "`%s`" % name in rules and not (TARGET / (".claude/commands/%s.md" % name)).exists():
            problems.append(
                "agent-registry names `%s`, but "
                ".claude/commands/%s.md was not installed" % (name, name))
else:
    problems.append(".agentic/guides/agent-registry.md not scaffolded")

# --- 4. AGENTS.md + ai-policy.md cite no uninstalled enforcement artifact ----
for rel in ("AGENTS.md", ".agentic/guides/policy/ai-policy.md"):
    doc = TARGET / rel
    if not doc.exists():
        problems.append("%s not scaffolded" % rel)
        continue
    for cited in sorted(set(CITATION.findall(doc.read_text(encoding="utf-8")))):
        if not (TARGET / cited).exists():
            problems.append(
                "%s cites an enforcement artifact that was not installed: %s"
                % (rel, cited))

for p in problems:
    print("  " + p)
sys.exit(1 if problems else 0)
