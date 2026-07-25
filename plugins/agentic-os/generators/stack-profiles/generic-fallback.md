# Stack profile: generic-fallback (historical — no longer an active code path)

> **This file is a documentation stub, not something the installer routes to
> anymore.** Before Stage 2 of the universal-stack-support program, "no
> curated profile matched" meant this profile applied and writer slots were
> unconditionally suppressed. As of Stage 2, "no curated profile matched"
> means `generators/stack-discovery.md` runs in `full` mode instead — it
> inspects the real repo and produces genuine, evidence-grounded
> per-capability facts, and Phase 5's applicability filter
> (`skills/agentic-init/SKILL.md` § Phase 5 step 1) reads those facts
> directly. Nothing in the installer reads this file at install time; it is
> kept only as a record of what the old all-or-nothing behavior was and why
> the new one is better, in case that history is useful.

## What actually happens now for a non-curated stack

Read `generators/stack-discovery.md` — specifically its "Process — `full`
mode" section — for the real behavior. In one line: **slots follow
discovery; only what discovery genuinely can't ground gets degraded**, not
the whole install. A repo with a real, evidence-backed `persistence` capability
still gets a real `gen/schema-architect`, even with zero curated-profile
match — proven live against two non-curated fixtures (a FastAPI+Alembic
backend and a schemaless Express+Mongoose backend) in Stage 2's golden runs,
`tests/universal/README.md`.

## What was wrong with the old all-or-nothing model

The old model conflated two different things: "no curated profile matched"
(a fact about a lookup table) and "this repo's facts can't be grounded" (a
fact about evidence). The first is common — most real stacks aren't one of
six curated profiles — and doesn't imply the second at all. Suppressing
every writer slot for every non-curated repo, regardless of how much real
evidence the repo actually offered, was the core universality gap this whole
program exists to close.

## What's still true, reframed per-capability instead of install-wide

The old "degraded expectations" mechanism itself was sound — it just applied
at the wrong granularity (the whole install) instead of the right one (a
single low-confidence capability). Per `stack-discovery.md`'s full-mode
process, when a specific capability's evidence is thin or absent:

1. Confidence honestly reflects that (below 80, not a confident guess) and
   the capability is named in the record's `unresolved` array with candidate
   values — Screen 5 asks the human directly instead of the installer
   guessing.
2. If a human answer still leaves a generated contract scoring below
   `{{SCORE_THRESHOLD}}` after the retry loop, it installs with a **relaxed
   per-agent threshold** recorded in the scorecard at `{{SCORECARD_PATH}}`,
   never silently at the default threshold — a **visible warning** names the
   degraded asset and its score, and a **tracked follow-up** is journaled.
3. A capability that's genuinely absent (e.g. `persistence.paradigm =
   external-or-none`, or `ui.applies = false` for an API-only service) skips
   its slot(s) — a true fact about this repo, not a degradation to apologize
   for.

None of this is unique to "no curated profile matched" anymore — it's just
what happens whenever a capability's real-world evidence is thin, curated
stack or not.

## Historical note

The original rationale ("an ungrounded writer agent is worse than none")
is still correct — it's *why* confidence gating and the `unresolved`
mechanism exist. What changed is the unit of measurement: it used to be
"the whole stack is unknown," now it's "this one capability's evidence is
thin," which is both more accurate and, per the Stage 2 golden runs, far
less pessimistic than the old default assumed.
