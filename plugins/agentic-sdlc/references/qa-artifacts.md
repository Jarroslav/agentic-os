# QA Artifacts

`qa-planner` writes two documents. This file is the shape both must take, so
that `sdlc-pipeline`, `qa-planner --review-tests` and the Phase 7 reviewer can
read them without guessing.

Both are markdown because humans read them at a gate. Both put the part that
can block a run first, and everything advisory after it — a reader who stops
after the first table has still seen everything that matters.

## qa-checklist.md

Written to `<run_dir>/qa-checklist.md` by `qa-planner --checklist`, before any
implementation begins.

```markdown
# QA Checklist — <run-id>

**Feature**: <the goal, in one line, from requirements.md>
**Risk flags**: <comma-separated, or "none">
**Written**: <ISO 8601 date>
**Merge base**: <sha>

## Blocking scenarios

Must be covered on this branch. The gate stops on any high- or medium-risk row
here that no test covers.

| ID | Scenario | Level | Covered today | Risk | First failing assertion |
|----|----------|-------|---------------|------|-------------------------|
| S1 | Rounds a 3-decimal line total to 2 places | unit | covered (TC-118) | low | `roundLine(1.005)` returns `1.01` |
| S2 | Rejects a negative quantity instead of crediting the invoice | unit | gap | high | `addLine({qty: -1})` throws `quantity must be positive` |

## Deferred to the harness

Advisory. Worth a follow-up in the external harness, never a reason to stop
this run. *(Omit the section when qa-strategy.md documents no harness.)*

| ID | Scenario | Level | Covered today | Risk | Where it goes |
|----|----------|-------|---------------|------|---------------|
| S3 | Two concurrent edits to one invoice settle to a single total | integration (harness) | unknown | medium | `<harness_path>/<area>/test_<feature>.py` |

## Deferred to manual

Advisory. Belongs in the test case management system. *(Omit the section when
qa-strategy.md configures no adapter.)*

| ID | Scenario | Level | Covered today | Priority | Where it goes |
|----|----------|-------|---------------|----------|---------------|
| S4 | A printed invoice matches the on-screen total to the cent | manual | gap | high | new case in <project> |

## Known gaps in the touched area

<Gaps carried over from qa-health.md that overlap this feature, as bullets, or "none">

## Constraints

<Anything from qa-strategy.md that shapes how these tests must be written, or "none">
```

### Field rules

- **Blocking** is the section, not a column. A row under "Blocking scenarios"
  blocks; rows under either deferred section never do. Encoding it twice invites
  the two to disagree.
- **Level** — one of `unit`, `integration`, `integration (harness)`, `e2e`,
  `manual`.
- **Covered today** — `covered (<ID>)` when the adapter or harness scan found a
  real test, `gap` when qa-health.md lists the area as risky and untested,
  `unknown` when neither was available to ask. `unknown` is an honest answer;
  do not round it to `gap`.
- **Risk** / **Priority** — `high` where a gap meets a risk flag, `medium` for a
  gap on its own, `low` where something already covers it.
- **First failing assertion** — concrete enough to write the failing test from
  without rereading the requirement: name the call, the input, and what comes
  back. "Validates input" is not an assertion.
- **Where it goes** (deferred rows only) — the actual path or system location,
  not a description of one.

---

## qa-test-review.md

Written to `<run_dir>/qa-test-review.md` by `qa-planner --review-tests`, after
the tests exist.

```markdown
# Test Review — <run-id>

**Status**: PASSED | ISSUES_FOUND
**Written**: <ISO 8601 date>

## Scenario verdicts

Blocking scenarios only. Deferred rows are out of scope here by construction.

| ID | Scenario | Verdict | Where it is tested |
|----|----------|---------|--------------------|
| S1 | Rounds a 3-decimal line total | covered | invoice-total.test.ts:24 |
| S2 | Rejects a negative quantity | missing | — |

## Test quality findings

A test that passes for the wrong reason is worse than a missing one: it reports
safety that is not there. Findings here are about that, not about style.

| Location | What is wrong | Severity | Concrete fix |
|----------|---------------|----------|--------------|
| invoice-total.test.ts:61 | Asserts the call returned something, not what it returned | medium | `expect(total).toEqual({ net: 1200, tax: 240 })` |
| — | S2 has no test at all | high | `it('rejects a negative quantity', () => expect(() => addLine({qty: -1})).toThrow('quantity must be positive'))` |

## Tally

- Blocking scenarios covered: <N> of <total>
- Quality findings: <N> high, <N> medium
```

### Field rules

- **Verdict** — `covered`, `partially-covered`, or `missing`. Use
  `partially-covered` when a test exercises the scenario but asserts less than
  the scenario claims.
- **Severity** — `high` for a scenario with no test, or an assertion that cannot
  fail; `medium` for a weak assertion or a name that hides what broke; `low` for
  style alone.
- **Concrete fix** — paste-ready code. A description of the fix is not a fix.
- **Status** — `ISSUES_FOUND` if any row is `missing` or any finding is `high`;
  `PASSED` otherwise.
