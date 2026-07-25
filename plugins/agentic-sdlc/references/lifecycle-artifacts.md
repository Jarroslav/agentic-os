# Run lifecycle artifacts: what lands under the run dir and who writes it

Every pipeline run leaves a trail. This reference names each artifact, the exact
producer that owns it, where it lands, and its blast radius. Use it to answer two
questions: *who is allowed to write this file* and *who is allowed to read it later*.

> Artifacts are the contract between phases. A downstream step never re-derives
> what an upstream step already wrote — it reads the artifact. If a file is absent,
> the phase that needed it stalls; it does not guess.

## Two roots, two jobs

Run state splits across two trees. Keep the split clean — never mix machine ledgers
into the human-readable tree, and never hand-edit the machine tree.

| Root | Contents | Audience | Default blast radius |
|------|----------|----------|----------------------|
| `.agentic/` | Ledgers, evidence, cached routing, adapters, durable memory | The orchestrator and its subagents | R1 (run-artifact writes) |
| `docs/superpowers/` | The human-readable planning trio (spec / plan / design) | People, reviewers, git history | R2 (repo file writes) |

The `.agentic/` tree is working state for the run. The `docs/superpowers/` tree is
committed product — it survives the run and belongs in the merge request.

## Anatomy of a run directory

A heavy-pipeline run claims a run id and writes under it:

```
.agentic/
  runs/<run-id>/
    decisions.jsonl              # judgment-gate verdicts (append-only)
    events.jsonl                 # phase transitions + side effects (append-only)
    task-evidence/               # one folder per implementation task
      <task-id>/                 #   commands run, output, diffs, gate results
    verification-evidence.json   # feature-verification output (per feature)
  guides/                        # adapters: ticket + MR/PR backends, standards
  memory/<role>/                 # role-memory: durable, cross-run
docs/superpowers/
  <feature-slug>/
    spec.md
    plan.md
    design.md
```

The lightweight orchestrator (XS/S/M tasks) writes a slimmer footprint — live
`spec.md` and `plan.md` under `docs/superpowers/tasks/<slug>/`, no per-task
evidence folders, no complexity breakdown. It reconciles those two files through
`mode: sync` after any post-completion change so the planning trio never drifts
from the code that shipped.

## Artifact catalog

| Artifact | Written by | Blast radius | Written when | Read by |
|----------|-----------|--------------|--------------|---------|
| `spec.md` | superpowers:brainstorming (heading shape) → orchestrator | R2 | After requirements intake, before `spec.approved` | Planner, reviewers, gate summaries |
| `plan.md` | superpowers:writing-plans (heading shape) → orchestrator | R2 | After `spec.approved`, before `plan.approved` | Implementer, `qa.drift` check |
| `design.md` | superpowers planning skill (heading shape) | R2 | When a design pass is warranted | Implementer, reviewers |
| `decisions.jsonl` | decision-router | R1 | Every judgment gate | Auditors, resume logic |
| `events.jsonl` | orchestrator + any R3 actor | R1 | Every phase transition and side effect | Auditors, `sdlc-status` |
| `task-evidence/<task-id>/` | orchestrator during implementation | R1 | Per task, as work lands | code-review, `code-review.final` |
| `verification-evidence.json` | feature-verification | R1 | After QA gates, per user-visible feature | `code-review.final`, reviewers |

> `spec.md`, `plan.md`, `decisions.jsonl`, `events.jsonl`,
> `verification-evidence.json`, and the `task-evidence` folder name are integration
> contracts. Other producers and consumers match on these exact names — do not
> rename or relocate them.

## The planning trio owns its own headings

`spec.md`, `plan.md`, and `design.md` are authored through superpowers skills, and
**their heading shapes come from those skills, not from this document.**
`superpowers:brainstorming` fixes what a spec looks like; `superpowers:writing-plans`
fixes the plan layout; the design pass fixes `design.md`. When you need to slice a
section out of one of these files, take the heading text from the skill that wrote
it, not from a copy pasted here — this reference does not restate their structure
and will go stale if it tries.

## Append-only ledgers

Two ledgers under the run dir are the audit spine. Both are append-only JSONL —
one object per line, never rewritten.

- `decisions.jsonl` — the decision-router writes one record per judgment gate
  (`spec.approved`, `plan.approved`, `qa.drift`, `code-review.final`,
  `requirements.ambiguous`, …). Each record carries the gate id, the structured
  verdict, and the prior context that fed the decision. In `hitl` mode the verdict
  is the user's answer; in autonomous mode it is a deterministic check, a fast-path
  approval, or a stand-in subagent verdict — the record notes which.
- `events.jsonl` — the orchestrator writes one record per phase transition. Any
  actor performing an R3 (external side-effect) step also appends here, so the
  ledger doubles as the side-effect log. R3 steps are always gated, so an R3 event
  is always preceded by its approving `decisions.jsonl` record.

Resume and status tooling replays these two files to rebuild run state. Keep them
grounded — a ledger records what happened, never a projection of what should have.

## Evidence artifacts

Evidence is captured while work is fresh, not reconstructed at review time.

- `task-evidence/<task-id>/` — for each implementation task the orchestrator drops
  the commands it ran, their output, the diff, and gate results. Deferred model-heavy
  code review reads these folders at the end rather than re-running the work.
- `verification-evidence.json` — for changes touching UI or any externally visible
  surface, feature-verification reuses existing e2e coverage when present, generates
  focused browser checks when coverage is missing, and records screenshots plus
  console and network errors here, one file per feature.

## How a gate consumes artifacts

Gates do not slurp whole files. A producer hands the gate an `ArtifactRefs` entry
naming an artifact (`kind` ∈ `spec | plan | diff | qa-report | evidence`) and,
optionally, the exact sections to pull:

```
sections: ["## <heading>", ...]
```

Slicing keeps context lean under the gate budget: **2 KB** summary cap per artifact,
**~6 KB** total per gate. If a named heading is absent from the file, the consumer
falls back to a whole-file read and emits a warning — the gate still runs, but at
full token cost, which is the signal that a heading drifted.

## Durable vs per-run

Not everything under `.agentic/` is scoped to a single run.

| Path | Lifetime | Owner |
|------|----------|-------|
| `.agentic/runs/<run-id>/` | One run | Orchestrator + decision-router |
| `.agentic/memory/<role>/` | Across runs | role-memory (durable facts, prefs, episodic log) |
| `.agentic/guides/` | Across runs | repo-guides (planted) / repo-audit-guides (audited) |

Adapters live in `.agentic/guides/`. No ticket or MR/PR backend is hardcoded — the
mr-creator and requirements intake read their backend from the guides tree, so the
same run artifacts work against Jira, Azure DevOps, GitLab, GitHub, or a custom CLI
without touching the pipeline. `repo-guides` plants that tree; `repo-audit-guides`
audits a repo's readiness before planting; `role-memory` keeps per-role state that
outlives any one run.

## Writer discipline

- Match the exact filenames above; downstream producers and gates key on them.
- `.agentic/` writes are R1; `docs/superpowers/` writes are R2; anything reaching an
  external system is R3 and only after its gate approves.
- Ledgers are append-only. To correct a record, append a new one — never edit a line.
- Ground every artifact in its inputs. If an upstream artifact is missing, stall the
  phase and surface it; do not fabricate the content a prior phase failed to write.
