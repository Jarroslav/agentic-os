# Planting Recommendations

Map audit findings to one of these actions. The auditor reports recommendations only; it does not implement them.

## Actions

| Action | Use when | Later foundation posture |
|---|---|---|
| `preserve` | Existing documentation is strong, current, compatible, and should remain the source of truth that agents read directly. | Keep it authoritative; avoid unnecessary rewrites. |
| `incorporate` | Existing documentation is useful, but foundation should own the future guidance. | Use it as source material, map its knowledge into factory-owned guidance, and decide separately whether the original documentation remains authoritative, becomes legacy, or stays tool-specific. |
| `replace` | Existing guidance is stale, generic, generated incorrectly, or contradicted by stronger evidence. | Propose replacement in a later gated diff or guide update. |
| `merge` | Existing content and foundation output already share the same authority surface or compatible managed-region/guide target. | Combine existing guidance with generated guide structure after approval. |
| `skip` | Area is absent, irrelevant, or out of scope for knowledge planting. | Do not generate or update that area unless the user asks. |
| `ask user` | Evidence is ambiguous, authority is unclear, or a choice affects future writes. | Stop before writing and ask a concrete question. |
| `halt` | Unsafe, destructive, approval-bypassing, or malformed managed-region conditions exist. | Do not plant until the blocker is resolved. |

## Finding-to-Action Mapping

| Finding | Recommended action | Rationale |
|---|---|---|
| Strong README and architecture docs that remain authoritative | `preserve` | They are the source of truth agents should continue to use directly. |
| Strong assistant entrypoint outside managed regions | `preserve` | Human-authored policy should remain intact. |
| Rich existing documentation that should feed factory guidance | `incorporate` | Foundation should ingest the knowledge into the approved factory-owned destination, not update the source docs in place as the main action. |
| Existing skills, commands, or subagents with minor gaps | `incorporate` or `ask user` | Preserve useful agentic knowledge as source material, but do not silently make host-specific assets factory-owned. |
| Thin docs but clear manifests and CI | `incorporate` | Repository evidence can support generated guidance in the factory structure. |
| Generic docs with no project detail | `replace` | Generic guidance does not help agents. |
| Stale generated managed-region content | `replace` | Generated content can be refreshed later through a gated diff. |
| No assistant entrypoint | `skip` for audit, then `ask user` in foundation | Auditor should not choose or create the target. |
| Multiple assistant entrypoints mostly agree | `ask user` | User should identify which surfaces are active. |
| Duplicate assistant or agentic sources claim authority | `ask user` or `halt` | Source of truth must be resolved first. |
| Existing agents, skills, commands, prompts, or Copilot instructions compete with agentic-sdlc ownership | `ask user` or `halt` | The user must choose the authoritative workflow before planting. |
| Conflicting test commands across docs and CI | `ask user` | Wrong quality gates create false confidence. |
| Malformed managed-region markers | `halt` | Automated entrypoint merge could damage content. |
| Approval bypass or destructive defaults | `halt` | Unsafe behavior must not be encoded. |

## Recommendation Format

Use this table shape inside `## Foundation Readiness And Next Steps`. Do not add abstract grading sections to the audit report.

| Area | Finding | Action | Later foundation implication |
|---|---|---|---|
| Documentation | `<finding>` | `preserve|incorporate|replace|merge|skip|ask user|halt` | `<specific implication>` |

Recommendations should be concrete:

- Good: "Incorporate the existing architecture and testing docs into factory-owned guides; ask whether the original docs remain authoritative or become legacy references."
- Good: "Ask user whether `AGENTS.md` or `CLAUDE.md` is authoritative before wiring guide imports."
- Bad: "Update the existing docs in place" when the intended outcome is factory-owned guidance.
- Bad: "Improve docs."

Recommendations must not perform writes or imply that this skill already changed files.

## In-Place Update Guardrail

Do not recommend updating useful existing documentation in place when foundation is expected to own the resulting guidance. Existing documentation has two valid roles: it remains the source of truth (`preserve`), or its knowledge is incorporated into factory-owned guidance (`incorporate`). In-place `merge` or `update` is valid only when the existing content is already the approved authority surface or compatible managed target.
