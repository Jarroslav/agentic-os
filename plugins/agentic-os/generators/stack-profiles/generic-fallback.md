# Stack profile: generic-fallback

Applied when no other profile's detection markers match. This profile makes
**degraded expectations explicit** (PLAN.md decision 6) — it never pretends
to know the stack.

## Detection markers

- None matched. This is the else-branch, chosen only after every other
  profile has been tested.

## Variable defaults

| Variable | Default |
|---|---|
| `{{MIGRATIONS_DIR}}` | empty — migration hooks skipped unless the interview supplies a directory |
| `{{GATE_COMMANDS}}` | none detected — **must** come from the interview; if the human supplies none, gate agents record "no automated gates configured" under `## Non-blocking` in every run |
| `{{MIGRATION_DIFF_COMMAND}}` | empty |
| `{{ENV_CHECK_COMMANDS}}` | `git status --short` only |
| `{{APP_START_COMMAND}}` | empty — feature verification degraded to manual |
| `{{BASE_URL}}` | interview |

## Generated-agent slots that apply

`gen/stack-guides` only, and even that in degraded form (see below).
Writer slots (`gen/schema-architect`, `gen/api-author`,
`gen/component-generator`, `gen/i18n-agent`) and `gen/migration-validator`
are **not generated** — without detected stack facts their contracts cannot
be evidence-grounded, and an ungrounded writer agent is worse than none.
The templated core agents (reviewer, gates, dispatcher) still install — they
are stack-agnostic.

## Degraded expectations (stated to the user at install time)

Per PLAN.md decision 6, when generation must proceed anyway (user opts in):

1. Generated output that scores below `{{SCORE_THRESHOLD}}` on the
   instruction-quality rubric installs with a **relaxed per-agent threshold**
   recorded in the scorecard at `{{SCORECARD_PATH}}`, never silently at the
   default threshold.
2. The installer prints a **visible warning** naming each degraded asset and
   its actual score.
3. A **tracked follow-up** is journaled (install journal + `## Escalate to
   human` in the installer's report): re-run generation after the human
   fills in stack facts, or hand-write the contract.

Additional degradations the user must expect:

- Stack guides reduce to structure-only documents: repo layout, observed
  file types, and TODO sections for the human — rules without evidence are
  not invented.
- No migration safety net: the migration-validator slot is absent, so any
  schema work is escalated to a human by policy.
- Feature verification is manual: no `{{APP_START_COMMAND}}` means the
  verification step reports "not verifiable autonomously".

## Stack facts for the generators

Only what is observable without stack knowledge: directory tree, dominant
file extensions, presence of a CI config (`.github/workflows/`,
`.gitlab-ci.yml`), presence of a Dockerfile/compose file, README claims
(cited as claims, not facts). Everything else: interview.
