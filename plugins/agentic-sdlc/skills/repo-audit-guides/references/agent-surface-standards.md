# Agent-surface standards: entrypoint files, skills, and subagents

Assessment criteria for the `repo-audit-guides` skill. Apply these when judging whether a
repository's agentic-assistant configuration is healthy **before** knowledge planting (writing
generated guidance into the repo). This is a scoring-free reference: no weights, no numeric
thresholds — you produce judgments and, where authority is unclear, escalate.

> These criteria are deliberately **not frozen**. They track the repo's agent platform and are
> expected to drift as hosts add or drop surfaces. Treat a rule that no longer matches the host as
> a gap in this reference, not evidence against the repo.

## Cross-cutting principles

Apply these to every surface below.

- **Vendor-neutral by default.** State criteria so they hold across hosts. Any host-specific rule
  must be labeled with the host it applies to and must never be presented as universal. Hosts you
  may encounter: Claude, Codex, Gemini, GitHub Copilot (and Cursor, present via its config
  directory).
- **Grounding.** A surface must not assert repo state it did not check. Flag anything that assumes
  a branch model, test runner, CI gate, or directory exists without reading evidence for it.
- **Point, don't duplicate.** Authoritative procedure lives in one place; other surfaces reference
  it. Inlined copies rot independently and become a source of cross-surface conflict.
- **No covert authority.** No surface may silently override repo standards or stand in for a
  human decision that a gate owns.

---

## Surface 1 — Entrypoint / context files

Files audited (exact names):

| File | Host association |
|------|------------------|
| `AGENTS.md` | cross-host / generic |
| `CLAUDE.md` | Claude |
| `GEMINI.md` | Gemini |
| `.github/copilot-instructions.md` | GitHub Copilot |

Criteria:

- **Short and scoped.** The entrypoint orients an agent and links out. It is not a manual. If it
  restates full procedures that already live in authoritative docs, that is the
  *duplicative long entrypoint* anti-pattern.
- **Expectations made explicit.** The file must state, or link to a doc that states, four things:
  - **Approval** — which actions need human sign-off before proceeding.
  - **Write-safety** — what the agent may modify and what is off-limits.
  - **Branch-safety** — the branch/commit policy (e.g., never commit to the default branch).
  - **Verification** — how the agent confirms work before claiming completion.
- **Machine-managed regions stay intact.** If a region is generated/managed, its start and end
  markers must both be present and well-formed. Generated text must occupy that region only —
  never interleaved line-by-line with human-authored policy. Flag missing, orphaned, or nested
  markers, and any human policy trapped inside a managed block.
- **No rival source of truth.** See *Authority assessment* below; an entrypoint that contradicts
  another surface or the repo's own docs is a cross-surface conflict.

---

## Surface 2 — Tool config directories

Directories audited (exact names):

`.claude/` · `.codex/` · `.agents/` · `.gemini/` · `.copilot/` · `.cursor/` · `.github/`

Criteria:

- **Only reachable assets.** Every asset in the directory should be referenced by an entrypoint,
  discoverable by the host's own convention, or otherwise wired in. Orphan files that nothing
  loads are noise — flag them.
- **Commands match real workflows.** Command/slash-command definitions must map to workflows that
  actually exist in the repo. Do not assume a host supports slash commands: flag command assets
  that presume a mechanism the host lacks, and flag commands describing steps the repo no longer
  runs (stale).
- **Hooks and settings are minimal and legible.** Each hook or setting states its purpose. No
  hidden writes, no destructive defaults, no side effects an agent would not expect from reading
  the config.
- **Memory/profile files do not silently override repo standards.** Per-user or per-agent memory
  must not quietly contradict the repo's committed policy. If it does, that override must be
  visible and intentional, not buried.
- **Adapter-driven integrations.** Ticket/MR/review backends are not hardcoded into assets;
  integration adapters live under `.agentic/guides/`. Flag any surface that hardcodes a specific
  source-control or tracker backend instead of reading the adapter.

---

## Surface 3 — Skills

Structure contract (verbatim): a skill has frontmatter with fields `name` and `description`; its
body lives in `SKILL.md`; reference files sit **exactly one level deep** from `SKILL.md`.

Criteria:

- **Frontmatter that triggers correctly.** `name` is specific (not a placeholder). `description`
  is discovery-oriented: it names concrete triggers — the phrases, tasks, or file patterns that
  should invoke the skill — not a vague topic label.
- **Concise main file, progressive disclosure.** `SKILL.md` carries the core path and defers
  detail to references. It should not front-load everything a rare branch might need.
- **References one level deep.** No reference-of-a-reference chains; a reader reaches any support
  file in one hop from `SKILL.md`. Flag deeper nesting.
- **No stale or model-known filler.** Cut time-sensitive content that will age out, and cut
  generalities a competent model already knows. A skill earns its tokens by carrying
  repo-specific or non-obvious knowledge.
- **Freedom calibrated to fragility.** Prescribe tightly where a wrong move is costly or
  irreversible; leave latitude where the task is robust and exploratory. A skill that over-scripts
  a safe task, or under-specifies a dangerous one, is miscalibrated.
- **Evals for important behavior.** Behavior that matters should be pinned by evals or pressure
  prompts, so regressions surface. Flag high-stakes skills with no such checks.

---

## Surface 4 — Subagents (and commands / reusable prompts)

Criteria:

- **Single responsibility.** One subagent, one job. A subagent that spans requirements *and*
  implementation *and* review is doing too much to reason about or bound.
- **Bounded read/write scope.** State what the subagent may touch, sized by blast radius:

  | Tag | Meaning |
  |-----|---------|
  | `R0` | read-only |
  | `R1` | writes run artifacts only |
  | `R2` | writes repo files |
  | `R3` | external side-effects (must sit behind a gate) |

  A subagent with unbounded write scope, or one that reverts unrelated changes, is an anti-pattern.
- **Explicit I/O and no-touch list.** The prompt states the inputs to inspect, the outputs to
  produce, and what must stay untouched. Prefer a structured return/verdict schema over free prose
  so callers can act on the result deterministically.
- **Verification tied to repo commands.** The subagent's "done" is defined by commands the repo
  actually runs (lint/build/test), not by self-assertion.
- **Parallel agents are coordinated.** Concurrent subagents need disjoint ownership or an explicit
  coordination rule; overlapping write scopes are a conflict waiting to happen.
- **Never a covert approval bypass.** A subagent must not stand in for a human-in-the-loop
  decision gate. Judgment gates route through the decision-router and, when authority is unclear,
  escalate; a subagent that auto-approves what a gate should hold — e.g. `spec.approved`,
  `plan.approved`, `qa.drift`, `code-review.final`, `requirements.ambiguous` — defeats the gate.
  Flag it.

---

## Authority assessment (gates the planting step)

Before planting, decide **which surface is authoritative** for each domain below. The winning
surface is the one an agent should obey when surfaces disagree.

| # | Domain |
|---|--------|
| 1 | project overview |
| 2 | quality gates |
| 3 | branch and commit policy |
| 4 | approval and review expectations |
| 5 | agent-specific commands |
| 6 | skill/subagent usage |

Rules:

- **Ambiguous authority → escalate.** If no single surface clearly owns a domain, or two surfaces
  claim it and conflict, the recommended action is the verdict string `ask user` before planting
  knowledge into that domain.
- **No rival source of truth vs the pipeline.** Other agentic assets must not claim to own
  **requirements**, **implementation gates**, **review gates**, or **knowledge guides** in
  competition with the `agentic-sdlc` pipeline — unless the user explicitly chose that setup. A
  surface that quietly reroutes any of these four domains away from the pipeline is a finding, not
  a preference.

> Authority assessment is the gate on planting. Resolve or escalate it first; a plant into a
> domain with contested ownership writes generated guidance on top of an unsettled contract.

---

## Anti-pattern quick list

Flag these on sight:

| Anti-pattern | What it looks like |
|--------------|--------------------|
| Vague asset names | skills/subagents/commands named `helper`, `misc`, `general` — nothing about the name aids discovery |
| Duplicative long entrypoints | an entrypoint that inlines every reference instead of pointing to it |
| Evidence-free state assumptions | a skill or prompt that assumes repo state (branch model, runner, CI) without checking |
| Unbounded subagent writes | a subagent with no write-scope limit, or one that reverts unrelated changes |
| Cross-surface conflicts | contradictions among skills, subagents, entrypoints, and repo docs |

---

## Scope notes

- This is assessment criteria, not a how-to for authoring entrypoints, skills, or subagents.
- It defines no scoring rubric, weights, or numeric thresholds.
- It governs assistant surfaces only; it does not prescribe repo doc structure elsewhere and
  mandates no specific host or vendor.
