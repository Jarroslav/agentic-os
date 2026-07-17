# Audit rubric: grading a repository's knowledge and assistant setup

The scoring layer for a repository knowledge audit. When you write a finding, this file gives you two
things and nothing else: the one label you attach to it, and the downstream disposition that label
triggers at the foundation (knowledge-planting) stage. Discovery, audit procedure, and report layout
live in the companion references — not here.

What you grade (assessed, never owned by the audit): README, docs, manifests, CI config, assistant
entrypoint files, generated guide trees, and agentic assets (commands, skills, subagents, hooks,
settings, prompts).

> The audit is R0 — read everything, write nothing to the repo. Findings land in run artifacts (R1).
> No label here authorizes a repo write; that is the foundation stage's job, behind its own approvals.

## Core rule

Attach exactly one label per finding, from the closed five-value set below, and cite evidence for it.
A label without a citation is invalid — drop the finding or go find the evidence first.

> Grounding: the foundation stage acts on your labels without re-reading the repo. An uncited label
> smuggles a guess into generated guidance.

## The scale

Rating label enum: `strong` | `partial` | `weak` | `missing` | `conflicting`

| Label | Means | Disposition |
|---|---|---|
| `strong` | Complete, specific, current, self-consistent; compatible with the live repo and the assistant surfaces detected | Keep as authoritative; optionally fold into generated guidance |
| `partial` | Real substance, but gaps in scope, commands, ownership, or freshness | Blend with generated guidance — only after the user confirms |
| `weak` | Thin, generic, outdated, or too vague for an agent to rely on | Regenerate or supplement, unless the user reveals context that upgrades it |
| `missing` | No evidence at all for the assessed area | Create new guidance, through the normal approval flow |
| `conflicting` | Two or more sources disagree, or together imply an unsafe workflow | Escalate to the user or stop — never let planting bake the contradiction in |

> `strong` is a high bar. Fail any one of complete / specific / current / consistent / compatible and
> the finding is at best `partial`. Good prose alone earns nothing.

## Decision rules

- One label per finding. No hedged double-labels, no unlabeled findings.
- `conflicting` is the only label that forces a hard stop or user escalation before planting proceeds.
- `partial` content merges only after explicit user confirmation.
- `missing` content is generated through the standard foundation approval path — never silently.
- `weak` content is replaced or supplemented by default; user-supplied hidden context is the only
  thing that overrides this.

## Evaluation lenses

Eight signals shape the write-up. They are lenses for judging evidence, not an outline — do not promote
any of them into a report or document heading unless it is literally the repo topic under analysis.

1. **Coverage breadth** — does knowledge span architecture, setup, commands, tests, gates, release,
   and contribution, or cluster on one topic?
2. **Repo fidelity** — do names, paths, branches, and tools still match what the live repo contains?
3. **Concreteness** — real commands, real file paths, worked examples; aspirational prose scores nothing.
4. **Cross-source agreement** — do README, docs, manifests, CI, assistant entrypoints, generated
   guides, and agentic assets tell one consistent story?
5. **Entrypoint fitness** — are assistant entrypoint files short, appropriate to their host, and linked
   to docs that still exist?
6. **Asset hygiene** — are commands, skills, subagents, hooks, settings, and prompts discoverable,
   correctly scoped, and current?
7. **Safety posture** — do setup files preserve approval, write-safety, branch-safety, and verification
   guarantees, or quietly erode them?
8. **Decidability** — is the cited evidence concrete enough for the foundation stage to choose an action
   without re-auditing?

## Recording findings

Cite evidence with a `path:line` locator. List every locator when a finding rests on more than one
source; a `conflicting` finding must cite each disagreeing source. For `missing`, absence still needs
an anchor: cite the artifact that creates the expectation — for example, a manifest that declares a
test script no document explains. A bare "not found" is not evidence.

When a table helps, use these four columns, in this order:

| Finding | Label | Evidence | Foundation action |
|---|---|---|---|
| Build and run commands documented and match the manifest | `strong` | `README.md:42, package.json:18` | `preserve` |
| Documented test command predates the runner switch | `weak` | `README.md:57` | `replace` |
| Manifest declares a lint script that no doc explains | `missing` | `package.json:21` | `incorporate` |
| Branch policy in CI contradicts the contribution guide | `conflicting` | `.github/workflows/ci.yml:18, CONTRIBUTING.md:9` | `halt` |

Cell value patterns: the label cell holds one of `strong|partial|weak|missing|conflicting`; the action
cell holds one of `preserve|incorporate|replace|merge|skip|ask user|halt`.

## Downstream contract

The foundation stage consumes each finding's action from a closed seven-item vocabulary.

Foundation action enum: `preserve` | `incorporate` | `replace` | `merge` | `skip` | `ask user` | `halt`

| Label | Typical actions | Gate before acting |
|---|---|---|
| `strong` | `preserve`, `incorporate` | none |
| `partial` | `merge` | user confirmation |
| `weak` | `replace`, `incorporate` (as supplement) | none by default; user context can redirect |
| `missing` | `incorporate` (generate fresh) | standard foundation approval |
| `conflicting` | `ask user`, `halt` | mandatory — pre-planting stop |

`skip` is available for any label when the user rules the area out of scope. Choose the action per
finding: the table shows defaults, not a lookup that replaces judgment.

## Non-goals

- Does not define artifact discovery, audit procedure, or report structure — see the auditor's other
  references.
- Does not define planting or generation mechanics, nor approval workflows — it only names the
  conditions that trigger them.
- Not a per-repo checklist. The signals are deliberately generic and must never dictate a report's
  headings.
