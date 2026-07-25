# Case authoring: writing cases on the output templates

Reference for the generation stage of `qa-case-generator`. It fuses two concerns
into one contract: how Phase 5 turns approved planning parameters into cases, and
the exact markdown shape each case must take. Read it just before you author cases;
the machine-scannable field labels below are parsed downstream, so reproduce them
character-for-character.

> Scope: manual/API test *documents* only. No automated test code
> (Playwright/pytest/vitest), no execution, no results reporting. Output is
> human-readable cases that a QA engineer or a sync adapter can consume.

---

## 1. Where this runs

Phase 5 sits between planning and review in the linear 0–7 pipeline. It never asks
the user anything — Phase 4 already settled scope and counts.

| In | Phase 4 handoff | pre-approved counts + ratios |
| --- | --- | --- |
| Out | Phase 6 review gate | generated `test_cases.md` for human sign-off |
| Blast radius | R2 | writes run-artifact files into the repo tree |

Phase 5 has **no halt condition** of its own. If planning was wrong, that surfaces
at Phase 6, not here.

---

## 2. Consume the approved parameters

Phase 4 hands you a parameter set. Treat these keys as the source of truth and do
not recompute or renegotiate them:

```
test_count   p1_count   p2_count   p3_count   api_ratio   ui_ratio
```

`p1_count + p2_count + p3_count` equals `test_count`. `api_ratio` and `ui_ratio`
tell you how many cases land on each template. Honor the split even if your own
read of the ticket would weight it differently — planning owns that decision.

---

## 3. Classify the test type

Scan the requirement text for keyword signals and let the majority decide the
template each case uses.

| Signal class | Indicators |
| --- | --- |
| API-leaning | `endpoint`, `REST`, `GraphQL`, HTTP verbs (GET/POST/PUT/DELETE), `curl` samples |
| UI-leaning | `button`, `screen`, `form`, navigation-style wording |

Emit a classification object with a `primary` and a `secondary` key. Values are the
literal strings:

```
"api"    "ui"    "mixed"
```

> Majority wins. A near-even tie yields a mixed suite — set `primary` to the
> dominant class and author both template kinds in the ratio Phase 4 supplied.

---

## 4. Assign IDs

Case IDs are stable, ticket-scoped, and monotonic.

- Format: `<TICKET_ID>_TC_<NNN>` — e.g. `PROJ-123_TC_001`
- Numbering starts at `001`, zero-padded to three digits.
- On regeneration, continue from `(highest existing number) + 1`; never reuse a
  retired number.
- Before overwriting any pre-existing artifact file, back it up first. Phase 0
  detects the existing suite; Phase 5 preserves the prior copy so a regeneration
  is recoverable.

---

## 5. Priority policy

Every case carries exactly one priority tier. The tier drives both *what* the case
exercises and *how many* of each you produce.

| Tier | Target share | What it covers |
| --- | --- | --- |
| P1 | ≈ 33% | one happy-path case per acceptance criterion; core success scenario |
| P2 | ≈ 42% | boundaries (empty / max / special chars), alternate paths, role variants, integrations, data variation |
| P3 | ≈ 25% | invalid input, error handling, timeout/network errors, unauthorized access, concurrency where relevant |

> P1 is anchored to acceptance criteria: one green-path case per AC, no more. P2 and
> P3 expand outward from there. The percentages are targets — the exact per-tier
> counts come from `p1_count` / `p2_count` / `p3_count`.

---

## 6. Template shapes

Two templates. Both open with the same heading line and carry an AC-traceability
field so every case maps to a specific acceptance criterion.

**Heading line (both kinds):**

```
### <TICKET_ID>_TC_<NNN> [P1|P2|P3] - <title>
```

### 6.1 Field table

| Label | Manual | API | Notes |
| --- | :---: | :---: | --- |
| `**Covers AC**:` | ✓ | ✓ | AC reference this case traces to |
| `**Type**:` | ✓ | ✓ | value `Manual` \| `API` |
| `**Preconditions**:` | ✓ | ✓ | state/data required before steps |
| `**Endpoint**:` | — | ✓ | method + path |
| `**Headers**:` | — | ✓ | JSON block |
| `**Request Body**:` | — | ✓ | JSON block |
| `**Steps**:` | ✓ | ✓ | numbered actions |
| `**Expected Result**:` | ✓ | ✓ | observable outcome |
| `**Expected Response**:` | — | ✓ | JSON block + HTTP status |
| `**Notes**:` | ✓ | ✓ | optional caveats, data refs |

Reproduce the labels exactly, including the bold markers and trailing colon — they
are the scan anchors for Phase 6 and the Phase 7 sync adapter.

### 6.2 Manual template (UI / visual / multi-screen)

```
### PROJ-123_TC_001 [P1] - <title>
**Covers AC**: AC-1
**Type**: Manual
**Preconditions**: <state, seeded data, signed-in role>
**Steps**:
1. <action>
2. <action>
**Expected Result**: <observable outcome>
**Notes**: <optional>
```

Use the manual template for anything the user sees or navigates: screens, forms,
button states, visual checks, flows that cross more than one view.

### 6.3 API template (REST / GraphQL request-response)

```
### PROJ-123_TC_014 [P3] - <title>
**Covers AC**: AC-2
**Type**: API
**Preconditions**: <auth state, existing resources>
**Endpoint**: POST <endpoint_path>
**Headers**:
```json
{ "Authorization": "Bearer <bearer_token>", "Content-Type": "application/json" }
```
**Request Body**:
```json
{ "field": "<value>" }
```
**Steps**:
1. <send request>
**Expected Result**: <outcome summary>
**Expected Response**:
```json
{ "error": "<message>" }
```
Status: 400
**Notes**: <optional>
```

Embed real JSON in the `**Headers**:`, `**Request Body**:`, and
`**Expected Response**:` blocks, and always state the HTTP status alongside the
expected response.

### 6.4 API scenario → status mapping

| Tier | Scenarios | Expected status |
| --- | --- | --- |
| P1 | valid input; authenticated request returns data | `200` / `201` |
| P2 | omitted optional fields; max-length input; role variants | `200` (behavioral variance) |
| P3 | missing required field | `400` |
| P3 | bad/expired token | `401` |
| P3 | absent resource | `404` |
| P3 | server fault | `500` |

---

## 7. Placeholders and conventions

Use the canonical placeholder vocabulary so cases stay data-agnostic and a reviewer
can slot in real values without guessing intent.

- **Identity/auth:** `<valid_username>`, `<invalid_username>`, `<valid_email>`, `<invalid_email>`, `<valid_password>`, `<weak_password>`, `<expired_password>`, `<admin_user>`, `<regular_user>`, `<guest_user>`
- **Entities:** `<user_id>`, `<product_id>`, `<order_id>`, `<valid_id>`, `<invalid_id>`, `<non_existent_id>`, `<session_id>`
- **Tokens/keys:** `<valid_token>`, `<expired_token>`, `<invalid_token>`, `<api_key>`, `<jwt_token>`, `<bearer_token>`
- **Time:** `<current_timestamp>`, `<past_date>`, `<future_date>`, `<iso_8601_datetime>`
- **Endpoints:** `<base_url>`, `<endpoint_path>`

The delimiter style — angle brackets vs. curly braces — is not yours to choose. Read
the project's `qa_conventions` setting and apply whichever delimiter it dictates
across every placeholder in the suite.

---

## 8. Persist artifacts

Write the suite into the dated task directory:

```
docs/superpowers/qa-tasks/<date>-<slug>/manual/
```

| File | Contents |
| --- | --- |
| `ticket-analysis.md` | classification + planning summary carried in |
| `test_cases.md` | the authored cases |
| `meta.json` | counts, splits, IDs, regeneration bookkeeping |
| `events.jsonl` | append-only run ledger |

Back up any file already present before overwriting (see §4).

---

## 9. Completion banner and handoff

Close Phase 5 with a banner, then hand off to Phase 6. Report:

- generated count
- P1 / P2 / P3 split
- UI / API split
- artifact directory

> Do not sync anywhere here. Phase 7 owns the optional push to a test-management
> system (R3, always behind a gate, skippable when no adapter is configured).
> Phase 5 stops at written files.

---

## Cross-references

- `test-templates.md` — sibling source for the raw template markdown and the
  placeholder vocabulary.
- `SKILL.md` — coverage formula, risk multipliers, priority-distribution quick
  reference, and the common-mistake list.
- `phase-4-test-suite-planning.md` — defines the plan the parameters come from.
- `phase-5-test-case-generation.md` — the executable step list this reference backs.
- `phase-6-user-review-gate.md` — the review gate that consumes this output.
- `qa-foundation` — recovery skill re-run when Phase 1 validation fails.
