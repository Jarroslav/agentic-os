# qa-case-generator

Turn a work-item ticket into a planned, written, reviewed, and optionally synced suite of functional test cases. Standalone — invoke it directly against an existing ticket; it is not wired into the `sdlc-autonomous` or `sdlc-standard` pipelines.

## Use It For

- Deriving **functional** tests from a ticket: manual UI scenarios plus API specs (endpoint + request/response templates with placeholders).
- Grouping the result by priority — **P1/P2/P3** — and grounding every case in the ticket plus your project QA docs.
- Optionally pushing the suite into a configured test-management backend (TestRail, Zephyr, ADO Test Plans) — only on your explicit approval.

Not for:

| Concern | Owner |
|---|---|
| Unit / integration tests | TDD workflow |
| Coverage analysis | `code-review` skill |
| Test execution + result analysis | test-runner tooling |
| Automation-framework scaffolding | — (out of scope) |
| Code generation / reading the host codebase | — (never; inputs are the ticket + QA docs only) |

> The skill never opens your source tree. It reasons from the ticket system and QA guidance, so it stays safe to run against any repo.

Run artifacts land under a per-run directory:

```
docs/superpowers/qa-tasks/<date>-<slug>/manual/
  test_cases.md       # main deliverable, grouped P1/P2/P3
  meta.json           # test counts, sync status
  ticket-analysis.md  # context + risk assessment
  events.jsonl        # audit trail
```

## How To Ask

Any of these trigger the skill:

- `qa-case-generator PROJ-123`
- `/qa-case-generator PROJ-123`
- Natural language: "generate test cases for PROJ-123"

It then runs six phases:

| # | Phase | Blast radius |
|---|---|---|
| 1 | Validate environment — fail fast on missing prerequisites | R0 |
| 2 | Light ticket fetch — check acceptance-criteria quality | R0 |
| 3 | Full context fetch — comments, subtasks, attachments, links | R0 |
| 4 | Generate — nominally 8–12 tests, adjusted by risk/complexity | R1 |
| 5 | Human review gate — approve / rework / abandon | R1 |
| 6 | Optional sync to the configured test-management adapter | R3 |

Suite size is derived, not fixed. Baseline is **3 cases per acceptance criterion**, then:

| Signal | Direction | Amount |
|---|---|---|
| auth / security keywords | increase | +50% |
| migration | increase | +40% |
| dangerous operations | increase | +30% |
| text-only changes | decrease | -40% |
| logging | decrease | -30% |
| single acceptance criterion | decrease | -20% |
| final clamp | bounds | 3–25 tests |

> The upper clamp protects you against an overloaded ticket ballooning into an unusable suite.

Example: a payments ticket trips the risk keywords, boosting coverage to **14 cases** split **10 manual / 4 API**; on approval at the review gate, a TestRail run is created.

## What It Needs

Hard preconditions — the skill stops if any fail:

- **QA foundation present.** `.agentic/guides/testing/qa-strategy.md` and `qa-health.md` (same directory) must exist. If not, run `qa-foundation` first — it creates `.agentic/guides/testing/`.
- **Work-item adapter declared** in `.agentic/guides/project.md` (examples: `gh`, `glab`). No ticket backend is hardcoded. If missing, configure via `/repo-guides`.
- **Clear acceptance criteria.** If the ticket's AC are vague or missing, the skill asks you to fix the ticket, then re-run.

Optional:

- **Test-management adapter** in `.agentic/guides/integration/test-management.md`. Required only for Phase 6 sync; sync is never automatic and always needs your explicit approval.

Troubleshooting:

| Error | Cause | Fix |
|---|---|---|
| `"Run qa-foundation first"` | QA docs missing | Run `qa-foundation` |
| `"No ticket adapter configured"` | Adapter undeclared | Declare it in `.agentic/guides/project.md` (or `/repo-guides`) |
| `"AC too vague"` | Acceptance criteria unclear/missing | Tighten the ticket, re-run |
| `"Ticket not found"` | Bad ID or credentials | Check the ID and adapter auth |
