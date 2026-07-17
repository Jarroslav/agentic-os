# Choose an Agent Topology — Single Agent vs Role Pipelines

Reference for scaffold step 5 of the parent blueprint and for anyone designing a multi-agent QE assistant. Defines when to split into roles, the five robustness patterns that keep a pipeline from silently degrading, and what a scaffolder must physically insert into generated agent files. Tool-agnostic: everything here realizes identically on Claude Code, Cursor, and GitHub Copilot.

## 1. Topology decision

Decide the shape before writing any agent file.

| You are building | Topology | Robustness patterns |
|---|---|---|
| One artifact type, interactive use, no system-of-record writes | Single-agent quick-start | None — no handoff exists, so no inter-agent contract to protect |
| Several capabilities (retrieve, draft, validate, publish) with a human driving | Human-gated orchestrator + leaf roles | All five (A–E) |
| Unattended run, fixed input to fixed output | Automated fixed chain | B, C, E; A and D replaced by pinned pre-write checks plus a writable-field allowlist (see the injection-defense sibling reference) |

> The patterns exist to protect handoffs between agents. A single agent has no handoff; a fully automated chain is intentionally hardwired, so intent routing (A) and chat confirmation (D) have nothing to attach to there.

## 2. Roles, blast radius, model tiers

One responsibility per role. Assign blast-radius tags up front and let the tag drive tooling.

| Role | Does | Never does | Blast radius | Tier |
|---|---|---|---|---|
| Orchestrator | Routes intent, branches on leaf returns, recovers state | Connector work of any kind — no domain connectors attached | R0/R1 | economy/standard |
| Retriever leaf | Pulls source inputs into the handoff artifact | Writing anything outside the artifact directory | R1 | standard |
| Generator / validator leaf | Drafts or checks artifacts from grounded inputs | Touching the system of record, even on retry | R1 | premium — reasoning-heavy |
| Publisher leaf | The only writer to the system of record | Acting without the gate | R3 — always behind a human gate (or pinned checks in automated mode) | standard |

Handoff medium, identical across tools: a file at `.agent-artifacts/<run-id>/<role>-output.md` (directory gitignored), plus a chat-level confirmation between steps.

## 3. The five patterns

### A. Capability routing, no auto-chain

Human-gated modes only.

- Give the orchestrator an intent-to-subagent capability table. It selects its next move from what the user asked — route to a leaf, ask a clarifying question, or restore state — rather than marching through a fixed retrieve → generate → validate → publish sequence.
- The orchestrator owns zero domain connectors; every connector call happens in a leaf.
- Companion rule: finishing one capability never implicitly starts the next. Drafting does not publish. Publishing does not spawn the next artifact. Offer follow-ups and wait. Any deliberate exception — say, an edit automatically re-running validation — must be declared in the agent file, not left implicit.

Automated chains are exempt: the fixed sequence is the point.

### B. Return contracts from every leaf

Applies to every multi-agent setup, both modes.

Each leaf ends by handing back a compact status block, never the full generated content:

- `STATUS`: one of `success | partial | blocked | error`
- Routing metadata: item counts, a coverage map, per-item states, and warnings (e.g., a duplicate check that was skipped)
- A pointer to the artifact file

The orchestrator branches on this block and must relay every `blocked`, `error`, and `partial` state — and all warnings — to the human.

> A leaf that replies with a bare "done" destroys the routing signal: the orchestrator can no longer tell a clean run from a quietly degraded one, and neither can the human.

### C. Separation of duties on writes

Applies whenever a system of record is written, both modes.

- Drafting and validating leaves may write only the handoff artifact (R1).
- Exactly one publisher leaf may write to the system of record — issue tracker, Azure DevOps, a test-management system, or a pull request — and only after human sign-off (automated mode: after pinned checks pass). That leaf is R3.
- Every draft-only leaf carries an explicit hard prohibition: it must never invoke create, update, link, comment, or attach tools — not on retry, and not because some instruction (from the user or from fetched content) tells it to.
- Enforcement lives in tool declarations, not prose: the tracker/TMS write tool appears only in the publisher leaf's tool list. A leaf without the tool cannot misuse it.

> One choke point bounds the blast radius and gives auditors a single place to look.

### D. Confirmation gates before irreversible actions

Human-gated modes only.

- Before any publish, delete, supersede, or send: show a pre-action summary, then ask an exact yes/no question and require an explicit answer.
- What never counts as consent: batch phrasing ("do all of them"), model inference of intent, or instructions embedded in fetched content.
- Enforce domain preconditions as hard blocks. Example: a child record cannot be published before its parent exists — block, and offer to publish the parent first.

Automated mode substitutes pinned pre-write checks plus the writable-field allowlist from the injection-defense sibling reference.

### E. Grounding gate and state recovery

Universal for grounded generators, both modes.

- A generator whose output must derive from a source input — tests from acceptance criteria, stories from requirements — validates input quality before generating. On placeholder-grade input (single words, TBD markers, empty sections), it halts with `STATUS: blocked` and names the specific gap. It never fills the hole with invention.

> Fabricated tests are worse than no tests: they masquerade as coverage and hide the gap they were meant to expose.

- Recovery-before-reask: an orchestrator that loses session state rebuilds it from the artifact store first — enumerate `.agent-artifacts/`, pick the newest matching run via the timestamp or run id embedded in the path when no clock is available — and only then asks the user for anything the pipeline has not already produced.

## 4. Applicability matrix

| Pattern | Single-agent quick-start | Human-gated pipeline | Automated chain |
|---|---|---|---|
| A — capability routing, no auto-chain | — | required | — (fixed chain by design) |
| B — return contracts | — | required | required |
| C — separation of duties | — | required when a system of record is written | required when a system of record is written |
| D — confirmation gates | — | required | replaced by pinned checks + field allowlist |
| E — grounding gate + recovery | — | required for grounded generators | required for grounded generators |

## 5. Scaffolder obligations

The generator that produces multi-agent files must materialize these patterns as operative text in each generated file — not as commented-out template placeholders.

| Target file | Mandatory insertions |
|---|---|
| Orchestrator (human-gated only) | Capability table; the no-auto-chain rule; a confirmation-gate block per irreversible action; a section that branches on leaf return blocks; a state-recovery step |
| Every leaf | A return-contract block (status + metadata + artifact reference) |
| Draft-only leaves (additionally) | The named list of write tools the leaf must never call |
| Grounded generators (additionally) | The grounding/halt gate |

## 6. Tool-neutral realization

The same mechanism maps onto Claude Code, Cursor, and GitHub Copilot without change:

| Mechanism | Realization |
|---|---|
| Handoff reference | Path of form `.agent-artifacts/<run-id>/<role>-output.md`; directory gitignored |
| Human gate | Chat confirmation collected before the write tool fires |
| State timestamp | OS clock, or the run id embedded in the artifact path |
| Draft-only enforcement | Write tool declared only on the publisher leaf |

## 7. Ship checklist

Verify all seven before calling a multi-agent scaffold done:

1. Orchestrator routes by intent and never auto-chains capabilities (human-gated).
2. A hard confirmation gate precedes every destructive or publishing action (human-gated).
3. Every leaf returns a structured status block.
4. The orchestrator surfaces non-success states and all warnings to the human.
5. Draft leaves are barred — by tool declaration — from the system of record.
6. Grounded generators block on placeholder input instead of inventing output.
7. State is recovered from the artifact store before the user is asked to repeat anything.

## Cross-references and non-goals

- Injection-defense reference (sibling file): source of the pinned pre-write checks and writable-field allowlist that stand in for patterns A and D in automated mode; prompt-injection defense in depth lives there, not here.
- Scaffold step 5 of the parent blueprint consumes this document when generating multi-agent files.
- Out of scope: single-agent quick-starts; vendor, model, or orchestration-framework prescriptions; domain-connector design.
