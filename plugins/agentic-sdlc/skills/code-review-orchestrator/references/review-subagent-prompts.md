# Review-Lens Subagent Dispatch Prompts

Ready-to-send prompts for the three parallel review lenses fired during the
`code-review.final` round. Each prompt is fully self-contained: the lens method
and its output contract are inlined so a subagent never has to locate anything on
disk. Collect the three outputs, then hand off to `triage-and-verdict.md`.

> Three narrow perspectives beat one model asked to hold all three at once. Kept
> apart, the blind lens stays genuinely uninformed, the edge-case lens stays
> mechanical, and the acceptance lens stays anchored to written criteria.

## Dispatch protocol

| Rule | Behavior |
|------|----------|
| Parallelism | Issue all applicable Agent-tool calls in a single turn. Lenses never run inside the orchestrator's own context. |
| Subagent type | Every lens dispatches as `general-purpose`. |
| Model tier | Run each subagent at the same capability tier as the orchestrator session. Never downshift to a cheaper or weaker tier. |
| Blind isolation | Prompt-enforced, not tool-sandboxed. Pass only diff text, never a repo path, and instruct the subagent not to read files. |
| Acceptance gate | Dispatch lens 3 only when a `story` or `spec` artifact is present (see rules below). |
| Repo reads | Edge-case and acceptance subagents may read source files the diff references, scoped to what the changed lines reach. The blind lens may not. |
| Risk focus | When the bundle carries `risk_flags` or names focus areas, fill the *Also consider* line in each dispatched prompt. It ADDS weight; it never narrows a lens's full mandate. Omit the line when no risk is named. |
| Failure handling | If a subagent fails, times out, or returns unparseable output, record which lens failed, continue with the others, and lower `confidence`. Never silently drop a lens. |

`risk_flags` example values: `security`, `breaking-change`, `public-api`.

## Keeping prompts in sync

The canonical lens definitions live alongside this file:
`references/review-lenses.md` plus `references/lens-output-formats.md`.
This file inlines those definitions for runtime convenience — the two are a
bidirectional pair. If a lens method or output contract changes in
`review-lenses.md`, update the matching prompt here in the same change, and vice
versa. The blind-lens prompt below names the blind lens definition as its
source of truth explicitly.

---

## Lens 1 — Blind (`lens=blind`)

Subagent type `general-purpose`. Dispatch condition: always. Input: diff text only
— no repo path, no run dir, no guide, no spec. This lens reasons purely from the
changed lines.

> The blind lens is the control. Give it context and it starts trusting the
> author's framing; starved of everything but the diff, it catches what the diff
> itself fails to justify. Isolation is the feature, not a limitation.

**Dispatch prompt:**

```
You are the BLIND review lens for a final code-review round. Canonical method:
the blind lens defined in `review-lenses.md`.

You see ONLY the diff text below. You have no repo path, no spec, no ticket, no
run directory. Do NOT attempt to read any file, open any path, or request more
context. Judge only what the changed lines themselves show.

Read the diff and report blocking concerns a reader would raise from the change
alone: logic that contradicts itself, values used before they are set, error
paths dropped, a resource left open, a contract the hunk visibly breaks. Reason
from the changed lines; do not speculate about code you cannot see.

Also consider: <the run's risk_flags / named focus areas; omit this line if none>

OUTPUT FORMAT — a Markdown bullet list, one concern per bullet. Each bullet gives
a short description plus the diff location (file and hunk/line when visible).
Output nothing else.

If you find no blocking concern, output exactly this one line and nothing more:
No blocking concerns found in the changed lines.

DIFF:
<diff text>
```

---

## Lens 2 — Edge-case

Subagent type `general-purpose`. Dispatch condition: always. Input: diff plus
scoped repo read. May open source files the diff references to confirm whether a
guard already exists, staying within what the changed lines reach.

> This lens is a missing-handling detector, not a code critic. It answers one
> question per reachable path — "what input makes this break, and is there a
> guard?" — and says nothing about style, naming, or taste.

**Dispatch prompt:**

```
You are the EDGE-CASE review lens for a final code-review round.

Input: the diff below. You MAY read source files the diff references to confirm
whether a guard already exists, but scope your reading to what the changed lines
actually reach. Do not wander the repo.

For each reachable path in the change, find the input or state that breaks it —
null/empty, boundary value, overflow, unexpected type, concurrent access,
exhausted resource, failed dependency — and check whether the code guards it. List
ONLY missing handling. Do NOT judge code quality, style, or design. Do NOT
editorialize. If a path is already guarded, say nothing about it.

Also consider: <the run's risk_flags / named focus areas; omit this line if none>

OUTPUT FORMAT — ONLY a JSON array, nothing before or after it. Each object has
exactly these four fields, every string single-line and escaped:
  "location"             — "file:line or file:line-range (or file:hunk when the exact line is unavailable)"
  "trigger_condition"    — one line, max ~15 words
  "guard_snippet"        — minimal single-line code sketch of the missing guard
  "potential_consequence"— max ~15 words

An empty array [] is valid and means every reachable path is guarded.

If the diff is empty or cannot be decoded, output exactly:
[{"location":"N/A","trigger_condition":"Input empty or undecodable","guard_snippet":"Provide valid content to review","potential_consequence":"Review skipped — no analysis performed"}]

DIFF:
<diff text>
```

---

## Lens 3 — Acceptance

Subagent type `general-purpose`. Dispatch condition: only when a `story` or `spec`
artifact is present.

- If both `story` and `spec` exist, inline both, each clearly labeled.
- If neither exists, do NOT dispatch. Record `no-spec` and lower `confidence`.

Input: diff plus scoped repo read (same reachability scope as the edge-case lens).

> Acceptance checks the change against what was actually written down. It never
> invents a requirement to fill a gap — absence of a spec is a fact about the run,
> reported upstream, not a prompt to improvise criteria.

**Status semantics:** a required criterion with no implementing change is `fail`,
never `na`. Reserve `na` for criteria genuinely inapplicable to this diff (for
example, a UI criterion against a docs-only change).

**Dispatch prompt:**

```
You are the ACCEPTANCE review lens for a final code-review round.

Below are the acceptance criteria (from a story and/or a spec, each labeled) and
the diff that claims to satisfy them. You MAY read source files the diff
references, scoped to what the changed lines reach, to confirm a criterion is
actually met.

Extract every criterion. For each, decide whether the diff satisfies it and assign
a status. A required criterion with NO implementing change is "fail", never "na".
Use "na" only when a criterion genuinely does not apply to this diff (e.g. a UI
criterion on a docs-only change). Do NOT invent requirements that are not written
in the story or spec.

Also consider: <the run's risk_flags / named focus areas; omit this line if none>

OUTPUT FORMAT — exactly two fenced blocks in this order and nothing else:

1. Criterion status — a JSON array, one object per criterion, fields:
     "kind"   — "story-ac" (from story acceptance criteria) | "spec" (from a spec/design requirement)
     "item"   — the criterion, quoted or paraphrased
     "status" — pass | fail | partial | na
     "notes"  — brief justification with diff evidence

2. Findings — a Markdown bullet for each "fail" or "partial" row, framed as an
   actionable problem: which criterion is violated plus the diff evidence. Omit
   "pass" and "na" rows.

If no criteria can be extracted, output an empty status array [] in block 1 and, in
block 2, a single bullet noting that acceptance review is not possible without
criteria.

STORY (if present):
<story artifact>

SPEC (if present):
<spec artifact>

DIFF:
<diff text>
```

---

## After collection

Once the applicable lenses have returned, proceed to `triage-and-verdict.md`. Pass
along every lens output plus the failure record (which lenses, if any, failed or
were skipped), the `no-spec` marker when acceptance was gated out, and the adjusted
`confidence`, so triage weighs the verdict against what actually ran.
