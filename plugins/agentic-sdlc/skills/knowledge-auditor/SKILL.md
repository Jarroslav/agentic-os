---
name: knowledge-auditor
description: >
  Checks a repository's documentation, structure, and agentic-assistant setup
  before any knowledge gets planted into it. Use it to survey, audit, inspect,
  assess, or review repo docs, assistant instructions, Claude/Codex/Gemini/
  GitHub Copilot configuration, subagents, skills, AGENTS.md, CLAUDE.md,
  GEMINI.md, or simply whether a repo is ready for knowledge planting.
metadata:
  author: agentic-os
  version: "0.1.0"
authors:
  - agentic-os
allowed-tools: [Read, Glob, Grep, Bash]
---

# knowledge-auditor

A read-only pass over a repository's documentation, structure, and agentic assistant setup.
It produces a structured audit for a later knowledge-foundation run to draw on when it decides
what to preserve, incorporate, replace, merge, skip, ask the user about, or halt on.

## Purpose

Reach for this skill ahead of knowledge planting, whenever a repository might already carry
project documentation, AI assistant entrypoints, Claude, Codex, Gemini, GitHub Copilot
configuration, skills, subagents, commands, or operating instructions that could conflict with
what's about to be planted.

Repositories that are fresh or belong to a new client typically have no agentic-sdlc output yet.
Leave existing `.agentic/` or `.agentic/guides/` state uninspected and unrated unless the user
specifically asks for agentic-sdlc artifact auditing — absent that request, the audit should rest
on repository evidence and general agentic best practices alone.

If the user does explicitly ask for `.agentic/` to be included, treat it as pre-existing repository
documentation and generated assistant guidance: inventory it as evidence, weigh it against the
repository's other docs and assistant entrypoints, and flag anything stale, conflicting, or
non-portable in that generated guidance.

Cover these surfaces in the audit:

- Repository shape, manifests, modules, and major source directories.
- Documentation such as `README.md`, `CONTRIBUTING.md`, `docs/`, ADRs, runbooks, architecture notes, onboarding guides, and any `*.md` file that appears to contain project documentation or documentation references.
- Explicitly requested agentic-sdlc artifacts such as `.agentic/`, `.agentic/guides/`, run metadata, generated reports, and generated assistant references.
- Assistant setup such as `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.claude/`, `.codex/`, `.agents/`, `.gemini/`, `.copilot/`, `.cursor/`, and similar tool-specific files.
- Claude, Codex, Gemini, and GitHub Copilot assets such as commands, skills, subagents, agents, hooks, settings, prompts, memory files, and managed regions in assistant entrypoints.
- Conflicts between documented commands, workflow rules, approval expectations, assistant entrypoints, skills, subagents, generated guidance, and actual repository evidence.
- Agentic setups that could compete with agentic-sdlc, duplicate agentic-sdlc responsibilities, override its workflow gates, or direct agents to use a different source of truth.

## Read-Only Constraints

This skill is not permitted to write to the repository.

Do not:

- Create guides.
- Update assistant entrypoints.
- Install tools or dependencies.
- Modify docs, generated files, manifests, config files, or git hooks.
- Run destructive commands.
- Run project tests, formatters, migrations, package installs, or commands that mutate caches or lockfiles.
- Perform git operations other than read-only inspection such as `git status`, `git branch --show-current`, `git log`, or `git diff --name-only`.
- Treat existing `.agentic/` artifacts as required, authoritative, or relevant by default.

Shell usage is restricted to read-only inspection commands such as `pwd`, `find`, `rg`, `ls`, `sed -n`, `wc -l`, and read-only git queries.

## Workflow

1. Confirm the repository root with `pwd`.
2. Inventory repository shape and documentation surfaces.
3. Inventory AI assistant setup and entrypoint files.
4. Inventory Claude, Codex, Gemini, GitHub Copilot skills, commands, subagents, agents, settings, hooks, prompts, and other agentic assets.
5. Analyze setup quality with `references/setup-quality-rubric.md` and the best-practice references.
6. Weigh the observed evidence against `references/good-setups.md`, `references/partial-setups.md`, and `references/bad-setups.md`.
7. Identify conflicts using `references/conflict-patterns.md`.
8. Produce planting recommendations using `references/planting-recommendations.md`.
9. Return the structured Markdown audit.

## Discovery Checklist

Stick to read-only discovery and cite evidence as `path:line` wherever possible.

Recommended commands:

```bash
pwd
find . -maxdepth 3 -type f \( -name 'AGENTS.md' -o -name 'CLAUDE.md' -o -name 'GEMINI.md' -o -name 'README.md' -o -name 'CONTRIBUTING.md' \) -not -path '*/node_modules/*' | sort
find . -maxdepth 5 -type f -name '*.md' -not -path '*/node_modules/*' -not -path '*/.git/*' | sort
find . -maxdepth 4 -type d \( -name '.claude' -o -name '.codex' -o -name '.agents' -o -name '.gemini' -o -name '.copilot' -o -name '.cursor' -o -name '.github' -o -name 'docs' \) -not -path '*/node_modules/*' | sort
find . -maxdepth 6 -type f \( -path '*/skills/*' -o -path '*/agents/*' -o -path '*/commands/*' -o -path '*/hooks/*' -o -path '*/prompts/*' -o -name 'settings*.json' -o -name 'copilot-instructions.md' \) -not -path '*/node_modules/*' | sort
rg -n "approval|ask user|test|lint|typecheck|build|pytest|ruff|eslint|branch|commit|subagent|agent|skill|command|hook|managed region|frontmatter|description|progressive disclosure|eval|copilot|gemini|claude|codex|sdlc factory|agentic-sdlc|source of truth|documentation|docs|runbook|ADR" AGENTS.md CLAUDE.md GEMINI.md README.md CONTRIBUTING.md docs .claude .codex .agents .gemini .copilot .cursor .github 2>/dev/null
git status --short
git log --oneline -10
```

When there are many Markdown files, sort them by purpose rather than lumping them into abstract buckets: project overview, setup, architecture, ADR, API, testing, release, operations, assistant instruction, generated guidance, or external documentation reference. For Markdown files that mostly just link elsewhere, note the destination they point to and whether that target is local, external, missing, or ambiguous.

If the user explicitly asks for `.agentic/` to be included, or an assistant entrypoint references `.agentic/`, run this additional targeted read-only discovery too:

```bash
find .agentic -maxdepth 4 -type f | sort
rg -n "test|lint|typecheck|build|approval|ask user|branch|commit|hook|quality|architecture|security|workflow|source of truth" .agentic 2>/dev/null
```

Adjust the paths to whatever actually exists in the repo. Narrow any command that would come back noisy before running it.

## Output Format

Return a structured Markdown audit with exactly these top-level sections:

```markdown
# Knowledge Audit Report

## Executive Summary

## Documentation Map

## Documentation Analysis

## Assistant Setup Analysis

## Agentic Infrastructure Analysis

## Conflict And Overlap Analysis

## Foundation Readiness And Next Steps

## Evidence Appendix
```

Keep the report anchored in concrete repository evidence. Do not score abstract qualities like "development standards clarity" or "repository shape clarity" — this is a readiness analysis, not a report card.

### Executive Summary

3-6 bullets covering:

- What kind of repo this appears to be.
- Whether documentation is usable for knowledge foundation.
- Which assistant setup appears authoritative.
- The highest-risk conflicts or stale surfaces.
- Whether foundation should `preserve`, `incorporate`, `merge`, `replace`, `skip`, `ask user`, or `halt`.

### Documentation Map

List the documentation surfaces as concrete paths:

| Path or group | Purpose | Freshness signal | Foundation use |
|---|---|---|---|
| `README.md` | `<what it covers>` | `<current/stale/unknown evidence>` | `preserve|incorporate|merge|replace|skip|ask user|halt` |

Include:

- Root docs such as `README.md`, `CONTRIBUTING.md`, `SECURITY.md`.
- `docs/`, ADRs, runbooks, architecture notes, onboarding guides, and any project-relevant `*.md`.
- Markdown files that mostly just reference other docs; note whether those references are local, external, missing, or ambiguous.
- `.agentic/` artifacts, but only when the user explicitly asked for them or assistant entrypoints reference them.

### Documentation Analysis

Treat each piece of documentation as either an existing source of truth or as source material the factory could incorporate:

| Topic | Current source | What is reliable | Gaps or stale areas | Foundation action |
|---|---|---|---|---|
| Architecture | `<paths>` | `<specific usable evidence>` | `<specific missing/stale/conflicting detail>` | `preserve|incorporate|merge|replace|skip|ask user|halt` |

Stick to concrete topics such as architecture, setup, commands, testing, quality gates, release, security, API, data, workflows, integrations, and contribution process. Leave out topics that aren't present, unless their absence would block foundation.

### Assistant Setup Analysis

Look at assistant entrypoints and any host-specific setup:

| Surface | Role observed | Authority | Problems | Foundation action |
|---|---|---|---|---|
| `AGENTS.md` | `<repo entrypoint/imports/etc>` | `authoritative|secondary|unused|unclear|conflicting` | `<specific issue or none>` | `preserve|incorporate|merge|replace|skip|ask user|halt` |

Include `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.claude/`, `.codex/`, `.agents/`, `.gemini/`, `.copilot/`, `.cursor/`, and any similar surfaces present in the repo.

### Agentic Infrastructure Analysis

Look at commands, skills, subagents, hooks, settings, prompts, memory files, and generated guidance:

| Asset group | Inventory | What it does | Alignment with docs | Foundation action |
|---|---|---|---|---|
| `.claude/skills/` | `<count and notable skills>` | `<observed responsibilities>` | `<aligned/stale/conflicting with evidence>` | `preserve|incorporate|merge|replace|skip|ask user|halt` |

Flag:

- Assets that already support foundation.
- Assets pointing at stale guide trees or docs.
- Assets that duplicate or compete with agentic-sdlc responsibilities.
- Hooks or settings capable of writing, installing, publishing, pushing, creating PRs, or running destructive commands.

### Conflict And Overlap Analysis

List only concrete conflicts or overlaps — say so plainly if none turned up.

| Conflict or overlap | Evidence | Impact on foundation | Required decision |
|---|---|---|---|
| `<specific conflict>` | `<path:line>` | `<what could go wrong>` | `preserve|incorporate|merge|replace|ask user|halt` |

Give priority to conflicts touching:

- Source of truth for guides or assistant instructions.
- Test, lint, build, commit, branch, release, or PR commands.
- Approval expectations and write safety.
- Agents, skills, commands, or prompts that compete with agentic-sdlc.
- Malformed or stale generated regions.

### Foundation Readiness And Next Steps

Lay out an action plan for knowledge-foundation:

| Area | Finding | Foundation action | Next step |
|---|---|---|---|
| Documentation | `<finding>` | `preserve|incorporate|merge|replace|skip|ask user|halt` | `<specific next action>` |

Rules:

- Use `halt` when continuing forward would bake in an unsafe, destructive, approval-bypassing, or contradictory setup.
- Use `ask user` when authority is unclear or more than one valid setup path exists.
- Use `preserve` when the existing documentation should stay the source of truth agents keep reading directly.
- Use `incorporate` when existing documentation is useful source material, but foundation ought to convert or map that knowledge into factory-owned guidance rather than treat the original files as the long-term target.
- Use `replace` for stale generated content or stale references.
- Use `merge` only when the existing content and the foundation target are already the same authority surface or a compatible managed-region/guide target.
- Use `skip` for areas that are absent or irrelevant.

When the recommendation is `incorporate`, the next step needs to name which existing documentation counts as source material, which factory-owned guidance will absorb that knowledge, and whether the original documentation stays authoritative, becomes legacy, or remains tool-specific. Don't recommend editing the original documentation in place when foundation is meant to own the resulting guidance.

### Evidence Appendix

Provide the evidence table:

| Claim | Evidence | Confidence |
|---|---|---|
| `<claim>` | `<path:line or command output summary>` | `high|medium|low` |

If exact line evidence isn't available, explain why and cite the read-only command that was used instead.

## Reference Index

| Need | Read |
|---|---|
| Setup finding labels | `references/setup-quality-rubric.md` |
| Documentation and repository standards | `references/documentation-standards.md` |
| Assistant setup best practices | `references/assistant-setup-best-practices.md` |
| Skill and subagent best practices | `references/skill-and-subagent-best-practices.md` |
| Strong setup examples | `references/good-setups.md` |
| Partial setup examples | `references/partial-setups.md` |
| Weak setup examples | `references/bad-setups.md` |
| Conflict taxonomy | `references/conflict-patterns.md` |
| Planting action mapping | `references/planting-recommendations.md` |
