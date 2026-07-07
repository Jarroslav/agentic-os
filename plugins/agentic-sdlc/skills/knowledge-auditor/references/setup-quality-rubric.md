# Setup Quality Rubric

Use this rubric to label each concrete documentation or setup finding as `strong`, `partial`, `weak`, `missing`, or `conflicting`. Always cite evidence for the label.

## Ratings

| Label | Meaning | Foundation posture |
|---|---|---|
| `strong` | Complete, specific, current, internally consistent, and compatible with the detected repository and assistant surfaces. | Preserve as source of truth unless foundation should incorporate it into factory-owned guidance. |
| `partial` | Useful evidence exists, but important scope, commands, ownership, or freshness details are incomplete. | Merge with generated guidance after user confirmation. |
| `weak` | Sparse, generic, stale, or too ambiguous to guide agents reliably. | Replace or supplement unless the user identifies hidden context. |
| `missing` | No relevant evidence found for the area being assessed. | Generate new guidance only after normal foundation approval. |
| `conflicting` | Two or more sources give incompatible instructions or unsafe workflow expectations. | Ask the user or halt before any planting that would encode the conflict. |

## Analysis Signals

Use these signals while writing concrete findings. Do not turn them into headings unless they are the actual repo topic being analyzed.

- Coverage: Does the repo document the actual areas foundation needs, such as architecture, setup, commands, tests, quality gates, release, and contribution flow?
- Currentness: Do paths, package names, branches, guide trees, and tool names match the current repo?
- Specificity: Does the guidance name real commands, files, conventions, and examples?
- Consistency: Do README, docs, manifests, CI, assistant entrypoints, generated guides, and agentic assets agree?
- Assistant compatibility: Are entrypoints concise, host-appropriate, and wired to current docs?
- Agentic setup quality: Are commands, skills, subagents, hooks, settings, and prompts discoverable, bounded, and current?
- Safety: Do setup files preserve approval, write-safety, branch-safety, and verification expectations?
- Foundation readiness: Can foundation preserve, merge, replace, skip, ask the user, or halt based on concrete evidence?

## Concrete Finding Table

Use this shape in analysis sections when useful:

| Finding | Label | Evidence | Foundation action |
|---|---|---|---|
| `<concrete setup or documentation finding>` | `strong|partial|weak|missing|conflicting` | `path:line` | `preserve|incorporate|replace|merge|skip|ask user|halt` |
