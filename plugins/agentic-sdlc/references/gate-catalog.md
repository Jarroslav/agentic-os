# Gate Catalog

This catalog names the judgment gates used by agentic-sdlc and the expected
resolver behavior. Deterministic checks run before model-heavy review whenever
possible.

| Gate | Phase | Primary Resolver | Artifact Inputs | Blocking Conditions |
|---|---:|---|---|---|
| `requirements.ambiguous` | 1 | `decision-router` | `requirements.md` | unanswered required scope or acceptance questions |
| `spec.clarification` | 4 | `decision-router` | brainstorming question context | unclear product or technical decision |
| `spec.approved` | 4 | human or `tech-lead-reviewer` | `requirements.md`, `design.md` | rejected design, missing required constraints |
| `plan.approved` | 5 | human or `tech-lead-reviewer` | `design.md`, `plan.md` | missing test-first task lines or unsafe plan |
| `qa-checklist.approved` | 6 | human (HITL) or `decision-router` (autonomous) | `qa-checklist.md` | unresolved high-risk gaps with no test scenario |
| `qa-tests.approved` | 8 | human (HITL) or `decision-router` (autonomous) | `qa-test-review.md` | missing high-risk scenarios or high-severity quality findings |
| `code-review.final` | 9 | `code-reviewer` | review bundle, diff, evidence summaries | critical or major review findings |
| `code-review.check` | 9 | `code-reviewer` | original findings, fix-up diff | unresolved finding or new high-risk regression |
| `qa.drift` | 10 | human or `tech-lead-reviewer` | `qa-report.md`, `design.md`, diff summary | implementation drift from approved artifacts |
| `feature.verification` | 10 | deterministic evidence, then human or `tech-lead-reviewer` | browser/tool evidence | missing or blocking user-visible proof |

## Rules

- HITL mode routes unresolved judgment to the user.
- Autonomous mode routes unresolved judgment through `decision-router`.
- Evidence shape failures are deterministic blockers.
- User-visible changes cannot reach handoff without feature-verification
  evidence or an explicit resolver approval.
- MR/PR creation is not a gate and is never invoked automatically.
