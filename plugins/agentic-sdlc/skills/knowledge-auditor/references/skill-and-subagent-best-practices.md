# Skill and Subagent Best Practices

Use this reference to assess Claude, Codex, Gemini, GitHub Copilot skills, subagents, commands, prompts, and reusable agent instructions. The criteria should evolve as the repository's agent platform evolves.

## Skill Quality

- Frontmatter has a clear `name` and a discovery-oriented `description` with concrete triggers.
- `SKILL.md` is concise and uses progressive disclosure into reference files when detail grows.
- References are one level deep from `SKILL.md` so agents can find the right material.
- The skill avoids stale time-sensitive instructions and generic explanations the model already knows.
- Instructions match the needed degree of freedom: strict for fragile operations, flexible for judgment-heavy work.
- Evals, pressure scenarios, or representative prompts exist for important behavior.

## Subagent Quality

- Each subagent has one clear responsibility and bounded write/read scope.
- Prompts say what context to inspect, what output to produce, and what not to change.
- Subagents are not used as hidden approval bypasses for HITL decisions.
- Verification expectations are explicit and tied to repository commands.
- Parallel subagents have disjoint ownership or clear coordination rules.

## Anti-Patterns

- Vague names like `helper`, `misc`, or `general`.
- Long entrypoint files that duplicate every reference.
- Skills that assume a specific repository state without checking evidence.
- Subagents that can write anywhere or revert unrelated changes.
- Conflicting instructions between skills, subagents, root entrypoints, and repository docs.
