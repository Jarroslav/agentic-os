# Code Review Orchestrator

Resolves the SDLC code-review gate. It gathers the run's diff and project context, runs three review lenses as parallel subagents, adjudicates coding standards and security against the project's guides, triages every finding into one deduplicated list, and persists a single approve / request-changes verdict as a file that `decision-router` reads back to drive the gate.

> Supersedes the earlier single-model holistic pass. The multi-lens approach catches more real defects; triage keeps the verdict low-noise.

## Use It For

- Resolving the `code-review.final` gate — a full multi-lens review of the run's diff.
- Resolving the `code-review.check` gate — a targeted re-check of prior findings after a fix-up, never a full re-review.
- Producing the canonical verdict JSON that `decision-router` records and escalates on.

The review is assembled from independent perspectives, each run as an isolated parallel subagent outside the orchestrator's own context:

| Lens | What it does | When |
|------|--------------|------|
| **Blind** | Seeded with the diff text alone, never a repo path; instructed to read nothing else, hunts adversarially with no project context (isolation is prompt-enforced, not a tool sandbox). | Always |
| **Edge-case** | Applies the edge-case lens method (see `references/review-lenses.md`); walks every reachable branch/boundary, reports missing handling. | Always |
| **Acceptance** | Applies the acceptance lens method (see `references/review-lenses.md`); audits the diff against story/spec criteria. | Skipped or run at lower confidence when no spec/story is present |
| **Standards & security** | Orchestrator itself (not a subagent) checks commit format, code-quality, and security against `.agentic/guides/**`. | Only when the guides directory is present |

Triage then normalizes, dedupes, and classifies each finding into one of `decision_needed`, `patch`, `defer`, `dismiss` — dropping `dismiss` — before the verdict is persisted.

## How To Ask

You do not call this skill directly; `decision-router` is its sole invoker, in **both** autonomous and HITL modes.

- **Autonomous** — the stored verdict drives the gate directly.
- **HITL** — the router runs the skill first to perform and store the review, then asks the user to decide, informed by that report.

The verdict file is the hand-off. The skill persists JSON and does **not** print the verdict; the router reads it back:

| Round | Output file (written to `<run_dir>`) |
|-------|--------------------------------------|
| Final | `code-review-final.json` |
| Check | `code-review-check.json` |

## What It Needs

Required inputs:

| Input | Purpose |
|-------|---------|
| `gate_id` | `code-review.final` or `code-review.check` |
| `artifacts` | ArtifactRefs for the review bundle / diff, story, spec, plan, project guides, and optional QA report |
| `original_task` | The task the change was meant to satisfy |
| `memory_brief` | Carried run/role context |

- Read access to the repo and to `.agentic/guides/**` for the standards/security adjudication. No external services or credentials.
- `references/review-lenses.md` is the canonical source of the three lens methods; the orchestrator inlines them into self-contained subagent prompts, so nothing needs to be loaded at runtime — but keep the inlined prompts and `review-lenses.md` in sync when a lens changes.

Reference docs (relative to this skill):

- `references/verdict-schema.md` — the exact output contract.
- `references/triage-and-verdict.md` — the triage rules and buckets.
- `references/review-subagent-prompts.md` — the three parallel lens dispatches.
