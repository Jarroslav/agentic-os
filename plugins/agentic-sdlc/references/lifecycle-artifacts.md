# Lifecycle Artifacts

agentic-sdlc passes durable file references between phases instead of relying on
chat history. Full runs write artifacts under `docs/superpowers/runs/<run-id>/`.

## Full-Run Artifacts

| Artifact | Producer | Consumer |
|---|---|---|
| `meta.json` | `sdlc-pipeline` | `sdlc-status`, resume logic |
| `events.jsonl` | `sdlc-pipeline`, `decision-router`, `sdlc-status`, lifecycle helpers | `sdlc-status`, resume logic, audit, repair |
| `decisions.jsonl` | `decision-router` | `sdlc-status`, audit, report builder |
| `work-item.md` | `sdlc-pipeline` | requirements, planning, handoff, `mr-creator` |
| `work-item-events.jsonl` | `sdlc-pipeline`, `product-owner`, `requirements-intake`, `mr-creator` | audit, status, external adapter reconciliation |
| `requirements.md` | `requirements-intake` | complexity scoring, spec, plan, review |
| `complexity.json` | `complexity-scoring` or heuristic path | `sdlc-pipeline` routing |
| `design.md` | `superpowers:brainstorming` | planning, review, drift checks |
| `plan.md` | `superpowers:writing-plans` | implementation, evidence validation |
| `evidence/<task-id>.json` | implementation tasks | evidence validation, review bundle |
| `review-bundle.json` | `sdlc-pipeline` | `code-reviewer` |
| `qa-report.md` | `qa-gates` | feature verification, report builder |
| `qa-checklist.md` | `qa-planner --checklist` | Phase 6 TDD subagents, Phase 7 review bundle |
| `qa-test-review.md` | `qa-planner --review-tests` | `decision-router` gate, fix-up tasks |
| `gate-plan.json` | `qa-gates` | QA reruns, feature verification |
| `evidence/verification/*.json` | `feature-verification` | `feature.verification` gate |
| `sdlc-report.html` | `report-builder` | humans, audit trail |

## Local Work Item Contract

External tickets are optional. Every approved story or SDLC run MUST have a
repository-local work item so planning, implementation, and MR creation have a
stable source of truth even when no adapter is configured.

Canonical project paths:

| Artifact | Path | Notes |
|---|---|---|
| Canonical work item | `docs/superpowers/work-items/<id-or-slug>.md` | Long-lived Markdown record for the story, task, or unresolved external ticket. `<id-or-slug>` is the external key when known, otherwise a stable kebab-case slug from the title or goal. |
| Canonical event ledger | `docs/superpowers/work-items/work-item-events.jsonl` | Append-only history for all local work items. Never rewrite or truncate. |
| Run-local mirror | `docs/superpowers/runs/<run_id>/work-item.md` | Copy or summary mirror of the canonical work item used by the run. Recreated on resume from the canonical item when needed. |
| Run-local event ledger | `docs/superpowers/runs/<run_id>/work-item-events.jsonl` | Append-only events relevant to the current run. |

The canonical Markdown file MUST use these sections and fields:

```markdown
# <Work Item Title>

**Status**: Draft | Approved | In progress | Ready for review | Done | Blocked
**Assignee**: <name or Unassigned>
**Reporter**: <name, requester, or Unknown>
**Branch**: <branch name or Not assigned>
**External Ticket**: <ticket key/url, ticket-unresolved:<id>, or Not configured>
**Source Story/Task**: <docs/stories/... path, free-form, greenfield, or other source>

## Acceptance Criteria

- <criterion or "(none provided)">

## Linked Artifacts

- <artifact path or URL with short label>

## History

- <ISO timestamp> - <event summary>
```

`work-item-events.jsonl` lines use the same base shape as the run event ledger
with `phase: null` when the event is not tied to a phase. Required work-item
event names:

| Event | Meaning |
|---|---|
| `work_item.created` | Local work item file was created. |
| `work_item.assigned` | Assignee, reporter, or branch ownership changed. |
| `work_item.transitioned` | Status changed. |
| `work_item.linked_artifact` | Story, requirements, run artifact, branch, commit, MR/PR, or report was linked. |
| `work_item.adapter_receipt` | External adapter returned a key, URL, or synchronization receipt. |
| `work_item.adapter_warning` | External adapter was unavailable, not configured, or returned a non-blocking warning. |

Skills that write local work items MUST append a human-readable row under
`## History` and a matching JSONL event. If writing the JSONL event fails, keep
the Markdown history as the durable fallback and report the warning.

## Run Event Ledger Contract

`events.jsonl` is the append-only run history. `meta.json` is a mutable snapshot and may be repaired from `events.jsonl`; the event ledger itself is never rewritten or truncated.

Each line is one JSON object:

```json
{
  "schema": 1,
  "ts": "<ISO>",
  "event": "phase.started | phase.completed | phase.failed | phase.interrupted | artifact.written | decision.recorded | work_item.created | work_item.assigned | work_item.transitioned | work_item.linked_artifact | work_item.adapter_receipt | work_item.adapter_warning | status.repaired | <semantic-event>",
  "run_id": "<id>",
  "phase": 0,
  "actor": "sdlc-pipeline | decision-router | sdlc-status | <skill-or-subagent>",
  "summary": "<single-line human summary>",
  "artifacts": ["<run-relative path>", "..."],
  "data": {}
}
```

Required fields:

| Field | Meaning |
|---|---|
| `schema` | Integer event schema version, currently `1`. |
| `ts` | ISO timestamp for when the event was appended. |
| `event` | Stable event name. Required lifecycle events include `phase.started`, `phase.completed`, `phase.failed`, `phase.interrupted`, `artifact.written`, `decision.recorded`, and the local work-item events listed above. |
| `run_id` | Current SDLC run id. |
| `phase` | Numeric phase id, or `null` for run-level events. |
| `actor` | Skill, subagent, or host component that appended the event. |
| `summary` | Concise human-readable summary. |
| `artifacts` | Run-relative artifact paths written or consumed by the event. |
| `data` | Event-specific structured payload; use `{}` when empty. |

Phase lifecycle is reconstructed by pairing `phase.started` with a later terminal event for the same phase: `phase.completed`, `phase.failed`, or `phase.interrupted`. A phase with `phase.started` and no later terminal event is resumable from that phase. Decision gates append both a `decisions.jsonl` row and a matching `decision.recorded` event in `events.jsonl`.

## Project Knowledge Artifacts

| Artifact | Producer                                      | Consumer |
|---|-----------------------------------------------|---|
| `.agentic/guides/project.md` | `knowledge-foundation`                        | ticket adapter lookup, product-owner, pipeline |
| `.agentic/guides/standards/git-workflow.md` | `knowledge-foundation`                        | `mr-creator`, code-reviewer |
| `.agentic/guides/quality-gates.md` | `knowledge-foundation`                        | `qa-gates` |
| `.agentic/guides/testing/qa-strategy.md` | `qa-foundation`                               | `qa-planner` (all modes), TDD subagents, `code-reviewer` |
| `.agentic/guides/testing/qa-health.md` | `qa-foundation`, `qa-planner --update`        | `qa-planner --checklist` |
| `.agentic/guides/<category>/*.md` | `knowledge-foundation`, `knowledge-harvester` | agents, review, project guidance |
| `.agentic/runs/<branch>.json` | lifecycle skills                              | run journal and handoff trace |

## Artifact Reference Contract

Gate calls pass summaries as `ArtifactRefs`:

```json
{
  "kind": "spec | plan | diff | qa-report | evidence | story",
  "path": "<absolute or repository-relative path>",
  "summary": "<short bounded summary>",
  "signature": "<sha-256>"
}
```

Stand-ins may read `path` directly when the summary is insufficient.
