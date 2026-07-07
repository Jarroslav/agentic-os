# Documentation Standards

Use this reference to assess repository documentation before knowledge planting. Treat it as an evolving checklist, not a fixed product template.

## Strong Documentation Signals

- `README.md` explains purpose, setup, common workflows, and where deeper docs live.
- Development docs name exact install, test, lint, type-check, build, review, and release commands.
- Architecture docs describe module boundaries, important data flows, external systems, and tradeoffs.
- ADRs or decision logs capture non-obvious decisions and current constraints.
- Docs cite active paths, package names, commands, CI jobs, and ownership signals that exist in the repository.
- Operational docs explain failure modes, migrations, secrets/configuration, deployment, and rollback when applicable.

## Weak Documentation Signals

- Docs are generic enough to fit any repository.
- Commands are missing, stale, or differ from manifests and CI.
- Architecture claims do not match current source layout.
- Setup instructions depend on hidden context or unlisted credentials.
- Important standards live only in chat history or tribal knowledge.

## Audit Questions

- What evidence proves the documented commands still work?
- Which docs are source material for future planting, and which are stale?
- Are there gaps that a foundation can infer from repository evidence, or must the user answer first?
- Do docs identify standards clearly enough for future agents to follow without guessing?
