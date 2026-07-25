# Engineering principles

`agentic-os` is not a prompt library. Every mechanism below exists because a
specific, observed failure mode in multi-agent coding kept recurring, and
prompting alone did not fix it — the fix had to be structural: a hook that
exits non-zero, a file a machine parses, a score a gate checks. This document
names those mechanisms as first-class ideas, explains the failure each one
closes, and says plainly why a conventional single-agent coding session
(Claude Code, Cursor, Copilot, or any agent framework without an enforcement
layer) doesn't close it on its own.

Each principle links to where it's implemented, not just described — you can
open the hook, the SKILL.md, or the template and read the enforcement, not
take this document's word for it.

> **Reading the paths.** This repository ships the *sources*: hooks under
> `plugins/agentic-os/templates/hooks/claude/` (most are `.tmpl` files rendered
> at install; a few ship verbatim as `.py`), agent contracts under
> `plugins/agentic-os/templates/agents/`. `/agentic-init` installs them into
> *your* repo at `.claude/hooks/` and `.agentic/agents/` respectively. Every
> link below points at the source you can read here; where the installed
> location isn't obvious from that default, it's spelled out as
> `source → installed`.

## 1. Write-scope contracts

**What**: every canonical and generated agent carries a `write_scope` glob and
a `forbidden_paths` glob in its contract. A `PreToolUse` hook checks every
`Write`/`Edit` against them before the tool runs; a violation aborts with a
non-zero exit, not a warning.

**The failure it closes**: in an unconstrained multi-agent setup, scope creep
is silent. An agent asked to write a migration "helpfully" also touches a
component file, or a review agent edits the code it was supposed to only
critique. Nothing stops it, because nothing *can* — the boundary exists only
in the prompt's wording, which the model can (and does) deprioritize under
pressure to finish the task.

**Why a plain session doesn't have this**: a single Claude Code or Cursor
session has one tool surface with no per-task boundary. You can *ask* the
agent to stay in one directory; nothing enforces it if it decides otherwise.

**Implementation**:
[`templates/hooks/claude/write_scope_guard.py.tmpl`](../plugins/agentic-os/templates/hooks/claude/write_scope_guard.py.tmpl)
→ installed as `.claude/hooks/write_scope_guard.py`; the
`write_scope`/`forbidden_paths` fields are declared in every agent contract
template under
[`templates/agents/`](../plugins/agentic-os/templates/agents/) → installed to
`.agentic/agents/`.

## 2. Blind pre-commit review

**What**: before every commit, a review subagent reads the exact staged diff
(`git diff --cached`) cold — no chat history, no access to the implementer's
reasoning, only a one-paragraph functional brief of what the change should
do. The approval is a sha256 stamp of that exact diff; re-staging invalidates
it and forces a fresh review.

**The failure it closes**: an agent that reviews its own work (or is handed
its own reasoning transcript) tends to confirm what it already decided —
gaps get rationalized away because the reviewer already believes the
narrative that justified them. A reviewer with zero access to that narrative
has nothing to rationalize with; it only has the diff.

**Why a plain session doesn't have this**: "self-review" in most agent
workflows is the same context window checking its own output, or a second
pass that still inherits the first pass's framing. Few coding-agent setups
spawn a genuinely blind second opinion, and fewer still gate the commit on it
at the tool level.

**Implementation**: the
[`blind-code-reviewer`](../plugins/agentic-os/templates/agents/core/blind-code-reviewer.md.tmpl)
agent contract; the `PreToolUse(Bash)` review-gate hook
[`precommit_review_gate.py`](../plugins/agentic-os/templates/hooks/claude/precommit_review_gate.py)
→ installed as `.claude/hooks/precommit_review_gate.py`, plus its git-level twin
[`templates/githooks/pre-commit`](../plugins/agentic-os/templates/githooks/pre-commit)
→ installed as `.githooks/pre-commit`, so the gate holds even outside the
harness that spawned the review.

## 3. The decision-router — autonomy as a resolution strategy, not a toggle

**What**: every judgment gate (spec approval, code review, QA drift, feature
verification) resolves through the same four-step state machine: HITL mode
short-circuits straight to a human question; otherwise a cheap deterministic
check runs first (does the evidence have the right shape at all); then a
fast-path for low-risk preconditions; only then a stand-in subagent verdict.
Any step can still escalate to a human on low confidence or a matching risk
flag. Every resolution — including which step answered it — is written to
`decisions.jsonl`.

**The failure it closes**: "autonomous mode" in most agent frameworks is
binary — the agent either asks you or it doesn't, uniformly, for every gate.
That forces a bad tradeoff: strict enough to be safe on the risky gates means
being needlessly interrupted on the routine ones, or loose enough to move
fast means the risky gates get the same rubber stamp as the routine ones.

**Why a plain session doesn't have this**: there's no per-gate resolution
strategy in a standard agent loop, and no audit trail of *why* a given
decision wasn't escalated — you can't reconstruct, after the fact, whether a
merge went through because a human approved it, a deterministic check passed,
or a subagent guessed.

**Implementation**:
[`skills/decision-router/SKILL.md`](../plugins/agentic-sdlc/skills/decision-router/SKILL.md);
the state machine is diagrammed in
[`plugins/agentic-sdlc/README.md`](../plugins/agentic-sdlc/README.md#decision-router-autonomous-gates).

## 4. The HITL escalation ladder

**What**: every agent's output must resolve into the same fixed severity
ladder — hard hook denial (a tool call physically refused) → `## Blocking`
→ `## Non-blocking` → `## Escalate to human` — and a `Stop`/`SubagentStop`
hook parses that structure fail-closed: a non-empty `Blocking` section stops
the parent outright (no silent retry, no "I'll just proceed"); a non-empty
`Escalate to human` section forces an `AskUserQuestion` before anything else
runs.

**The failure it closes**: "flagging a concern" is usually a sentence buried
in prose, and whether the parent agent (or the human) actually notices and
acts on it is a matter of luck and prompt discipline. A structural contract
every agent must conform to — parsed by code, not inferred by another
model — makes escalation mechanical instead of hopeful.

**Why a plain session doesn't have this**: a normal agent response is free
text. Nothing forces a specific severity taxonomy, and nothing automatically
halts the parent when a sub-step raises something serious — the calling
context has to notice on its own.

**Implementation**:
[`templates/hooks/claude/subagent_gate.py.tmpl`](../plugins/agentic-os/templates/hooks/claude/subagent_gate.py.tmpl)
→ installed as `.claude/hooks/subagent_gate.py`; every agent contract template
ends with the same five-section output contract; the ladder itself is codified
in
[`templates/policy/escalation-policy.md.tmpl`](../plugins/agentic-os/templates/policy/escalation-policy.md.tmpl)
→ installed to `.agentic/guides/policy/escalation-policy.md`.

## 5. Evidence-grounded repository discovery

**What**: stack facts (persistence paradigm, API style, UI framework, i18n
presence) are derived with a `file:line` citation and a 0–100 confidence per
fact, not asserted. Below a confidence threshold, the fact is surfaced to the
human at the interview instead of guessed. Discovered facts are explicitly
labeled **unverified hints** in every downstream generator prompt — a
generator must re-derive and re-cite each fact against the live repository,
and a rule may never cite the discovery record itself as its evidence. An
instruction-quality rubric check enforces the second half of that rule
mechanically.

**The failure it closes**: the single most common failure observed while
building this program's non-curated-stack support was **vocabulary
transplant** — a generated agent contract for a MongoDB service quietly
inheriting Postgres/RLS language from the curated exemplar it was shown, or a
generated contract citing an installer-internal field name as if it were a
fact about the target repository. Prompting an agent to "be careful" about
this did not reliably prevent it; grounding every fact in a citable location
and mechanically rejecting rules that cite the wrong source did (see
[`tests/universal/README.md`](../tests/universal/README.md) for the golden
runs, including one case where this exact check caught a live violation
during testing, not in theory).

**Why a plain session doesn't have this**: a single agent session re-derives
"what stack is this" informally every time, with no confidence scoring, no
enforced provenance, and no mechanism stopping it from generalizing from a
similar-looking example it saw in training or in a shared exemplar.

**Implementation**:
[`generators/stack-discovery.md`](../plugins/agentic-os/generators/stack-discovery.md);
the "evidence guarantee" rule embedded in
[`agent-generator.md`](../plugins/agentic-os/generators/agent-generator.md)
and
[`guide-generator.md`](../plugins/agentic-os/generators/guide-generator.md);
the discovery-record-citation check in
[`templates/guides/standards/instruction-quality-rubric.md`](../plugins/agentic-os/templates/guides/standards/instruction-quality-rubric.md)
→ installed to `.agentic/guides/standards/`.

## 6. Generated agent contracts as audited build artifacts

**What**: stack-specific agent contracts (schema-architect, api-author,
component-generator, migration-validator, i18n-agent) aren't hand-written
once and left to drift. They're generated per repository by an LLM subagent
from a paradigm-neutral exemplar plus real, cited repo evidence, then
independently audited by a separate `instruction-auditor` subagent against a
scored, evidence-accuracy rubric. The score and the content hash both land in
`docs/audits/instruction-scorecard.json`; a `SubagentStart` hook hard-blocks
that agent's spawn if its cited guides' content hash no longer matches what
was graded.

**The failure it closes**: hand-maintained system prompts silently rot as the
codebase they describe changes underneath them — a rule that was true at
authoring time becomes false, and nothing notices. Treating a generated
contract as a graded, hash-pinned artifact means staleness is a hard block,
not a slow accumulation of wrong claims nobody catches until an agent acts on
one.

**Why a plain session doesn't have this**: custom instructions/system prompts
in most tools are static text with no freshness check and no independent
verification step before they're trusted.

**Implementation**:
[`generators/agent-generator.md`](../plugins/agentic-os/generators/agent-generator.md),
[`generators/guide-generator.md`](../plugins/agentic-os/generators/guide-generator.md),
and
[`templates/hooks/claude/instruction_gate.py.tmpl`](../plugins/agentic-os/templates/hooks/claude/instruction_gate.py.tmpl)
→ installed as `.claude/hooks/instruction_gate.py` (the hook reads the
scorecard and exits 2; it does not grade). The independent grader is the
[`instruction-auditor`](../plugins/agentic-os/templates/agents/core/instruction-auditor.md.tmpl)
contract, and the rubric it grades against is
[`templates/guides/standards/instruction-quality-rubric.md`](../plugins/agentic-os/templates/guides/standards/instruction-quality-rubric.md)
→ installed to `.agentic/guides/standards/`.

## 7. The agent registry — one routing matrix, not scattered dispatch logic

**What**: which agent owns which intent lives in exactly one place — a single
markdown table, `.agentic/guides/agent-registry.md` — that orchestrators read
at runtime instead of encoding dispatch rules in code. It's a hybrid file: a
static, curated upper section plus a section machine-appended at generation
time for stack-specific agents, reconciled specially (not blindly
overwritten) on every `/agentic-upgrade`.

**The failure it closes**: routing/dispatch logic embedded in orchestrator
prompts or code is invisible to a reviewer and easy to fork accidentally (two
code paths quietly deciding "who handles X" differently). A single table is
diff-reviewable, human-editable, and has exactly one row per intent by
construction.

**Why a plain session doesn't have this**: there's usually no registry at
all — routing is whatever the current prompt's ad hoc judgment produces, and
it isn't visible or auditable independent of a specific run's output.

**Implementation**:
[`templates/governance/agent-registry.md.tmpl`](../plugins/agentic-os/templates/governance/agent-registry.md.tmpl)
→ installed to `.agentic/guides/agent-registry.md`; the
orchestrator-appends-rows logic in
[`skills/agentic-init/SKILL.md`](../plugins/agentic-os/skills/agentic-init/SKILL.md)
Phase 5 and the split-reconcile logic in
[`skills/agentic-upgrade/SKILL.md`](../plugins/agentic-os/skills/agentic-upgrade/SKILL.md).

---

None of these are pure prompting tricks — each has a hook that exits
non-zero, a file a machine parses and re-verifies, or a score a gate checks.
That's the deliberate bet this project makes: governance for coding agents
has to be enforced the way any other production system is enforced, not
requested in prose and hoped for.
