# Context Assembly — Shared QA Authoring Reference

Assemble the full ticket-and-code picture that QA generation runs on. This is the
gather step: pull the work item and everything attached to it, resolve its links,
map it onto the codebase, score its risk and structural weight, and hand a single
grounded aggregate downstream. It is shared by the QA generator skills — the
`qa-case-generator` pipeline loads it at its context-gathering phase, and any
sibling generator that produces cases from a work item reuses the same contract.

> This step collects and scores; it never judges. It does not open a decision
> gate and never halts the pipeline. On thin or missing data it emits a warning
> and proceeds with whatever it could fetch. Gating happens later, in planning
> and human review.

**Blast radius:** `R1`. Reads are the work item, its linked items, and repo
files; the only write is the assembled aggregate into the run's artifact area
under `.agentic/`. External reads flow through an adapter, never a hardcoded
backend. **Model tier:** `economy` — this is mechanical fetch plus keyword-class
scanning, not reasoning.

---

## Output contract

Context assembly produces exactly these top-level fields for the planning phase:

| Field | Type | Meaning |
|---|---|---|
| `ticket_context` | JSON object | The full aggregate — every fetched field, linked items, and code-area map, merged into one blob |
| `risk_signals` | list | Risk keywords that matched, across all fetched content |
| `risk_multiplier` | number | Coverage weight derived from `risk_signals` (base `1.0` + matched bumps) |
| `complexity_indicators` | list | Structural signals that tripped (subtask count, comment volume, priority) |
| `complexity_multiplier` | number | Coverage weight derived from `complexity_indicators` |

> The multipliers are **stored, not applied, here.** Context assembly computes
> and records them; the planning phase (`phase-4-test-suite-planning.md`) feeds
> them into the coverage math. Do not act on them in this step.

Any code-area mapping and link-resolution detail lives inside `ticket_context`
under implementation-defined sub-keys — the five fields above are the guaranteed
surface every consumer can rely on.

---

## What to fetch

Resolve the work item through the **work-item adapter** declared in
`.agentic/guides/`. The adapter abstracts the ticket backend (issue tracker, work
tracker, or file-backed story) so nothing here is bound to a specific vendor.

Fetch the full record — the lightweight AC-check phase saw only a subset; this
phase pulls everything:

| Field | Notes |
|---|---|
| title | baseline |
| description | baseline |
| AC | baseline (acceptance criteria) |
| comments | full thread; fuels the comment-volume complexity signal |
| subtasks | full list; fuels the subtask-count complexity signal |
| linked items | resolve the links **and** fetch the linked items themselves (see below) |
| attachments | metadata and references; do not inline binaries |
| priority | fuels the priority complexity signal |
| labels | scanned for risk keywords and code-area hints |
| `ticket_url` | canonical reference kept for citation and handoff |

---

## Linked-issue traversal

Resolve links **one hop only.** For each item the ticket links to, fetch its core
fields (title, type, status, url) through the same adapter. Do not follow
links-of-links — transitive recursion blows up fan-out and re-fetches the world.

Rules:

- **Deduplicate by id.** A ticket often reaches the same item by two paths; fetch it once.
- **Guard cycles.** `A → B → A` is common with bidirectional link types; the one-hop cap plus dedup closes the loop, but track visited ids explicitly.
- **Prioritise by link type** where the adapter exposes it. Parent/epic and blocking relationships (`blocks`, `is-blocked-by`) get full-field fetches; loose `relates-to` links may stay shallow (reference only).
- **Subtasks are first-class**, not "links" — traverse them fully. They drive both the code-area map and the subtask-count complexity bump.
- Every hop goes through the work-item adapter, keeping the backend pluggable.

---

## Code-area mapping

Map the work item onto the regions of the repository it touches, so planning and
generation can target real coverage instead of guessing.

Derive candidate areas from, in order of confidence:

1. **Linked commits / change requests** attached to the ticket — the strongest signal for touched paths.
2. **Explicit file or module paths** named in the description, AC, or comments.
3. **Component / area labels** on the ticket and its subtasks.
4. **QA foundation knowledge** — if `qa-foundation` has recorded test locations and a coverage map under `.agentic/`, cross-reference the candidate areas against it to locate the existing (or missing) tests for each area.

> Ground the mapping. Only record a code area you can trace to fetched content or
> repo files — never invent a path because it "seems related." Unmapped is an
> honest state; a fabricated path corrupts every downstream plan.

Fold the result into `ticket_context` (e.g. a `linked_code` sub-section listing
touched paths and, where known, the tests that already cover them).

---

## Risk-signal scan

Scan **all** fetched content — title, description, AC, comments, subtasks, linked
items, labels — for risk keywords. Each tier contributes its bump once when any of
its keywords appear; sum the matched tiers onto the base of `1.0`.

| Tier keywords | Bump |
|---|---|
| auth, payment, security, password, encryption | +50% |
| migration, data-loss, database schema | +40% |
| admin, delete, production | +30% |

Record every matched keyword in `risk_signals` and the summed weight in
`risk_multiplier`. Example: a ticket mentioning `payment` and `production` yields
`risk_signals: [payment, production]`, `risk_multiplier: 1.80` (`1.0 + 0.50 + 0.30`).

---

## Structural-complexity scan

Score the shape of the work item independently of its keywords. Each indicator
that trips contributes its bump:

| Indicator | Bump |
|---|---|
| 5+ subtasks | +20% |
| 10+ comments | +20% |
| Priority High or Critical | +15% |

Record the tripped indicators in `complexity_indicators` and the summed weight in
`complexity_multiplier`. Then classify the overall complexity as
`low | medium | high` — this label is what surfaces in the completion banner.

---

## Context-budget rules

Keep `ticket_context` within a sane token envelope so the planning and generation
prompts stay affordable and focused. Budget by signal, not by fetching less:

- **Never trim the baseline.** Description and AC are kept in full — they are the specification the cases must satisfy.
- **Reference, don't inline.** Attachments are carried as filenames/urls and metadata; extract text only when it is cheap and clearly relevant. Never inline binary payloads. Keep `ticket_url` and linked-item urls for citation.
- **Truncate long comment threads.** Keep the first comment, the most recent, and **any comment containing a risk keyword**; summarise the rest. Risk-bearing comments must survive truncation — they already fed the scan.
- **Cap link resolution** at one hop (above). This is the primary fan-out control.
- **Preserve raw source text** for kept content so downstream can quote it — do not paraphrase facts away.

---

## Completion banner

On finishing, emit this machine-readable progress marker verbatim (counts and
values filled in):

```
✅ Phase 3: Full Context Fetch
   - Comments: <count>
   - Subtasks: <count>
   - Risk signals: <keywords>
   - Complexity: <low|medium|high>
```

---

## Partial-data handling

This step **never halts.** If the adapter returns an incomplete record, a linked
item is unreachable, or attachments cannot be resolved:

- Assemble `ticket_context` from what was fetched.
- Emit a warning naming what is missing (e.g. "3 linked items unreachable").
- Still emit the completion banner and still compute both multipliers over the available content.

Missing context degrades coverage quality downstream; it does not stop the run.
The human-review gate later in the pipeline is where thin context gets caught.

---

## Handoff

The assembled `ticket_context`, `risk_signals`, `risk_multiplier`,
`complexity_indicators`, and `complexity_multiplier` flow to the planning phase,
`phase-4-test-suite-planning.md`, which consumes the multipliers in its coverage
math. The coverage formula and priority distribution themselves are **not** defined
here — they live in the skill's `SKILL.md` alongside the risk-multiplier quick
reference. This step's job ends at handing over a complete, scored, grounded
aggregate.
