# Unattended Automation: Pin a Workflow or Run an Agent

Wire issue trackers, chat, and pipelines so their events fire your QE blueprints over HTTP — no human typing into a chat window. This guide covers the trigger chain, the agent-vs-workflow decision, wiring recipes for four trigger surfaces, a security hardening model, and a launch checklist.

**Assumes:** the agent already produces good output when invoked manually; you have admin rights in the trigger system, an HTTPS-reachable agent endpoint, and access to a secret manager.

**Out of scope:** prompt authoring and agent instruction design; the content of the QE blueprints themselves (see the catalog); platforms with no HTTP-reachable agent surface beyond the workarounds in the [platform matrix](#executing-platform-matrix); general webhook security beyond what write-capable agent triggers need.

---

## The core decision: free-planning agent vs pinned workflow

Two architectures can sit behind the same trigger:

| | Free-planning agent | Pinned workflow |
|---|---|---|
| Control flow | Orchestrator plans at runtime, dispatches subagents | Fixed sequence of agent calls |
| Per step | Chosen live | Model, prompt, and toolset pinned in advance |
| Can ask a human mid-run | Yes | No |
| Predictability | Low | High |
| Testability | Hard | Each step testable in isolation |
| Flexibility | High | Low |

Decision rules:

| Situation | Choose |
|---|---|
| Human invokes the run and can redirect it | Orchestrator + subagents |
| Event fires the run with nobody watching | Pinned workflow |
| Unsure | Workflow. Reach for a free-planning agent only when genuinely necessary. |

> With a human in the loop, flexibility wins — the human corrects drift in real time. Unattended, nobody corrects anything, so predictability and testability win. Production automation lands on a pinned workflow almost every time, whatever the executing platform (Claude Code, Cursor, GitHub Copilot).

---

## Anatomy of a trigger chain

Every integration below is the same five-link chain:

```
external event
  -> automation rule / flow / pipeline hook
    -> HTTP POST carrying event context to the agent endpoint
      -> agent run
        -> results written back into the origin system
           (ticket comment, MR review, chat reply)
```

Each side must bring:

| Side | Requirements |
|---|---|
| Agent | Configured instructions; reachable HTTPS API; auth token |
| Trigger | A rule/flow/hook; ability to POST; event context (issue key, PR id, message text) |

---

## Pinning a workflow

Do not let the agent pick tools live. Pre-wire the sequence:

```
retrieve -> generate -> validate -> publish
```

Pin every step. One responsibility per step.

| Step | Job | Model tier | Blast radius |
|---|---|---|---|
| retrieve | Pull ticket/PR/message context from the origin system | economy | R0 (read-only) |
| generate | The one genuinely reasoning step — produce the artifact | premium | R1 (writes run artifacts) |
| validate | Check output against schema, policy, grounding | standard | R1 |
| publish | Write back into the origin system | economy | R3 (external side-effect) |

Per-step pins, all four steps:

- **Model tier fixed.** Premium only where reasoning happens; standard/economy everywhere else. Tier choice per blueprint step: see the sibling model-selection guide (`model-selection.md`, this folder).
- **Tools minimal and explicit.** Grant only what the step needs.
- **Prompts version-controlled.** No free-form user instructions injected at runtime — the event payload supplies data, never directives.
- **Grounded.** The step may only assert facts present in its inputs. Vague output usually means a starved payload, not a weak model — see the [failure catalog](#failure-catalog).
- **Idempotent.** Safe to re-run on the same event. See [idempotency](#idempotency-and-replay).
- **Failure routing defined.** Each step declares what happens on failure: retry, escalate to a human, or block the publish step.

> The publish step is R3: it changes state in a system other people rely on. R3 stays behind a human gate until production output quality is proven — and removing that gate is a deliberate decision that requires the fully-automated control set in the [security model](#security-model), not a config toggle.

---

## Prerequisites

Before wiring anything:

- [ ] Agent configured, with toolkit permissions scoped to the workflow's steps
- [ ] HTTPS endpoint, ideally already network-restricted
- [ ] Per-trigger, narrowly scoped token in a secret manager, with a rotation schedule
- [ ] Rights to create rules/flows/pipeline steps in the trigger system
- [ ] Trigger system can send an HTTP POST
- [ ] HMAC signing and idempotency plan agreed **before** any no-gate workflow goes live

---

## Wiring recipes

| Origin system | Mechanism | Middle layer |
|---|---|---|
| Jira | Automation rule + web request action | none |
| Azure DevOps | Service hook | Power Automate (required) |
| Teams / Outlook | Power Automate flow | Power Automate, both directions |
| CI/CD | Pipeline event + curl step | none |

### Jira: automation rule + webhook

1. Create an automation rule on the triggering event (issue created, transitioned, labeled).
2. Add a web request action: POST to the agent endpoint, bearer token from a secret, body carrying the issue key **plus** title, status, and the fields the workflow needs.
3. Have the workflow's publish step write results back as a comment, sub-tasks, or linked items.

Proven uses: story review posted as a comment; sub-task generation; test-case generation with cases created in the TMS and linked back; epic decomposition into stories under the epic.

**Anti-pattern — infinite loop.** The bot's own comment re-fires the rule, which posts another comment, forever. Add a rule condition that skips events authored by the bot's service account before enabling anything.

### Azure DevOps: service hook routed through Power Automate

Service hooks emit a fixed JSON shape you cannot reshape at the source. Put Power Automate between the hook and the agent:

1. Create a service hook subscription for the work-item or PR event.
2. Point it at a Power Automate flow that parses the hook payload, extracts the fields the workflow needs, and builds the agent's expected request body.
3. The flow POSTs to the agent endpoint with the token pulled from a secure input.

### Teams / Outlook: Power Automate, bidirectional

**Inbound** (event fires the agent): trigger a Power Automate flow on a new channel message or inbound email. Filter to @mentions of the bot — without the filter the flow fires on every message in the channel. The flow POSTs the message text and context to the agent; the workflow replies in-thread.

**Outbound** (agent posts proactively): expose a Power Automate flow with an HTTP-request trigger, then register that trigger URL as an OpenAPI tool the agent can call. Use it for notification bots and scheduled digests.

Proven uses: @mention bot answering in-thread; support bot fed by messages or email; proactive/scheduled notification bot.

### CI/CD: pipeline step + curl

A plain shell step. Endpoint URL and token live in encrypted pipeline secrets, never in the YAML.

GitHub Actions:

```yaml
on:
  pull_request:
    types: [opened, synchronize]
jobs:
  agent-review:
    runs-on: ubuntu-latest
    steps:
      - name: Fire review workflow
        env:
          AGENT_ENDPOINT: ${{ secrets.AGENT_ENDPOINT }}
          AGENT_TOKEN: ${{ secrets.AGENT_TOKEN }}
        run: |
          curl -sf -X POST "$AGENT_ENDPOINT" \
            -H "Authorization: Bearer $AGENT_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"event\": \"Review PR #${{ github.event.pull_request.number }} in ${{ github.repository }}\"}"
```

GitLab CI:

```yaml
agent_review:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - >
      curl -sf -X POST "$AGENT_ENDPOINT"
      -H "Authorization: Bearer $AGENT_TOKEN"
      -H "Content-Type: application/json"
      -d "{\"event\": \"Review MR !${CI_MERGE_REQUEST_IID} in ${CI_PROJECT_PATH}\"}"
```

Azure Pipelines:

```yaml
- script: |
    curl -sf -X POST "$(AGENT_ENDPOINT)" \
      -H "Authorization: Bearer $(AGENT_TOKEN)" \
      -H "Content-Type: application/json" \
      -d "{\"event\": \"Review PR $(System.PullRequest.PullRequestId)\"}"
  displayName: Fire agent review workflow
```

Adjust the JSON body to each agent platform's request spec — a wrong field name is the classic 400 (see the [failure catalog](#failure-catalog)).

Proven uses: MR/PR review on open or update, posted as a review comment; scheduled (nightly) batch review of all open MRs.

---

## Executing platform matrix

| Executing platform | Trigger surface | Auth | Notes |
|---|---|---|---|
| Claude Code | Hosted routines fired via HTTP | Per-routine bearer token | Paid plan required; API is experimental |
| Cursor | Webhook URL; Slack, GitHub, cron, Linear, PagerDuty integrations | Managed per integration | No public REST API |
| GitHub Copilot | `repository_dispatch` event watched by a GitHub Actions workflow | Standard workflow token | Executes inside Actions |

### Hosted routines (Claude Code)

> Status: experimental as of the 2026-04 review. Requires a paid plan. Re-check the platform's docs for current header names and body field before shipping.

- Path shape: `POST /v1/claude_code/routines/{id}/fire`
- Auth: per-routine bearer token
- Required headers: a versioned API header and a dated beta header (names per current docs)
- Body: JSON with a single field carrying the event text
- Response: returns **immediately** with a session URL. It does not block until the run finishes — the caller cannot read results from the response. Write-back into the origin system happens from inside the workflow's publish step.

One consequence of the immediate return: each fire creates a fresh session with no built-in dedupe key. Deduplication is entirely the caller's job.

---

## Security model

> A trigger endpoint drives a write-capable agent. A bearer token alone is the floor, not the target posture: leak the secret and any caller on the internet acts as your agent.

Apply defenses top-down; each layer assumes the one above it can fail:

| # | Layer | Control |
|---|---|---|
| 1 | Network restriction | VPN, IP allowlist, or mTLS; ingress limited to the trigger system's egress IPs |
| 2 | Caller identity | mTLS or signed requests; bearer-only reserved for low-risk, network-restricted paths |
| 3 | Payload integrity | HMAC signature header computed over the raw body; reject on mismatch |
| 4 | Token scoping | One rule = one least-privilege token; scheduled rotation |
| 5 | Replay protection | Event id as dedupe key; reject repeats within the window |

Minimum controls by automation level:

| Level | Definition | Minimum controls |
|---|---|---|
| Semi-automated | Human reviews output before anything publishes | Network allowlist + bearer token + idempotency key |
| Fully automated | Workflow writes directly into the origin system | Allowlist or mTLS + HMAC body signing + per-trigger scoped rotated token + enforced idempotency key |

---

## Idempotency and replay

Idempotency is mandatory, not optional. Trigger systems retry, humans double-click manual buttons, and some agent platforms create a fresh session per request with no built-in dedupe.

- Carry the origin event id (issue key + event timestamp, PR id + head SHA, message id) in every request.
- Check it before **any** write: has this event already produced output? A cheap concrete check — look for an existing bot comment on the ticket before posting one.
- Treat the event id as the dedupe key for replay protection (layer 5 above).

---

## Failure catalog

| Symptom | Likely cause | Fix |
|---|---|---|
| Rule fires forever on its own output | Bot comment re-triggers the rule | Skip condition on the bot service account ([Jira recipe](#jira-automation-rule--webhook)) |
| Output vague or generic | Payload carried only an id; workflow had nothing to ground on | Enrich payload with key, title, status, and needed fields; align agent instructions to those fields |
| 401 after working previously | Token rotated or expired | Rotate token, update the secret store |
| 400 on every call | Wrong input field name or JSON shape | Validate the body against the platform's request spec |
| Timeouts, no response | Network restriction blocks the trigger's egress | Allowlist the trigger system's egress IPs |
| Duplicate runs, double comments | Retries or overlapping events with no dedupe | Enforce the idempotency key; check for existing output before writing |

---

## Provenance labels

Every published output carries an AI-generated marker: a label in the test-management system, a ticket label, a commit trailer, a PR marker.

> Two reasons: readers deserve to know what was machine-written, and the labels are your adoption metric — count them to measure what the automation actually produces.

---

## Launch checklist

Work through in order. Do not skip to event-based firing.

1. [ ] Invoke the workflow manually in chat; confirm output quality
2. [ ] Wire a manual-button trigger; fire it; confirm the full chain end-to-end
3. [ ] Restrict endpoint ingress (allowlist / VPN / mTLS)
4. [ ] Scope the token to this one trigger; schedule rotation
5. [ ] Sign payloads with HMAC (required before removing any human gate)
6. [ ] Enforce the idempotency key on every write path
7. [ ] Filter out the bot's own service-account events
8. [ ] Enrich the input payload; match agent instructions to the fields actually sent
9. [ ] Add AI-provenance labels to every published output
10. [ ] Keep the human review gate until production output quality is proven

---

## Related references

- `model-selection.md` (this folder) — which model tier each pinned step gets
- Blueprint documents in the catalog — §2 (agentic implementation) describes the human-invoked orchestrator pattern; §5 (automation) plus this guide describe the trigger-fired workflow
- Vendor docs: Atlassian automation web-request action; Microsoft Learn (service hooks, work-item rules, Power Automate); GitHub Actions documentation; Cursor automations page; the hosted agent platform's docs site
