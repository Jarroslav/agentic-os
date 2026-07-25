# Design-Review Checklists for QE Agent Setups

Binary gate criteria for agent-harness design. Every item is pass/fail — an unchecked box blocks the gate it belongs to. Concepts (autonomy tiers, blast radius classes, draft/commit, compaction, goal loops) are defined in the sibling agent-design references; this file only operationalizes them.

Blast radius tags used throughout:

| Tag | Meaning |
|-----|---------|
| R0 | Read-only |
| R1 | Writes run artifacts only |
| R2 | Writes repository files |
| R3 | External side effects — always behind a human gate |

## Hard Rules

Apply these at every gate. They override any checklist interpretation.

| # | Rule |
|---|------|
| 1 | Choose the lowest autonomy tier that still delivers value; raise it only on evidence. |
| 2 | Every risky action passes a draft stage that is distinct from its commit stage. |
| 3 | Approval authority lives outside the model. The model never approves its own actions. |
| 4 | Destructive capability is deny-by-default; turning it on requires a human gate plus a written recovery plan. |
| 5 | Goal-style autonomous loops are added only after the base agent passes its eval suite. |
| 6 | Subagents are added only when decomposition measurably improves outcomes. |
| 7 | Each production incident produces a new regression eval. |
| 8 | Guidance you keep repeating in prompts gets migrated into mechanical validators. |

## Checklist Index

| Gate | Checklist | Items |
|------|-----------|-------|
| Before build | Minimum-viable blueprint | 18 |
| Before build | Build order | 14 steps |
| Design review | Overall design | 16 |
| Design review | Per-tool | 14 |
| Design review | Permission model | 10 |
| Design review | Context hygiene | 9 |
| Design review | Planning discipline | 6 |
| Design review | Goal loops | 8 |
| Design review | Skills quality | 11 |
| Design review | Connectors / MCP | 11 |
| Design review | Agent-legible environment | 9 |
| Design review | Prompt-cache posture | 10 |
| Design review | Mechanical invariants | 6 |
| Before ship | Eval suite composition | 11 |

## Minimum-Viable Blueprint

Gate: do not start building until every box is checked.

- [ ] Domain, primary user, and the job to be done are written down.
- [ ] Scope and non-goals are explicit.
- [ ] Autonomy tier is the lowest one that still delivers value.
- [ ] The model → tool → observation loop is defined end to end.
- [ ] Budgets are quantified: max steps, max tool calls, wall-clock time, tokens, cost.
- [ ] Tool registry is small and every tool is typed.
- [ ] Permission matrix covers read, draft, write, external, financial, destructive, and privileged classes.
- [ ] Every risky operation is split into a draft stage and a separate commit stage.
- [ ] Mutation tools are blocked while the agent is in planning mode.
- [ ] Every goal loop carries stop rules.
- [ ] Context assembly is cache-aware (stable content first).
- [ ] Memory, plans, and approvals live outside the context window in durable storage.
- [ ] Compaction and rehydration rules are written down.
- [ ] Skills load only when their trigger fires, never unconditionally.
- [ ] Connectors are namespaced by origin and every call is logged.
- [ ] Cost telemetry is emitted per run.
- [ ] Traces and evals ran before launch.
- [ ] First rollout is limited or shadow-mode, not full production.

## Build Order

Provider-neutral sequence. Do not skip ahead: each step assumes the previous ones hold.

1. Hand-rolled model / tool / observation loop.
2. Strict schemas plus local argument validation.
3. Runtime permission checks.
4. Structured results and structured error observations.
5. Budgets and stop conditions.
6. Tracing.
7. Cache-aware ordering plus cache telemetry.
8. Planning mode for high-risk work.
9. Context compaction.
10. Skills for reusable workflows.
11. Scoped external connectors.
12. Goal loops — only after the eval suite passes (Hard Rule 5).
13. Subagents — only with evidence of improvement (Hard Rule 6).
14. Recurring knowledge-base upkeep and entropy cleanup.

## Overall Design

- [ ] Persona is defined with a single responsibility.
- [ ] Autonomy tier is chosen and recorded.
- [ ] Every action is assigned a blast radius class (R0–R3).
- [ ] Done criteria are stated.
- [ ] Source-of-truth systems are named.
- [ ] Instruction hierarchy is documented (what overrides what).
- [ ] Tool set is minimal for the job.
- [ ] Permission matrix is complete across all risk classes.
- [ ] Draft/commit split exists for every risky operation.
- [ ] Context builder is specified (what enters context, in what order).
- [ ] Durable memory is designed.
- [ ] Compaction triggers are defined.
- [ ] Criteria for entering planning mode are set.
- [ ] Goal budgets are set.
- [ ] Skills and connector strategy is decided.
- [ ] Observability and an eval plan exist.

## Per-Tool

Run this list once per tool in the registry.

- [ ] Name states what the tool does.
- [ ] Description covers when to use it and when not to.
- [ ] Input schema is strict and typed.
- [ ] Output schema is structured.
- [ ] Arguments are validated locally before execution.
- [ ] Blast radius class (R0–R3) is assigned.
- [ ] Side effects are declared.
- [ ] Permission policy is attached.
- [ ] Timeout is set.
- [ ] Result size is capped.
- [ ] Retry policy is defined.
- [ ] Audit policy is defined.
- [ ] Errors return as structured observations, not raw stack dumps.
- [ ] Sensitive data is redacted from results and logs.

## Permission Model

- [ ] Auto-run is limited to in-scope R0 (read-only) tools.
- [ ] Draft tools and commit tools are separate tools.
- [ ] Outbound sends (mail, chat, posts) require approval.
- [ ] Financial actions require approval plus strong authentication.
- [ ] Identity and access changes require approval plus strong authentication.
- [ ] Destructive operations are denied by default; enabling one requires a gate and a recovery plan.
- [ ] Shell access is sandboxed.
- [ ] Connectors are namespaced and use scoped credentials.
- [ ] Approval records are persisted.
- [ ] The model cannot approve its own actions by any path.

## Context Hygiene

- [ ] Trusted instructions are kept structurally apart from untrusted data.
- [ ] Scoped instructions load conditionally, not permanently.
- [ ] Retrieved content is tagged with source and trust level.
- [ ] Facts that must be exact stay verbatim in context — grounding over paraphrase.
- [ ] Large tool outputs are summarized before entering context.
- [ ] Oversized artifacts are offloaded to files and referenced by path.
- [ ] Plan, goal, and approval state are re-attached after every compaction.
- [ ] Skill and connector state is tracked across compaction.
- [ ] No secrets appear in context.

## Planning Discipline

- [ ] Planning mode is required for risky or ambiguous work.
- [ ] Mutation tools are blocked while planning mode is active.
- [ ] The plan is stored as an external artifact, not chat-only text.
- [ ] The plan contains objective, scope, risks, steps, validation, rollback, and a done condition.
- [ ] Approval is bound to a specific plan version.
- [ ] Post-approval execution proceeds through todos or checkpoints.

## Goal Loops

- [ ] The loop pursues exactly one objective.
- [ ] The done condition is measurable.
- [ ] The budget is explicit.
- [ ] The validation method is defined.
- [ ] Forbidden actions are enumerated.
- [ ] Approval-required actions are enumerated.
- [ ] The progress log is durable.
- [ ] Stop rules are explicit.

## Skills Quality

- [ ] Skill name matches its directory name.
- [ ] Naming is lowercase with hyphens.
- [ ] The skill manifest carries the required frontmatter fields.
- [ ] The description is written for triggering — it says when to activate.
- [ ] The body is concise.
- [ ] Depth lives in focused reference files loaded on demand.
- [ ] Gotchas are documented.
- [ ] Validation steps are present.
- [ ] An activation eval exists.
- [ ] An output-quality eval exists.
- [ ] The skill does not silently expand permissions.

## Connectors / MCP

- [ ] A server inventory exists and is current.
- [ ] Tools are namespaced by origin server.
- [ ] Credentials are per-user or scoped, never shared globals.
- [ ] Scopes follow least privilege.
- [ ] Tool descriptions are reviewed and truncated; external ones are treated as untrusted input.
- [ ] Every connector tool has a mapped blast radius class.
- [ ] Risky calls sit behind approval.
- [ ] Large results are filtered before they enter context.
- [ ] Every call is logged.
- [ ] Auth failure is handled gracefully.
- [ ] Credential revocation is handled gracefully.

## Agent-Legible Environment

- [ ] Top-level instructions act as an index, not a monolith.
- [ ] Source-of-truth documents are retrievable by the agent.
- [ ] Plans persist as artifacts.
- [ ] Schemas, policies, and runbooks are machine-readable.
- [ ] Validation signals are reachable through approved tools.
- [ ] Logs, metrics, and traces are queryable.
- [ ] Human feedback gets folded back into docs, tools, validators, or evals.
- [ ] A cleanup process exists for stale assets.
- [ ] Large systems carry scorecards or gap trackers.

## Prompt-Cache Posture

- [ ] Stable content is ordered before volatile content.
- [ ] Tool definitions are sorted deterministically.
- [ ] Timestamps and request IDs sit late in the prompt or are dropped.
- [ ] Prompt and tool bundles are versioned.
- [ ] Provider cached-token counters are logged.
- [ ] Hit rate is monitored per session and per tenant or segment.
- [ ] System prompt plus tool list is hashed to detect cache fragmentation.
- [ ] Compaction boundaries are explicit.
- [ ] Summaries are not rewritten every turn.
- [ ] Long-retention cache is used only where reuse pays for it.

## Mechanical Invariants

- [ ] Recurring prompt guidance has been converted into validators.
- [ ] Validator errors carry model-readable fix instructions.
- [ ] Architectural boundaries are enforced by machinery, not prose.
- [ ] Secret, PII, and citation checks exist where relevant.
- [ ] Cost, latency, and result-size budgets are enforced, not advisory.
- [ ] Incident-driven regression evals exist (Hard Rule 7).

## Eval Suite Composition

Gate: do not ship until every box is checked.

- [ ] Happy paths are covered.
- [ ] Near misses are covered.
- [ ] Prompt-injection cases are covered.
- [ ] Tool-misuse cases are covered.
- [ ] Approval-bypass attempts are covered.
- [ ] Connector-failure cases are covered.
- [ ] Overflow and compaction stress cases are covered.
- [ ] Conflicting-instruction cases are covered.
- [ ] High-risk (R2/R3) actions are covered.
- [ ] Cost and latency are measured, not just correctness.
- [ ] Every production incident to date has its own regression eval.
