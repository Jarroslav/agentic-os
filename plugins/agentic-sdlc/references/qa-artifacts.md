# QA Artifacts

Format contracts for artifacts produced by `qa-planner`. These are consumed
by `sdlc-pipeline`, `qa-planner --review-tests`, and the Phase 7 code reviewer.

## qa-checklist.md

Written to `<run_dir>/qa-checklist.md` by `qa-planner --checklist`.

```markdown
# QA Checklist — <run-id>

**Feature**: <one-line goal from requirements.md>
**Risk flags**: <comma-separated list, or "none">
**Generated**: <ISO 8601 date>
**Merge base**: <sha>

## Automated — this run

Scenarios to implement in the current feature branch. Gate blocks on uncovered high/medium-risk scenarios here.

| # | ID | Scenario | Type | Existing coverage | Risk | Suggested test-first description |
|---|----|----------|------|-------------------|------|----------------------------------|
| 1 | S1 | Happy path: <description> | unit | covered (TC-42) | low | `expect(fn(input)).toBe(expected)` |
| 2 | S2 | Edge case: <description> | integration | gap | high | `expect(() => fn(null)).toThrow('input required')` |

## Automated — harness backlog

Non-blocking. Implement as a follow-up in the external test harness.
*(Omit section if no harness repo is documented in qa-strategy.md.)*

| # | ID | Scenario | Type | Existing coverage | Risk | Where to add |
|---|----|----------|------|-------------------|------|--------------|
| 3 | S3 | Integration: <description> | integration (harness) | unknown | medium | `<harness_path>/<coverage_area>/test_<feature>.py` |

## Manual — backlog

Non-blocking. Create or update these test cases in the test case management system.
*(Omit section if no test case management is configured in qa-strategy.md.)*

| # | ID | Scenario | Type | Existing coverage | Priority | Where to add |
|---|----|----------|------|-------------------|----------|--------------|
| 4 | S4 | Manual verification: <description> | manual | gap | high | Jira: create test case in <project> |

## Coverage gaps in affected area

<Bullet list of gaps from qa-health.md overlapping this feature, or "none">

## Notes

<Relevant constraints from qa-strategy.md, or "none">
```

### Field rules

- `Blocking`: implicit by section — `yes` for "Automated — this run"; `no` for harness backlog and manual backlog
- `Type`: `unit` | `integration` | `integration (harness)` | `e2e` | `manual`
- `Existing coverage`: `covered (<ID>)` if found in test case adapter or harness scan | `gap` if in qa-health risky areas | `unknown` if adapter not configured and harness not scanned
- `Risk` / `Priority`: `high` if gap + risk flag overlap | `medium` if gap only | `low` if covered
- `Suggested test-first description`: must be specific enough to write a failing test from — include function name, input, and expected outcome or assertion style
- `Where to add` (harness/manual only): exact file path or system location where the test/case should be created

---

## qa-test-review.md

Written to `<run_dir>/qa-test-review.md` by `qa-planner --review-tests`.

```markdown
# QA Test Review — <run-id>

**Status**: PASSED | ISSUES_FOUND
**Generated**: <ISO 8601 date>

## Scenario Coverage

Only `Blocking: yes` scenarios (from "Automated — this run") are evaluated here.

| # | Scenario | Coverage | Test file(s) |
|---|----------|----------|--------------|
| 1 | Happy path: ... | covered | auth.test.ts:12 |
| 2 | Edge case: ... | missing | — |

## Quality Findings

| Test file | Line | Finding | Severity | Fix suggestion |
|---|---|---|---|---|
| auth.test.ts | 45 | Asserts truthy only; should assert specific value | medium | `expect(result).toEqual({ id: 1, role: 'admin' })` |
| — | — | No test for scenario #2 (edge case: null input) | high | `it('throws on null', () => { expect(() => fn(null)).toThrow('input required') })` |

## Summary

- Scenarios covered: <N>/<total blocking>
- Quality issues: <high count> high, <medium count> medium
```

### Field rules

- `Coverage`: `covered` | `partially-covered` | `missing`
- `Severity`: `high` (missing scenario / assertion checks nothing) | `medium` (weak assertion / bad naming) | `low` (style only)
- `Fix suggestion`: must include exact code the engineer can paste
