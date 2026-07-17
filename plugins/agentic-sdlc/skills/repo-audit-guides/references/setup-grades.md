# Setup grades: one graded exemplar catalog

Reference for the `repo-audit-guides` skill. Classify a repository's documentation and
AI-assistant configuration into three grades — **strong**, **partial**, **weak** — before
knowledge planting decides whether existing material stays authoritative. This file merges the
three grade tiers into a single comparative catalog so you rate against one shared vocabulary
instead of three separate rubrics.

You are the reader. You emit per-dimension ratings and one recommendation verb per archetype you
match. You do not edit files. Auditing is read-only (R0); the writes live downstream in
planting / the foundation flow (R2), always behind the **foundation entrypoint merge gate**.

> Grade meanings. **Strong** = specific, current, internally consistent, safe for planting to
> preserve. **Partial** = holds real value but needs reconciliation or a user decision about
> whether existing docs remain the source of truth. **Weak** = stale, conflicting, boilerplate,
> or unsafe; planting must not consume it without confirmation, replacement, or a stop.

---

## How to read this catalog

Every archetype is scored on the same nine dimensions, using the same value enum, and resolves to
one verb.

**Rating dimensions** (exact output labels):
`Completeness`, `Correctness`, `Freshness`, `Specificity`, `Consistency`,
`Assistant compatibility`, `Agentic setup quality`, `Skill and subagent quality`,
`Planting readiness`

**Rating values** (enum): `strong` | `partial` | `weak` | `missing` | `conflicting`

**Planting recommendation verbs** (enum):
`preserve` | `merge` | `incorporate` | `replace` | `ask user` | `skip` | `halt`

**Probe set** — the files and dirs you inspect to gather signal:
`README.md`, `CONTRIBUTING.md`, `docs/development.md`, `docs/architecture.md`,
`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.claude/`, `.codex/`, `.agents/`,
`package.json`, `Makefile`, `pyproject.toml`

> Assume multi-host detection. `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.claude/`, `.codex/`, and
> `.agents/` are how you tell which assistant surfaces exist (Claude Code, Codex-style,
> Gemini-style). Absence of all of them is itself a signal, not an error.

---

## Shared dimension table

What each dimension measures, and what `strong` versus `weak` looks like on it. Use this to turn
observations into the value enum.

| Dimension | Reads `strong` when | Reads `weak` when |
|---|---|---|
| `Completeness` | Docs plus assistant surfaces cover the workflow: setup, build, test, run, gates | README is a stub; lint/type-check/test commands or CI gates go undocumented |
| `Correctness` | Documented commands and paths resolve against `package.json` / `Makefile` / `pyproject.toml` / CI and the tree | Commands fail, paths 404, imports name removed modules |
| `Freshness` | Docs reflect current packages, dirs, and architecture | Docs reference deleted dirs, old package names, a prior product |
| `Specificity` | Guidance is concrete to this repo — real commands, real files | Generic boilerplate that would fit any project |
| `Consistency` | Test/lint/format/type-check commands identical, same order, across entrypoints, docs, and CI | Commands disagree between surfaces; instructions tell agents to skip gates |
| `Assistant compatibility` | Entrypoint is concise, delegates detail to guides, names critical rules/gates/approval expectations, does not present host-specific slash commands as universal | Monolithic dump, or one host's slash commands passed off as universal |
| `Agentic setup quality` | Managed regions use start/end markers, separate generated from human content, references resolve | Markers missing, generated and hand-written content tangled, refs stale |
| `Skill and subagent quality` | Concise frontmatter + trigger text, progressive disclosure into references, bounded ownership, explicit verification, evals or pressure scenarios on important assets | Missing gates, branch rules, or ownership; no verification; no evals |
| `Planting readiness` | Planting can preserve or make a small merge without a human in the loop | Requires user confirmation, replacement, or a hard stop before consumption |

> Grounding rule that cuts across every dimension: evidence must resolve. Docs and commands match
> manifests; paths exist; agentic assets cite real repo files. An unverifiable claim never rates
> `strong` no matter how well written.
>
> No arithmetic. Dimensions are independent labels — do not average, weight, or roll them into a
> single score. Report the per-dimension values and let the dominant ones drive the verb.

---

## Grade A — Strong (preservable)

Archetypes safe for planting to keep as-is, or to let the foundation own going forward. Default
verb is `preserve`; escalate to `incorporate` when the foundation should own future guidance, or
`merge` for a small, additive gap closed through the gate.

| Archetype | Observable signals | Dominant ratings | Verb |
|---|---|---|---|
| Full docs + resolving commands | README/CONTRIBUTING/`docs/development.md` complete; every command runs against the manifests and CI | `Completeness` `strong`, `Correctness` `strong`, `Freshness` `strong` | `preserve` / `incorporate` |
| Proper delegating entrypoint | Concise `AGENTS.md`/`CLAUDE.md` names rules, gates, approval expectations, and delegates detail to guide files | `Assistant compatibility` `strong`, `Consistency` `strong` | `preserve`; `merge` via gate |
| Healthy managed regions | Managed-region start and end markers present, generated vs human content separated, references resolve | `Agentic setup quality` `strong` | `preserve`; gate-only updates |
| Evidenced skills/subagents | Skills/subagents carry tight frontmatter, progressive disclosure, bounded ownership, verification, and evals or pressure scenarios | `Completeness` `strong`, `Skill and subagent quality` `strong` | `preserve` or small `merge` |
| Consistent gate commands | Test/lint/format/type-check commands identical and same-ordered across entrypoints, docs, and CI; no "skip the gate" language | `Correctness` `strong`, `Consistency` `strong` | `preserve` |

> `preserve` vs `incorporate`: preserve when the existing doc should stay the source of truth;
> incorporate when the material is good but the foundation should own the future version of it.
> `merge` only closes a small additive gap and still routes through the foundation entrypoint
> merge gate with a diff shown.

---

## Grade B — Partial (usable, needs reconciliation)

Real source material, but you cannot fully clear it without a reconciliation step or a user
decision on authority. Default verbs are `merge` (after approval) and `ask user`.

| Archetype | Observable signals | Dominant ratings | Verb |
|---|---|---|---|
| Docs missing commands | Docs exist and read well but omit lint/type-check/test commands, or CI gates are undocumented | `Completeness` `partial`, `Correctness` `partial` | `merge` after approval |
| Non-delegating entrypoint | Entrypoint is useful but monolithic — carries detail inline instead of pointing to guide files | `Assistant compatibility` `partial`, `Agentic setup quality` `partial`/`missing` | `preserve` critical rules, gated `merge` of guide refs |
| Thin agentic coverage | Skills/subagents present but miss gates, branch rules, or ownership; settings not inferable from the tree | `Skill and subagent quality` `partial`, `Completeness` `partial` | `merge` missing guidance; `ask user` for non-inferable settings |
| Stale managed regions | Markers present but the paths or commands inside them have drifted from the tree | `Freshness` `partial`/`weak`, `Consistency` `partial` | `merge` or `replace` — only after a diff in a later foundation run |
| Mixed assistant surfaces | Two entrypoints mostly agree, or `.claude/`/`.codex/`/`.agents/` dirs are unreferenced; no stated priority | `Assistant compatibility` `partial`, `Consistency` `partial` | `ask user` which surface is authoritative |

> Merge manifest-backed commands rather than inventing them: pull the real command from
> `package.json` / `Makefile` / `pyproject.toml` and propose that, gated. For a monolithic
> entrypoint, preserve the critical rules now and defer the guide-reference restructuring to a
> gated merge — don't rewrite human-authored rules to make it delegate. When two surfaces both
> look authoritative, resolve authority with `ask user` before merging either.

---

## Grade C — Weak (replace, confirm, or stop)

States planting must not consume as-is. Verbs escalate `replace` → `ask user` → `halt` as
confidence in a safe automatic fix drops and as risk to human-authored or safety content rises.

| Archetype | Observable signals | Dominant ratings | Verb |
|---|---|---|---|
| Boilerplate docs | README is template text; docs carry no commands; `docs/architecture.md` describes a different product; dead paths | `Completeness` `weak`, `Specificity` `weak`, `Freshness` `weak` | `replace` with evidence-backed guidance; `ask user` if evidence is thin |
| No assistant surfaces | None of `AGENTS.md`/`CLAUDE.md`/`GEMINI.md`/`.claude/`/`.codex/`/`.agents/` exist | `Assistant compatibility` `missing`, `Agentic setup quality` `missing` | `skip` entrypoint assessment; planting proposes a target file later |
| Stale entrypoint | Entrypoint references removed dirs, old packages, or missing imports | `Correctness` `weak`, `Freshness` `weak` | `replace` managed content; `ask user` before touching human-authored rules |
| Parallel authorities | Competing entrypoints / commands / skills / subagents claim authority for one workflow with no priority | `Agentic setup quality` `conflicting`, `Consistency` `conflicting` | `ask user` or `halt` |
| Unsafe instructions | Guidance says to bypass approvals, run destructive git by default, ignore dirty trees, or auto-install tools | `Correctness` `conflicting`, `Planting readiness` `conflicting` | `halt` until the user resolves |

> `skip` is not a failure — with no assistant surfaces there is simply nothing to assess yet;
> planting will propose a target entrypoint downstream. Guard the boundary between generated and
> human content: `replace` the managed region, but `ask user` before rewriting hand-authored
> rules. Unsafe instructions always `halt` — never let planting inherit a bypass-approvals or
> destructive-by-default instruction, regardless of how the surrounding doc is framed.

---

## Verb selection — quick reference

Collapse the catalog to a decision order when an archetype is ambiguous:

| If the state is… | Verb |
|---|---|
| Complete, correct, current, consistent | `preserve` |
| Good, but the foundation should own the future version | `incorporate` |
| Sound with a small, evidence-backed additive gap | `merge` (gated, diff shown) |
| Non-inferable setting, unclear authority, or thin evidence | `ask user` |
| Boilerplate, stale, or wrong-product content with clear evidence for a fix | `replace` (gated, diff shown) |
| No assistant surface to assess | `skip` |
| Competing authorities, or unsafe instructions | `halt` (or `ask user` for authority conflicts) |

> Any `merge` or `replace` of a managed region happens only in a later foundation run, through
> the foundation entrypoint merge gate, with the diff shown before the change lands. The auditor
> never performs the change — it names the verb.

---

## Boundaries

- This is a classification rubric, not a how-to for writing docs, skills, or subagents.
- The auditor recommends a verb; it does not plant, merge, replace, or edit any file.
- Command checking is limited to confirming documented commands match the manifests — no CI or
  platform-runner specifics beyond that.
- Ratings are per-dimension labels only. There is no scoring arithmetic and no weighting between
  dimensions.
