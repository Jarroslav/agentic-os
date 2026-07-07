# Conflict Patterns

Use these patterns in `## Conflict And Overlap Analysis`. Include severity, evidence, impact on foundation, and the required decision.

## Approval Bypass

Pattern:

- One source requires explicit user approval before writing, while another source tells agents to proceed automatically.
- Assistant instructions say to skip review gates, avoid showing diffs, or modify entrypoints without confirmation.
- Docs tell agents to install tools or dependencies automatically.

Severity:

- `critical` when bypass applies to writes, installs, entrypoint changes, destructive commands, or external side effects.
- `important` when bypass applies only to low-risk generated reports.

Impact:

- Later planting may encode unsafe workflow behavior.

Action:

- `halt` for critical bypass.
- `ask user` for important bypass or unclear wording.

## Dirty-Branch Work

Pattern:

- Instructions tell agents to ignore `git status`.
- Docs allow overwriting uncommitted changes.
- Existing workflow omits branch or worktree checks for generated guide changes.

Severity:

- `critical` if overwrite or reset is encouraged.
- `important` if branch hygiene is merely absent.

Impact:

- Later planting may overwrite user or coworker changes.

Action:

- `halt` if destructive behavior is requested.
- `ask user` before any later write if unrelated dirty files exist.

## Duplicate Agentic Sources

Pattern:

- Multiple entrypoints, command directories, skill directories, or subagent directories claim authority for the same workflow.
- Entrypoints import duplicate architecture, quality-gate, or workflow instructions.
- Same agentic purpose appears in multiple locations with different commands, ownership, or approval rules.

Severity:

- `critical` if duplicate agentic sources contain incompatible rules.
- `important` if duplicate agentic sources are redundant but consistent.

Impact:

- Later planting may create or preserve the wrong source of truth.

Action:

- `ask user` which source is authoritative.
- `halt` if no safe merge path exists.

## Competing SDLC Ownership

Pattern:

- Existing agents, skills, commands, prompts, Copilot instructions, or assistant entrypoints claim responsibility for requirements intake, planning, implementation gates, review gates, knowledge guides, or run journals that overlap agentic-sdlc.
- Another setup directs agents to ignore `.agentic/guides/`, bypass agentic-sdlc quality gates, or treat a different generated guide tree as the source of truth.
- A custom command wraps agentic-sdlc but changes approval, verification, or write-safety semantics.

Severity:

- `critical` if the competing setup bypasses approvals, writes, destructive-command safety, review gates, or quality gates.
- `important` if the competing setup is redundant but mostly compatible.

Impact:

- Later planting may preserve conflicting operating systems and leave agents with two competing workflows.

Action:

- `ask user` which workflow owns SDLC responsibilities.
- `halt` when competing ownership also changes safety, approval, or destructive behavior.

## Competing Assistant Commands

Pattern:

- `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` specify different test, lint, branch, commit, or approval commands for the same task.
- Tool-specific command files conflict with root entrypoint instructions.
- Host-specific slash commands are documented for hosts that do not support them.

Severity:

- `critical` if commands have destructive or release side effects.
- `important` if commands only affect validation consistency.

Impact:

- Agents may run the wrong checks or report false confidence.

Action:

- `ask user` for the authoritative command.
- `merge` only after evidence from manifests or CI supports the chosen command.

## Managed Region Drift

Pattern:

- Managed-region start and end markers do not match.
- Managed regions reference files that no longer exist.
- Human-authored rules inside managed regions conflict with generated content outside them.

Severity:

- `critical` if markers are malformed and an automated merge could damage human text.
- `important` if references are stale but markers are intact.

Impact:

- Later entrypoint updates may be unsafe or confusing.

Action:

- `halt` on malformed markers.
- `ask user` or `replace` stale generated content through a later gated diff.

## Source-of-Truth Conflict

Pattern:

- README, entrypoint, CI, and manifests identify different setup or test flows.
- Project settings name different default branches or ticket prefixes.
- Docs and commit history disagree about branch or commit conventions.

Severity:

- `important` by default.
- `critical` when release, deployment, security, or data-migration instructions conflict.

Impact:

- Later generated guides may institutionalize an incorrect workflow.

Action:

- `ask user` unless manifest or CI evidence clearly resolves the conflict.
