# Suite Planning: Case Types, Coverage, and Depth

Stage 4 of `qa-case-generator`. You size the suite, decide the type and priority mix, sketch a grouped outline, and hold a user gate — all **before** any full case body is written. Nothing here emits real test cases; this is the cost-control checkpoint that stands between analysis and generation.

- **Blast radius:** R1 — you compute, present, and (on approval) persist parameters to run memory. No repo writes, no external calls.
- **Halt on:** user cancel, or a change request you cannot satisfy by recompute.
- **Never** enter Stage 5 (generation) without a recorded approval from this stage. That is the load-bearing rule of the whole skill.

> Generation burns tokens per case. A wrong count or wrong split multiplies that waste across the entire suite. Sizing cheaply and confirming once is the point of the gate.

---

## Inputs you consume

| From | What | Used for |
|------|------|----------|
| Stage 2 (AC quality) | per-AC clarity scores, 0–3 | coverage base |
| Stage 3 (full context) | risk signals from description, comments, subtasks, links | multipliers / reducers |
| Ticket text | AC + description keywords | API-vs-UI split |

The clarity rubric (what earns a 0 vs a 3) is defined upstream — do not redefine it here. You read the scores, you do not grade them.

---

## Step 1 — Coverage count

Base is the sum of clarity scores. Scale it by risk multipliers, shrink it by simplicity reducers, then clamp.

```
test_count = base × multipliers × reducers
```

`base = Σ(per-AC clarity, each 0–3)`.

### Complexity multipliers (stack multiplicatively)

| Signal | ×    |
|--------|------|
| payment / billing | 1.4 |
| multi-step workflow | 1.3 |
| authorization / permissions | 1.3 |
| data migration | 1.2 |
| external integration | 1.2 |
| state transitions | 1.2 |

### Simplicity reducers (stack multiplicatively)

| Signal | ×    |
|--------|------|
| single AC | 0.8 |
| text / label change | 0.6 |
| logging / monitoring | 0.7 |
| ticket with zero comments | 0.9 |

Apply every signal that matches; multipliers and reducers can both fire on the same ticket. Round the result to the nearest integer.

### Bounds

| Result | Action |
|--------|--------|
| `< 3` | Warn the AC is too abstract to justify fewer than 3 tests; enforce a **3-test floor**. |
| `> 25` | **Cap at 25** and suggest the user split the ticket into smaller stories. |

> The floor stops a vague ticket from producing a token-cheap but useless one-test suite. The ceiling stops a bloated ticket from generating an unreviewable wall of cases — splitting the ticket is the correct fix, not a bigger suite.

**Worked example.** Four ACs scoring 3, 3, 2, 2 → `base = 10`. Ticket is an external integration (×1.2), no reducers. `test_count = 10 × 1.2 = 12`.

---

## Step 2 — Case type (API vs UI)

Decide the type weighting purely by counting keyword indicators in the AC and description. No guessing beyond the scan.

- **API indicators:** endpoint, REST, GraphQL, HTTP verbs, curl, API docs.
- **UI indicators:** button, screen, form, navigation, mockup.

```
api_ratio = api_indicators / total_indicators
ui_ratio  = ui_indicators / total_indicators
```

`total_indicators = api_indicators + ui_indicators`. The two ratios drive how many API-shaped vs UI-shaped cases the outline leans toward.

**Worked example.** Text hits `endpoint`, `REST`, `POST` (3 API) and `button`, `form` (2 UI) → total 5, `api_ratio = 0.6`, `ui_ratio = 0.4`.

---

## Step 3 — Depth (priority mix)

Split `test_count` across three priorities, each rounded to the nearest integer, each with a floor of 1.

| Priority | Share | Focus |
|----------|-------|-------|
| P1 | 33% | critical path |
| P2 | 42% | edge cases |
| P3 | 25% | negative |

Round P1 and P2 to nearest integer; let P3 absorb the remainder so the three sum to `test_count`. If any bucket rounds to 0, bump it to 1 and borrow from the largest bucket.

**Worked example.** `test_count = 12` → P1 = round(3.96) = 4, P2 = round(5.04) = 5, P3 = 12 − 4 − 5 = 3.

---

## Step 4 — The outline (not the cases)

Produce an outline only — never full case bodies. Group by AC / functional area, and for each group give:

- a per-area count estimate,
- 1–2 sample titles per priority present in that area.

Alongside the outline, present a **rough token-cost estimate** for the generation step so the user can weigh the spend. The estimate is a coarse placeholder, not a computed budget — do not invent precise math for it.

**Header line**

```
Test Suite Plan for <TICKET_ID>
```

The user-facing variant prefixes it: `📋 Test Suite Plan for <TICKET_ID>`.

---

## Step 5 — The approval gate

Present the plan, then parse the user's reply into one of three intents.

| Intent | Keyword | Synonyms | Behavior |
|--------|---------|----------|----------|
| proceed | `proceed` | yes, looks good | lock parameters, advance to Stage 5 |
| adjust | `adjust` | change | mutate the one requested parameter, rebuild the **whole** plan, re-present |
| cancel | `cancel` | stop, skip | exit; log the skip to the audit ledger |

Specific asks — "more P1s", "fewer tests", "make it API-heavy" — are **adjust**, not new intents. On any adjust: change only what was asked, recompute the full plan from that one mutation, and show it again. Loop until the user proceeds or cancels.

> Rebuilding the whole plan on every tweak keeps the count, split, and ratios internally consistent. Patching one number in place drifts them out of agreement.

Record the outcome. Approvals and skips both land in `decisions.jsonl` / `events.jsonl` so the run stays auditable.

---

## Outputs

On **proceed**, hold these parameters in run memory and hand them to Stage 5:

```json
{
  "test_count": <N>,
  "p1_count": <N>,
  "p2_count": <N>,
  "p3_count": <N>,
  "api_ratio": <0-1>,
  "ui_ratio": <0-1>,
  "user_approved": true
}
```

Then print the completion banner:

```
✅ Phase 4: Test Suite Planning
<approval note>
Coverage: <test_count> tests (P1=<p1>, P2=<p2>, P3=<p3>)
<ready-for-Phase-5 line>
```

---

## Recovery

| Situation | Move |
|-----------|------|
| user pushes back on the plan | treat as **adjust**; recompute and re-present |
| user cancels | log the skip and exit cleanly |

Upstream failures (missing QA docs, weak ACs) belong to earlier stages — you only reach Stage 4 once those passed.

---

## Boundaries

- **Outline only.** No real cases here; case bodies are Stage 5's job.
- **Token estimate is a placeholder.** This stage does not define token-estimation math.
- **Clarity rubric lives elsewhere.** The 0–3 scale is referenced, not defined here.
- **Templates live elsewhere.** Case structure is not this file's concern.

## Cross-references

| File / skill | Relationship |
|--------------|--------------|
| `SKILL.md` | single source of truth for the coverage formula, multipliers, and priority split — this stage mirrors it |
| `phase-5-test-case-generation.md` | consumes the approved parameters above |
| `test-templates.md` | manual + API case structures, applied in Stage 5 |
| `qa-foundation` | builds the QA docs that Stage 1 validated before you got here |
