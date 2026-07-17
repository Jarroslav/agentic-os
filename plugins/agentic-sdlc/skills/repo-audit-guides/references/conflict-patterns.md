# Conflict Patterns

Rubric for detecting contradictory or overlapping guidance during the repository audit. Apply every pattern below to the documentation and assistant setup you scan. Findings produced here go into the report section headed `## Conflict And Overlap Analysis`.

> Why this matters: a later planting phase writes generated guides under `.agentic/guides/` and updates entrypoints through gated diffs. Any conflict the audit waves through becomes load-bearing in that phase — either corrupting what gets written or institutionalizing the wrong rule. Frame every impact statement against that write phase.

## Finding format

Report each match with exactly four fields:

| Field | Content |
|---|---|
| Severity | `critical` or `important` — closed scale, no third value |
| Evidence | file path plus the quoted or closely paraphrased text that triggered the match |
| Impact on foundation | what the planting phase would corrupt or institutionalize if left unresolved |
| Required decision | one of `halt`, `ask user`, `merge`, `replace` |

Severity in one sentence: escalate to `critical` when the conflict weakens safety semantics — approval gates, write protection, destructive-command guards, install side effects; redundancy without incompatibility stays `important`.

Disposition vocabulary:

- `halt` — stop; do not reach planting until the conflict is resolved.
- `ask user` — present the conflict; the user picks the authority or path forward.
- `merge` — combine sources; allowed only where manifest or CI evidence settles which side is right.
- `replace` — supersede stale generated content via a later gated diff. Never applied to human-authored text.

## Pattern index

| # | Pattern | `critical` trigger | Default disposition |
|---|---|---|---|
| 1 | Approval bypass | bypass reaches writes, installs, entrypoints, destructive commands, or external effects | `halt` when critical; else `ask user` |
| 2 | Dirty-branch work | overwrite or reset of uncommitted work encouraged | `halt`; `ask user` before any later write |
| 3 | Duplicate agentic sources | duplicated sources carry incompatible rules | `ask user`; `halt` if no safe merge exists |
| 4 | Competing SDLC ownership | approval, verification, or write-safety semantics altered | `ask user`; `halt` on safety change |
| 5 | Competing assistant commands | disputed commands have destructive or release side effects | `ask user`; `merge` only with manifest/CI evidence |
| 6 | Managed region drift | malformed markers endanger human-authored text | `halt`; `ask user` / `replace` for stale content |
| 7 | Source-of-truth conflict | release, deployment, security, or data-migration instructions diverge | `ask user` unless manifest/CI evidence decides |

## 1. Approval bypass

**Detect.** Any instruction source that lets agents skip explicit user approval, hide or suppress diffs, auto-install dependencies, or auto-edit entrypoint files.

**Severity.** `critical` when the bypass covers repo writes, installs, entrypoint edits, destructive commands, or external side effects. `important` when it is limited to low-risk generated reports or the wording is too ambiguous to classify.

**Impact.** Planting inherits the weakest gate it finds; an approval hole audited past today is an approval hole in every guide written tomorrow.

**Decision.** `halt` at `critical`; `ask user` at `important`.

## 2. Dirty-branch work

**Detect.** Guidance to disregard `git status`, tolerance for clobbering uncommitted work, or the absence of any branch/worktree hygiene rule at all.

**Severity.** `critical` when overwriting or resetting uncommitted work is actively encouraged. `important` when hygiene is merely missing.

**Impact.** The planting phase writes files; on a dirty tree those writes can silently destroy in-progress human work.

**Decision.** `halt` at `critical`. Regardless of severity: `ask user` before any later write while unrelated dirty files are present.

## 3. Duplicate agentic sources

**Detect.** More than one entrypoint, command directory, skill directory, or subagent directory claiming authority over the same workflow.

**Severity.** `critical` when the duplicated rules are incompatible with each other. `important` when the duplicates are redundant but consistent.

**Impact.** Planting must choose one home for generated guidance; a second live authority keeps steering agents against the foundation from wherever it was left standing.

**Decision.** `ask user` to designate the single authority. `halt` when no merge can preserve the safety guarantees of both sources.

## 4. Competing SDLC ownership

**Detect.** Pre-existing agents, skills, commands, or prompt files — Copilot instruction files included — that overlap this plugin's intake, planning, gate, or journal responsibilities; text directing agents to ignore the generated tree at `.agentic/guides/`; wrappers around the plugin that change its approval, verification, or write-safety behavior.

**Severity.** `critical` when safety semantics change. `important` for overlap that leaves safety behavior intact.

**Impact.** Two SDLC owners emit contradictory instructions into the same agent context; planting under a contested owner writes that contradiction into the foundation permanently.

**Decision.** `ask user` who owns the SDLC — agentic-sdlc or the incumbent. `halt` when the ownership dispute also alters approval, write-safety, or destructive-command behavior.

## 5. Competing assistant commands

**Detect.** Root entrypoints (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) disagreeing on test, lint, branch, commit, or approval commands; tool-specific files contradicting the root; slash commands documented for hosts that do not support them.

**Severity.** `critical` when the disputed commands carry destructive or release side effects. `important` when only validation consistency suffers.

**Impact.** Generated guides must cite one command set; planting the wrong one makes every future run a gamble on which document the agent happened to read first.

**Decision.** `ask user` for the authoritative command. `merge` is permitted only when a manifest or CI definition proves which command is real — cite that evidence in the finding.

## 6. Managed region drift

**Detect.** Managed-region start/end markers in entrypoints that fail to pair; managed blocks referencing files that no longer exist; human-authored rules placed inside managed blocks that clash with generated text outside them.

**Severity.** `critical` for malformed markers — an automated merge over broken boundaries can delete or mangle human-authored text. `important` for references that are stale but structurally intact.

**Impact.** Planting rewrites managed regions in place; broken markers turn a surgical update into a destructive one.

**Decision.** `halt` on malformed markers. For stale generated content: `ask user`, or `replace` through a later gated diff.

## 7. Source-of-truth conflict

**Detect.** README, entrypoints, CI configuration, and manifests naming different setup or test flows; default branch or ticket prefix diverging between documents; docs contradicting the conventions visible in commit history.

**Severity.** `important` by default. Escalate to `critical` when the divergence touches release, deployment, security, or data-migration instructions.

**Impact.** Generated guides ground on repository facts; conflicting facts either block grounding or plant a wrong fact as canon.

**Decision.** `ask user` — unless manifest or CI evidence resolves the conflict decisively, in which case record the evidence and proceed with the resolved value.

## Scope

This reference covers detection, classification, and disposition only. It does not define the audit report's overall structure, prescribe merge algorithms, or enumerate host platforms, CI systems, or manifest formats — evidence sources are cited generically in findings.
