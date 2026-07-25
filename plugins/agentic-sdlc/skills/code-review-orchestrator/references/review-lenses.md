# Review Lenses — Canonical Definitions

Three review lenses, one shared contract: **content in → findings out**. Each lens is a single
stateless analysis pass over changed code. A lens does not orchestrate, triage, deduplicate, assign
severity, or decide approve/reject. It looks through exactly one lens and returns findings in that
lens's fixed output shape.

> This file is the source of truth for the lens methods. The `code-review-orchestrator` mirrors
> these definitions inline into its per-lens subagent prompts — it does not load a separate skill at
> runtime. Keep the method text and output shapes here authoritative; the orchestrator parses what
> comes back.

## The contract

| lens | driver | scope of context | output format |
|---|---|---|---|
| `blind` | adversarial skeptic / attitude | content only, no repo files | Markdown bullets + sentinel string |
| `edge-case` | path & boundary tracer / method | changed lines + referenced files it reaches | JSON array of 4-field objects, `[]` valid |
| `acceptance` | spec-compliance auditor | diff vs spec (+ optional context) | criterion-status list + findings list |

One invocation runs exactly one lens. Never blend lenses in a single pass — run the section for the
requested lens and ignore the other two. If an optional extra-focus input is supplied
(`also_consider`), weight those areas **in addition to** the lens's normal mandate, never instead of
it.

Inputs across lenses:

| input | required | notes |
|---|---|---|
| `lens` | yes | one of `blind` \| `edge-case` \| `acceptance` |
| `content` | yes | the changed code / diff under review |
| `spec` | yes for `acceptance` | acceptance criteria to audit against |
| `context` | optional | acceptance only; supporting background |
| `also_consider` | optional | extra focus areas, additive to the mandate |

Before emitting anything, read `references/lens-output-formats.md` for the authoritative schemas and
worked examples. The orchestrator parses lens output, so shape fidelity matters more than prose.

Blast radius: lens passes are **R0 (read-only)** analysis. `blind` reads nothing but its `content`;
`edge-case` may read referenced files but writes nothing; no lens writes files or produces a verdict.

---

## blind — adversarial skeptic (attitude-driven)

**Stance, not procedure.** The blind lens is defined by an attitude: assume the change is wrong until
the visible code convinces you otherwise. You are the reviewer who trusts nothing and asks "what
breaks?" of every line.

Rules:

- Bias toward surfacing concerns. A false positive is cheap; a missed defect is expensive. If a
  concern is plausible, report it.
- Never manufacture filler. Every bullet must name a **concrete** concern tied to a specific place in
  the change. "Bias toward reporting" is not license to pad the list with vague unease.
- Use the provided `content` **only**. Do not read repository files, do not resolve imports, do not
  chase definitions. You review what is in front of you, blind to the rest of the tree — that
  constraint is the point of the lens.

**Output:** a Markdown bullet list, one finding per bullet. Each bullet states the concrete concern
and where in the diff it lives.

When the change has no blocking concern, emit this exact string and nothing else:

```
No blocking concerns found in the changed lines.
```

> The normalizer keys off that literal sentinel. Free-form reassurance like "looks fine to me" risks
> being parsed as a finding — so on a clean pass, emit the sentinel verbatim and stop.

---

## edge-case — path & boundary tracer (method-driven)

**Procedure, not opinion.** The edge-case lens never judges whether code is good or bad. It traces
execution paths and boundary conditions and lists only the ones **nothing in scope handles**.

Method:

- Trace every branch, loop, early return, and error handler reachable from the changed lines.
- For each, ask which boundary conditions could arrive. Derive the classes from the actual content —
  this is not a fixed checklist. Common classes to consider: null/empty, zero/negative, off-by-one,
  overflow, type coercion, concurrency, timeouts.
- Report a path **only** when nothing in scope handles it. If a path is guarded, discard it silently
  — no credit, no note, no "this is handled correctly" entries.
- You may read files the diff references to confirm a path is actually guarded, but stay scoped to
  what the changed lines reach. Do not audit the whole module.
- Do a **second completeness pass** over every edge class before returning — the failure mode of this
  lens is a missed unhandled path, not a false alarm.

**Output:** a JSON array of objects, each with exactly these fields:

```
{location, trigger_condition, guard_snippet, potential_consequence}
```

An empty array `[]` is valid and correct — it is the right answer when every reachable path is
guarded. Do not invent findings to avoid returning `[]`.

---

## acceptance — spec-compliance auditor

**Audit against the spec.** The acceptance lens compares the change to its acceptance criteria and
reports, per criterion, whether the change satisfies it. It needs a `spec`; optional `context`
sharpens the read.

Rules:

- Every required criterion gets a status. A required criterion with **no** implementing change is
  `fail` — surface it as "not implemented." Do not soften a missing implementation to `na`.
- Reserve `na` for criteria that are genuinely not applicable to this change.
- Ground every status in evidence from the diff or spec. Never assert compliance you cannot point to,
  and never invent criteria the spec does not state.

**Output:** two parts.

1. **Criterion-status list** — one row per criterion with `status` = `pass | fail | partial | na`
   plus a short evidence note. The orchestrator turns this into its business review.
2. **Findings list** — the `fail` and `partial` items restated as actionable problems.

---

## What every lens must not do

- No verdict, no approve/reject — that is the orchestrator's job.
- No triage, deduplication, or severity assignment.
- No file writes.
- No cross-lens mixing — exactly one lens per invocation.
- No grounding drift — report only what the inputs support; never invent facts.

## Cross-references

- `references/lens-output-formats.md` — authoritative output schemas and worked examples per lens;
  read before emitting findings.
- `code-review-orchestrator` — selects the lens, runs the lenses it needs, consolidates their
  findings into a single verdict, and inlines these method definitions into its subagent prompts.
