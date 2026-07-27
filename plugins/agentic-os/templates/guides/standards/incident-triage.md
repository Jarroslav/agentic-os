# Incident Triage — Read-Only Diagnosis Standards

<!-- Scaffolded by agentic-os to .agentic/guides/standards/incident-triage.md.
     Single source of truth for AI-assisted incident triage. Triage entry point:
     the incident-triage agent. -->

Blocking standards for diagnosing production and runtime incidents with an
agent in the loop. The agent diagnoses; humans execute. Teams record their
per-service specifics (allowlist, bounds) directly in this installed file —
it is user-owned after install.

## Triage is read-only

The triage agent never mutates cluster, infrastructure, or application state.
These verb classes are always outside triage, whatever the tool: apply, patch,
delete, scale, restart, rollout, exec-into, write-config, rotate-credential.
Every fix is a recommendation with the exact command for a human to run; the
human executes and owns the outcome. A "quick safe fix" performed by the agent
is a policy violation, not initiative.

## The three-hypothesis rule

Every triage run produces **exactly 3 ranked root-cause hypotheses**. Each
slot carries: a one-sentence hypothesis, a confidence label (`High` / `Medium`
/ `Low`), the evidence lines it rests on, and the **cheapest read-only next
diagnostic** that would confirm or kill it.

When fewer than 3 hypotheses have evidence, the shortfall is stated in the
output ("1 of 3 slots evidence-backed") and every unsupported slot carries the
literal label `speculative — no direct evidence`. Padding the list with
plausible-sounding fillers is the fabrication class defined in
[`evidence-integrity.md`](evidence-integrity.md) § "MUST NOT pad a list to hit
a required count" — that rule governs here.

Rank by evidence weight, never by how easy the fix would be.

## Runtime bounds

Every bound on automated triage activity is a **number plus a unit** — a bound
without a unit is not a bound. At minimum, a triage loop declares: maximum
diagnostic rounds per run, a per-recommended-command time budget, a cooldown
between evidence re-polls, and a cost cap per run.

Every automated triage loop names **one kill-switch** that halts all triage
activity when set. The shipped default is the environment variable
`AGENTIC_INCIDENT_TRIAGE_DISABLED=1`; when it is set, the agent emits only an
escalation and stops. A loop without a named kill-switch does not run.

## Tool access is an allowlist

The commands and tools triage may recommend or invoke are an explicit
allowlist recorded in this file per service (read/list/describe/status calls,
log retrieval, metric queries). **Anything not listed is denied by default.**
Denylists are prohibited: a denylist fails open the day a new tool appears,
an allowlist fails closed. "It isn't on the forbidden list" is never a
justification.

## Escalation

Severity declaration, paging, rollback, restart, scaling, and config changes
are human-owned decisions — the agent surfaces them with options under its
escalation section and never resolves them
(see [`../policy/escalation-policy.md`](../policy/escalation-policy.md)).
An active incident with no named human owner halts triage: the first
escalation is "who owns this incident?".

## How to propose a change

Same protocol as the other standards: add the rule here, quote the incident it
came from, PR title `docs(standards): <rule short title>`. Only the owner can
approve removing or weakening a rule.
