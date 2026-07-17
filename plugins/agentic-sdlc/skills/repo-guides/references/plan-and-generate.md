# Plan and generate the guide set

> One flow, two phases. **Phase 2 (planning)** converts the Phase-1 audit into a
> plan the user can approve. **Phase 3 (generation)** renders the approved guides
> from templates. Phase 2 presents and asks; it never touches disk. Phase 3 is the
> only phase in this flow that writes. Read both halves before you start — the plan
> you build in Phase 2 is the literal input Phase 3 consumes.

You are the agent running the `repo-guides` skill. This is procedure, not
prose for a human reader. Follow it in order.

## Blast radius at a glance

| Phase | Work | Tag |
| --- | --- | --- |
| Phase 2 planning | Read audit, render plan, ask, collect approval | R0 (read-only) |
| Phase 2 ledger | Record the approval verdict to `decisions.jsonl` / `events.jsonl` | R1 (run-artifact writes) |
| Phase 3 guides | Write `.agentic/guides/<category>/<file>.md` | R2 (repo file writes) |
| Phase 3 entrypoints | Edit `CLAUDE.md` / `AGENTS.md` managed regions | R2, and every change outside a managed region needs its own gate |

## Hard rules

- **No writes in Phase 2.** Not one file, not one line — until the user approves.
- **Explicit keyword gate.** Approval requires a keyword the user types: "approve",
  "yes", or "go". Silence, a thumbs-up emoji, or "looks good, but…" is not approval.
- **Open questions block approval.** If any `ask user` item is still open, an
  approval keyword counts as incomplete. Ask the pending questions first, re-render
  the plan, then re-ask.
- **No silent overwrites.** A guide whose code has drifted is only replaced through a
  planned `update` (or an approved `replace` diff). Never overwrite in place unasked.
- **No padding.** Short-but-useful content ships short. Never inflate a guide to hit
  a length target.
- **`project.md` is not a junk drawer.** Route project drift and generic guide
  content to the owning guide, never into `project.md`.

---

## Phase 2 — Planning

### Step 1: Choose the plan driver

> The plan is a conversation with the user, not a monologue. Prefer a structured
> brainstorm when the host offers one.

- If `superpowers:brainstorming` appears in the available skills, invoke it with the
  Skill tool and run the plan conversation through it.
- Otherwise present the plan inline in the main session.
- Never auto-install the superpowers plugin. When it is absent, fall back to the
  inline plan and native subagent support. Absence degrades the experience; it never
  blocks the run.

### Step 2: Build the plan

The plan carries **nine elements**. Emit only the ones that apply to the detected
repo shape.

| # | Element | When |
| --- | --- | --- |
| 1 | Repo shape, with the evidence that decided it | Always |
| 2 | Modules table | Monorepo only |
| 3 | Audit summary, drawn from the six audit sections | Always |
| 4 | Entrypoint target files (`CLAUDE.md`, `AGENTS.md`) | Always |
| 5 | Output directories | Always |
| 6 | Incorporation map (source → destination) | When any area is `incorporate` |
| 7 | Per-scope guide table | Always |
| 8 | Entrypoint merge plan, one row per managed region | Always |
| 9 | Subagent dispatch plan | Monorepo only |

The audit summary must draw from the six Phase-1 sections by name:
`Documentation Map`, `Documentation Analysis`, `Assistant Setup Analysis`,
`Agentic Infrastructure Analysis`, `Conflict And Overlap Analysis`,
`Foundation Readiness And Next Steps`.

Output directories:

| Repo shape | Guide output root |
| --- | --- |
| Single repo | `.agentic/guides/` |
| Monorepo (per module) | `<module>/.agentic/guides/` |

#### Table specs (columns are a contract — reproduce them exactly)

**Modules table** (monorepo only):

```
path | language | framework | build | test
```

Illustrative (a TypeScript monorepo):

| path | language | framework | build | test |
| --- | --- | --- | --- | --- |
| apps/web | TypeScript | Next.js | next | vitest |
| apps/api | TypeScript | Fastify | tsup | vitest |
| packages/ui | TypeScript | React | tsup | vitest |

In this shape the root scope carries a `guide-imports` table only — no root-level
guides. A single repo runs in the main session with no subagents.

**Per-scope guide table:**

```
Category | Action | Proposed guide files | Audit recommendation | Evidence
```

Category examples and their target files:

| Category | Target file |
| --- | --- |
| Architecture | `.agentic/guides/architecture/architecture.md` |
| Testing | `.agentic/guides/testing/testing-patterns.md` |
| Development | `.agentic/guides/development/development-practices.md` |
| API | skip when no routes are detected |

**Incorporation table** (only when element 6 applies):

```
Existing documentation | Factory destination | Decision needed
```

**Entrypoint merge table:**

```
Target | Managed regions | Outside managed regions
```

Managed-region names you will see: `guide-imports`, `task-classifier`,
`critical-rules`, `commands`.

### Step 3: Map each audit recommendation to a plan action

Each action is a distinct behavior. Do not collapse them.

| Action | Behavior |
| --- | --- |
| `preserve` | Keep strong human-authored docs authoritative. Edits land only inside a plan-named managed section/subsection. |
| `incorporate` | Ingest existing docs into the factory-owned destination. List source→destination. Ask whether the original stays authoritative, is superseded for AI guidance, or remains host-specific. |
| `replace` | For stale/incorrect generated content. Requires an approved diff before replacing. |
| `merge` | Only when the source already shares the same authority surface, or targets an approved compatible managed region/guide. Enumerate retained vs. added content. |
| `skip` | Exclude the area; record the reason. |
| `ask user` | Stop before any write. Ask one concrete question. Re-render the plan after the answer. |
| `halt` | Stop the run. Phases 3–4 stay blocked until resolved. |

> **Preference rule.** When docs are useful but are not the long-term factory-owned
> output, choose `incorporate`, not `merge`. Never make an in-place update the
> primary action when factory-owned output is the goal.

**Legacy mapping (apply only after the audit has run):**

| Condition | Action |
| --- | --- |
| No guide exists, and audit evidence is `partial`/`missing` with concrete repo evidence | `create` |
| A guide exists and only managed sections need a refresh | `update` |
| No codebase evidence | `skip` (record the reason) |

### Step 4: Gate on evidence quality

> Weak inputs make confident-sounding wrong guidance. Grounding beats coverage.

| Signal | Required behavior |
| --- | --- |
| Rating `weak` | `ask user` or `skip`. Never generate confident guidance from weak docs. |
| Rating `missing` | Generate only from concrete repo evidence; otherwise `skip`. |
| Rating `conflicting` | User picks the authoritative source. `halt` if the conflict touches approval, safety, managed regions, guide source-of-truth, or quality gates. |
| Confidence `low` | Treat as `ask user`, unless the area is skipped. |
| No `file:line` reference | `skip` the category, or request evidence pre-approval. |

Every guide claim traces to concrete evidence in `file:line` form. No reference, no
claim.

### Step 5: Route `project.md` content during planning

`project.md` is special-cased. It is rendered later only per the Project Context
schema defined in `SKILL.md` (Step A, "Project Context schema") — never from a
generic guide template.

While planning, route discovered facts to their owning guide, not into `project.md`:

| Discovered fact | Owning guide |
| --- | --- |
| Git conventions | git workflow guide |
| Commands, task routing | quality gates / entrypoint regions |
| Package ownership | architecture guide |
| Validation-reporting policy | quality gates / tools guide |

### Step 6: Plan entrypoint merges

For each entrypoint target (`CLAUDE.md`, `AGENTS.md`), fill the merge table with the
managed regions you will touch and anything you propose to change outside them.

> Changes outside managed regions are higher-trust edits. Each one needs its own
> explicit approval line in the plan — a blanket "approve" does not cover them.

### Step 7: The approval gate

Present the full rendered plan, then the prompt line, verbatim:

```
Approve / Customize / Cancel?
```

| Choice | Effect |
| --- | --- |
| Approve | Advance to Phase 3. Requires a keyword: "approve", "yes", or "go". |
| Customize | Edit scope, re-render the plan, re-ask. |
| Cancel | Halt. No writes. |

Route this decision through the `decision-router` judgment gate (`plan.approved`) and
record the verdict, with prior context, to `decisions.jsonl` and `events.jsonl`.
Re-check: if any `ask user` item is still open when the keyword arrives, treat the
approval as incomplete — resolve the questions first.

---

## Handoff contract (Phase 2 → Phase 3)

Phase 3 consumes exactly what Phase 2 approved:

- the approved per-scope guide list, with each guide's action;
- the incorporation map and entrypoint merge plan;
- the subagent dispatch plan (monorepo only).

The handoff is blocked while any `ask user` or `halt` item is unresolved. A `halt`
keeps Phases 3–4 closed.

---

## Phase 3 — Generation

### Step 1: Load the craft rules first

Before authoring anything, load `references/knowledge-craft.md`. That file owns
style, structure, size caps, the placeholder contract, the evidence rule, and the
quality bars. This document defers to it on all of them.

### Step 2: Apply the existing-content policy

| State of the target guide | Action |
| --- | --- |
| Absent | Fresh render. |
| Present, user content | Keep the user content. Refresh only stale pieces — commands, dead `file:line` refs, framework versions in headers. |
| Code-drifted | Must carry a Phase-2 `update` action. Never a silent overwrite. |

### Step 3: Single-repo render loop

Run in the main session. Per guide, six steps:

1. Read the template at `references/templates/guides/<category>/<file>.md.template`.
2. Resolve placeholders from Phase-1 discovery and `file:line` references.
3. Strip heavy code blocks while keeping practices and references intact.
4. Write the guide to `.agentic/guides/<category>/<file>.md`.
5. Check the size cap and the quality gates.
6. Never pad short-but-useful content to reach a length target.

### Step 4: Render `project.md` correctly

`project.md` renders only from the Project Context schema in `SKILL.md` (Step A),
never from a guide template under `references/templates/guides/`. Any git convention,
command, task-routing rule, package-ownership fact, or validation-reporting policy
belongs in its owning guide (git workflow / quality gates / entrypoint regions /
architecture / tools), not here.

### Step 5: Monorepo — parallel subagents

> One subagent per module. Dispatch them all in a single message so they run in
> parallel.

- Prefer `superpowers:dispatching-parallel-agents`. If it is absent, make direct
  Agent-tool calls with `subagent_type: "general-purpose"`.
- Give each subagent exactly:
  - the module path;
  - the approved guide list for that module;
  - the per-module stack values (`path | language | framework | build | test`);
  - the template directory path (`references/templates/guides/`);
  - the generation rules path (`references/generation.md` — this document).

Each subagent returns this machine-parsed schema:

```
{ module: <path>, written: [list of file paths], line_counts: { <path>: <int> },
  placeholders_resolved: [list], placeholders_dropped: [list], warnings: [list] }
```

The main session aggregates the returned summaries and forwards them to Phase 5
validation.

### Step 6: Failure recovery

| Failure | Recovery |
| --- | --- |
| Malformed or missing subagent output | Re-dispatch that one module with identical input. |
| Guide over the size cap | Ask the user to drop or condense before Phase 4. |
| Padding or near-duplicate lines | Reject and re-render. |
| Project-level drift written into `project.md` | Relocate it to the owning guide before continuing. |

Phase 4 is gated on size-cap fixes; do not advance past an oversized guide.

---

## Non-goals

- No writes of any kind during Phase 2. Planning is presentation plus approval only.
- No auto-installation of missing host skills.
- No generation from `weak` or evidence-free documentation. No padding to length.
- `project.md` is not a home for project drift or generic guide content.
- No silent overwrites of existing or outdated guides. No bypassing the
  explicit-approval keyword gate.

## Cross-references

- **Upstream:** Phase-1 audit output (the six named sections); `SKILL.md` Step A for
  the `project.md` schema.
- **Sibling:** `references/knowledge-craft.md` (authoring rules);
  `references/templates/guides/` (the template tree).
- **Downstream:** Phase 4 (blocked by size-cap issues); Phase 5 validation (consumes
  the aggregated subagent summaries).
- **Optional host plugins:** the superpowers skill set (brainstorming, parallel
  dispatch) — used when present, never installed.
