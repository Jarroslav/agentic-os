# Grant Tools by Blast Radius (R0–R3)

Design reference for the tool surface an agent may call. Covers how to classify each tool by the damage an errant call can do, gate it accordingly, and constrain what flows in and out of the model. Audience: engineers and QA architects building agent harnesses — the people writing tool definitions, permission engines, and sandbox policy, not the agents themselves.

Sibling method references (architecture, context management, evaluation) assume the tiers and verdicts defined here whenever they mention a gated action.

## 1. The blast-radius ladder

Tag every tool with one of four tiers before you wire it into a harness. The tag answers a single question: **if the model calls this tool with the worst plausible arguments, what is the largest thing that breaks?**

| Tag | Blast radius | Default stance |
|-----|--------------|----------------|
| R0 | Nothing changes. Reads, searches, pure computation. | Grant freely within a scope boundary. |
| R1 | Run artifacts change. Drafts, reports, logs, scratch workspace — recreatable by rerunning. | Grant when path-scoped to the run's own workspace. |
| R2 | Repo files or internal records change. Persists beyond the run; reviewable before it lands. | Approval, or an explicit per-tool allowlist. |
| R3 | The outside world changes. Messages leave, money moves, access shifts, data disappears. | Always behind a human gate. No allowlist exemptions. |

> The ladder is asymmetric on purpose. Misclassifying an R0 tool as R2 costs a needless prompt; misclassifying an R3 tool as R1 costs a sent email or a deleted record. When in doubt, tag one tier higher.

An R3 gate means a human sees the concrete action — recipient, amount, target record — before it executes, not a blanket "the agent may act" toggle granted once per session.

## 2. Risk classes and where they land

Tag each tool with a fine-grained risk class as well; the blast-radius tier is derived from it. The permission engine consumes the class, humans reason in tiers.

| Risk class | Tier | Notes |
|------------|------|-------|
| `read_only` | R0 | Scope boundary still applies (see §3). |
| `search_only` | R0 | Bounded query surface, no mutation. |
| `compute_only` | R0 | Pure computation inside a bounded environment. |
| `network_open_world` | R0/R1 | Web reach; allow or restrict per product policy. Treat fetched content as untrusted input. |
| `draft_only` | R1 | Produces a proposal object, never a committed effect. |
| `write_local` | R1 | Writes confined to the run workspace. |
| `process_execution` | R1 | Only ever inside a sandbox (§8); tier assumes the sandbox holds. |
| `write_internal` | R2 | Repo files, internal records, tickets, wikis. |
| `write_external` | R3 | Third-party systems of record. |
| `communication` | R3 | Anything that reaches a human outbox: email, chat, comments on external trackers. |
| `financial` | R3 | Approval **plus** step-up authentication. |
| `identity_access` | R3 | Approval **plus** step-up authentication. |
| `security_sensitive` | R3 | Key material, policy objects, audit configuration. |
| `destructive` | R3 | Default-deny; approve only with a recovery plan attached. |
| `privileged_admin` | R3 | Default-deny outside break-glass procedures. |

## 3. Decision rules

Encode these as policy, not as prompt text. The model never enforces its own permissions.

| Operation | Rule |
|-----------|------|
| Public reads | Allow. |
| Private user reads | Allow only inside the requesting user/session boundary. |
| Org-level reads | Gate on role. |
| Web search | Allow or restrict per product policy. |
| Pure computation | Allow inside a bounded environment. |
| Draft-only actions | Allow. |
| Local artifact writes | Allow when path-scoped. |
| Internal record writes | Approval, or a policy allowlist. |
| Outbound communication | Draft always; sending needs approval. |
| Financial actions | Approval + stronger authentication. |
| Identity/access changes | Approval + stronger authentication. |
| Destructive actions | Default-deny, or approval with a recovery plan. |
| Process execution | Sandbox + command allowlist + timeout. |
| Installing new connectors | Approval + review. |

## 4. A tool is a contract

The model consumes a declared interface; execution belongs entirely to the harness. Nothing about how a tool runs — credentials, retries, network paths — is the model's business. Declare every tool with a complete record:

| Attribute | What it fixes |
|-----------|---------------|
| Identifier | Stable name the model calls. |
| Intent | One sentence: what this tool is for. |
| Input schema | Strict JSON schema for arguments. |
| Output schema | Strict JSON schema for results. |
| Risk class | One value from §2. |
| Side-effect class | None / local / internal / external. |
| Resource scope | Which records, paths, or tenants it may touch. |
| Permission rule | Which policy from §3 governs it. |
| Timeout | Hard wall-clock ceiling. |
| Output cap | Maximum bytes/items returned (§7). |
| Retry policy | Idempotent-retry vs. retry-blocked. |
| Audit policy | What gets logged per call (§5). |
| Error shape | The structured failure contract (§7). |

The registry must expose the risk metadata to the permission engine at decision time. A tool whose risk class the engine cannot read does not ship.

### Narrow beats generic

One tool, one responsibility — the same single-responsibility rule you apply to roles applies to tools. A verb bound to a domain object is auditable; a universal escape hatch is not.

| Avoid | Prefer |
|-------|--------|
| Run an arbitrary shell command | Execute the project's test suite in a sandbox |
| Issue any HTTP request | Search the policy-document index |
| Execute raw SQL updates | Read one customer account by ID |
| Send an untyped message anywhere | Draft an email bound to a case ID |
| Mutate any record | Apply a refund by approval ID |

> A generic tool inherits the blast radius of the worst thing it can express. `run_shell` is R3 no matter how it is usually used, so every call pays the R3 gate. Ten narrow tools with honest tiers are cheaper to operate than one omnipotent tool behind a permanent prompt.

### Schema discipline

- Require every field that matters; reject unknown properties.
- Use enums for bounded choices, typed IDs instead of freeform strings.
- Validate locally before executing — a malformed call must fail before it touches anything.

Schema conformance is a **reliability** property. It stops garbled calls; it does not stop well-formed harmful ones. Security lives in the permission layer, never in the schema.

### Descriptions

A tool description should tell the model: when to use it, when not to, prerequisites, side effects, notable failure modes, and one or two valid-argument examples. Long reference material goes behind a discovery tool or a linked resource — never inline in the description.

## 5. The permission engine

### Typed verdicts

A boolean is not enough. The engine returns one of:

`allow` · `deny` · `ask_user` · `require_approval` · `require_step_up_auth` · `force_sandbox` · `downgrade_to_draft`

`downgrade_to_draft` is the workhorse: instead of refusing a `communication` call outright, the engine converts it into its R1 preparation counterpart (§6) and lets the run keep moving.

### Audit record

Log every decision — allows included — with:

- tool identifier
- arguments (or a hash when arguments carry sensitive payloads)
- risk class and resource scope
- verdict and the policy rule that matched
- user/session identity; approver identity when a gate was cleared
- timestamp

> An unlogged `allow` is the decision you will most want to reconstruct after an incident and cannot.

## 6. Split risky verbs: prepare, then commit

Any R2/R3 effect worth gating is worth splitting into a pair: a **prepare** tool (R1, produces a reviewable object with an ID) and a **commit** tool (R2/R3, consumes that ID and nothing else).

| Prepare (R1, autonomous) | Commit (gated) |
|--------------------------|----------------|
| Draft an email | Send it |
| Stage a refund | Issue it |
| Propose a record change | Apply it |
| Stage a contract amendment | Submit it |
| Produce a trade recommendation | Place the order |
| Stage a workflow change | Commit it |

Rules:

- Prepare-stage tools run without asking. That is the point — the agent does all its thinking at R1.
- Commit-stage tools require approval unless a policy allowlist explicitly marks a specific commit tool as low-risk.
- The commit tool accepts only the prepared object's ID. It cannot commit anything a human (or the gate) has not seen.

## 7. Shape what comes back

### Observations, not dumps

Tool results are context the model must reason over — treat them as a designed surface. Return a structured observation:

- `status` — succeeded / failed / partial
- a one-line summary
- itemized results carrying IDs and evidence references
- valid next actions the model may take from here

Evidence references are what keep the agent grounded: every claim in its output should trace to an ID or reference a tool actually returned, never to an invented fact.

### Cap the volume

The model should never receive ten thousand rows to answer a counting question. Apply the knobs at the tool boundary:

| Knob | Use |
|------|-----|
| Character cap | Hard ceiling per result |
| Item cap | Max entries per response |
| Pagination cursor | Model pulls the next page only if needed |
| Log tail | Last N lines, not the whole log |
| Snippet length | Excerpt around the match, not the file |
| Artifact handle | Park bulky data outside context; return a reference the model can pass to other tools |

### Errors are data

A failed call returns through the same channel as a success — never a silent crash, never a raw stack trace. Mirror the success shape:

- `status: failed`
- `error_type` — one of: `unknown_tool` · `invalid_arguments` · `permission_denied` · `approval_required` · `auth_expired` · `not_found` · `timeout` · `rate_limited` · `conflict` · `non_idempotent_retry_blocked` · `internal_error`
- a human-readable message
- safe next actions (retry, page, ask the user, pick a different tool)

`approval_required` and `permission_denied` are distinct on purpose: the first tells the model to route through a gate; the second tells it to stop trying.

## 8. Sandbox policy

Force sandboxed execution — the `force_sandbox` verdict or a static rule — for anything involving: shell or process execution, browser automation, model-generated code, file manipulation, tools you did not author, external data, or multi-step connector flows.

Controls to compose:

- filesystem allowlist; read-only mounts where feasible
- network allowlist with egress logging
- process timeout; CPU and memory caps
- ephemeral workspace, with snapshot/resume if runs are long
- secret isolation (nothing ambient inside the sandbox)
- an explicit artifact-export policy — what may leave the sandbox, and how

## 9. Secrets never touch the model

Credentials are a harness concern. The model calls a tool; the tool authenticates internally; the result comes back redacted.

- Short-lived, narrowly scoped tokens only.
- Bind credentials to the user/session, never to the agent globally.
- Redact secret-shaped values in every trace and log.
- No ambient environment credentials reachable from tool code the model influences.
- Block reads of secret-like files (key material, token stores) absent explicit approval.
- Never route a credential through model context to hand it from one tool to another — pass an opaque handle instead.

## 10. Progressive tool visibility

Exposing the full catalog on every turn burns context and measurably degrades tool selection. Reveal tools in tiers:

| Tier | Visible when |
|------|--------------|
| base | Always — the small core set. |
| task | After the task is classified. |
| skill | After a skill/playbook is selected. |
| connector | After the relevant connector is authenticated. |
| deferred | On demand, via a search/discovery tool. |
| sensitive | Hidden until needed **and** approved. |

Visibility is not permission: a hidden tool is still governed by §3 once revealed, and a visible tool still hits its gate. The tiers manage attention; the engine manages authority.

## Scope

This reference is platform-neutral: no framework, connector protocol, or vendor SDK specifics. It does not cover prompt design, model selection, or evaluation method, and it does not prescribe an approval UI or auth provider — only the decision semantics they must implement. Infrastructure hardening beyond the agent's tool boundary is out of scope.
