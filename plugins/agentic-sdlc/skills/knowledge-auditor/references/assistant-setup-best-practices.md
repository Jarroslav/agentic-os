# Assistant Setup Best Practices

Use this reference to assess assistant entrypoints and tool-specific setup. Keep it vendor-neutral unless a surface is explicitly host-specific.

## Entrypoints

- Root entrypoints such as `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md`, plus GitHub Copilot entrypoints such as `.github/copilot-instructions.md`, should be concise and clearly scoped.
- Entrypoints should identify the authoritative docs or references rather than duplicating long procedures.
- Host-specific instructions should be labeled by host and should not be presented as universal.
- Approval, write-safety, branch-safety, and verification expectations should be explicit.
- Managed regions should have intact start/end markers and should not mix generated text with human-authored policy.

## Tool-Specific Directories

- `.claude/`, `.codex/`, `.agents/`, `.gemini/`, `.copilot/`, `.cursor/`, `.github/`, and similar directories should contain assets that are referenced or clearly discoverable.
- Commands should map to real repository workflows and avoid stale slash-command assumptions when the host does not support them.
- Hooks/settings should be minimal, explain their purpose, and avoid hidden writes or destructive defaults.
- Memory/profile files should not override repository standards without evidence.
- Agentic assets should not compete with agentic-sdlc by claiming a different source of truth for requirements, implementation gates, review gates, or knowledge guides unless the user has explicitly chosen that setup.

## Authority Assessment

Rate which surface is authoritative for:

- project overview
- quality gates
- branch and commit policy
- approval and review expectations
- agent-specific commands
- skill/subagent usage

When authority is unclear, recommend `ask user` before planting.
