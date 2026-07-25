# Tokenomics — the cost model behind the pipeline's mechanics

Every design decision in agentic-sdlc that touches cost maps onto one factor of
the agent-loop cost model:

```
AgentLoopCost ≈ Tasks × Attempts × AgentTurns × ContextSize × ModelPrice × Parallelism
```

Cost work habitually fixates on **ContextSize** and **ModelPrice**. The
multipliers are the point: a single wasted *attempt* re-pays the entire
`AgentTurns × ContextSize × ModelPrice` product of everything it redoes, so a
bounded loop is usually worth more than a trimmed prompt. This reference names
which mechanism bounds which factor, and is the review rubric for future
cost-touching contributions: state which factor a proposal reduces, and what it
costs on the others.

## Mechanism → factor map

| Mechanism | Where | Factor bounded | How |
|---|---|---|---|
| Heuristics-first complexity routing | `sdlc-pipeline` Phase 3 | Tasks, ModelPrice | Cheap signals resolve routing without dispatching the `sizing-analyst` subagent when the answer is obvious. |
| Cheapest-first gate resolution | `decision-router` | Attempts, ModelPrice | Deterministic checks and fast-paths run before any stand-in subagent; a model is the last resort, never the first. |
| Loop-cap registry (`meta.json.loops`) | `sdlc-pipeline` § Loop accounting | **Attempts** | Every retry/fix-up/revision loop has a named ID, a counter in run state, and a hard cap; at cap the run halts with a resume command instead of silently paying for another round. Caps: `gate-catalog.md` § Loop caps. |
| Deterministic evidence validation | `sdlc-pipeline` Phase 7 | Attempts, ModelPrice | Malformed or missing task evidence produces an exact fix instruction — never a model-judged review round. |
| Deferred code review | `sdlc-pipeline` Phase 9 | AgentTurns, ModelPrice | Model review runs exactly twice (review + findings-only check) against the *complete* diff, not once per task. |
| ArtifactRefs summaries | `sdlc-pipeline` § Artifact summaries | **ContextSize** | Gates receive ~2 KB extracts + sha-256 signatures (~6 KB/gate budget), never full artifact bodies. |
| `memory_brief` single load | `sdlc-pipeline` Phase 0 | ContextSize, AgentTurns | Memory is read once (~6 KB cap) and propagated; never re-read mid-run. |
| Run isolation / no cross-run adoption | `sdlc-pipeline` § Constraints | Attempts | Stale sibling artifacts can't masquerade as phase output — the class of "implemented against the wrong spec" rework is structurally excluded. |
| Fresh-context task subagents | Phase 7 via `superpowers:subagent-driven-development` | ContextSize | Each implementation task starts from a compact plan slice, not the orchestrator's accumulated history. |
| Parallelism-safety rules | `references/parallelism-safety.md` | **Parallelism** | Parallel dispatch is a bounded, rule-checked decision, not an orchestrator default. |
| Mode routing (hitl / autonomous / task) | `references/mode-routing.md` | Tasks | `sdlc-task` gives user-classified small work a short pipeline instead of the full 13 phases. |
| Model-tier routing (`economy`/`standard`/`premium`) | `references/model-routing.md` | **ModelPrice** | Dispatches resolve a tier mapped in host config; every default is `inherit`, and no model ID ever ships in the plugin. |

## What deliberately does NOT exist

- **A shipped pricing table or model IDs** — vendor-specific and stale on
  arrival; hosts map their own models (everything is `model: inherit` today).
- **Per-phase hard session stops** — one checkpoint/resume contract covers
  interruption; a forced stop at every boundary trades user experience for
  context savings the subagent architecture already provides.
- **Token telemetry collectors** — a `usage.sampled` event may be recorded by
  hosts that have usage data, but the plugin ships no collector or dashboard;
  per-run reporting is a roadmap item (`report-builder`).

## Review rubric

A change that adds a loop must register a loop ID and cap. A change that adds
a gate must state its deterministic pre-checks. A change that inlines file
bodies into a gate or subagent prompt must justify why an ArtifactRef summary
is insufficient. A change that dispatches a subagent must say which factor
pays for it and which factor it saves.
