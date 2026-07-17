# Universal-stack harness (model-driven, manual)

`tests/run-matrix.sh` is deterministic and CI-gated, but it routes entirely
through `tests/lib/refinstall.py` — a Phase-4-only reference executor that
never exercises Phase 1 stack **discovery** or Phase 5 **generation**. Those
are model-driven: they need a real subagent run, not a mock. This directory
documents the manual (but repeatable) procedure that proves universality —
the same method used to verify Stage 0's exemplar de-leak, extended here to
`generators/stack-discovery.md`.

There is no automated runner here on purpose: spawning real subagents from a
bash script isn't possible, and mocking the model-driven parts would prove
nothing about the actual claim (that discovery generalizes beyond the six
curated stacks). Run this procedure by hand — via the `Agent` tool — whenever
`stack-discovery.md`, an exemplar, or a generator prompt changes in a way
that could affect fact acquisition or generation quality.

## Procedure

1. **Confirm-only regression check** (must pass before shipping any
   discovery-related change): spawn `stack-discovery.md` in `confirm-only`
   mode against a curated-stack fixture with the matched profile as input.
   Assert the record's derived `{{MIGRATIONS_DIR}}` /
   `{{PERSISTENCE_WRITE_SCOPE}}` (and other scalars the profile defines)
   match the profile's "Variable defaults" table exactly. A drift here means
   a curated-stack install changed behavior — that is the one regression this
   whole design exists to prevent.
2. **Full-mode discovery on a non-curated or greenfield fixture**: spawn
   `stack-discovery.md` in `full` mode against a repo with no Tier-1 marker
   match. Assert: every non-null field carries real `file:line`/directory
   evidence (never invented); confidence honestly reflects evidence strength
   (thin/absent evidence → below 80, `unresolved` entries with named
   candidates — never a confident guess dressed as certainty).
3. **Generation on a non-curated fixture** (Stage 2+): run discovery (step 2),
   then generate the applicable `gen/*` slots per Phase 5's capability-driven
   applicability table against the fixture, and independently audit each via
   the `instruction-auditor` contract, exactly as Stage 0/1 did for the
   curated stack. Universality is proven when the generated agent audits
   ≥95, grounded in the fixture's real code — not in the discovery record
   (the record is an unverified hint per `stack-discovery.md` § Evidence
   guarantee; a generated rule citing it fails the instruction-quality-
   rubric's discovery-record check — this check has already caught a real
   instance live, see the Stage 2 golden run below).

## Fixtures

| Fixture | Path (outside this repo) | Purpose |
|---|---|---|
| `agentic-os-fresh-install` | `~/git/test/agentic-os-fresh-install` | Curated Next.js+Supabase, populated. Confirm-only regression anchor (step 1) and the Stage 0 exemplar-de-leak proof. |
| `agentic-os-pytest-api-fixture` | `~/git/test/agentic-os-pytest-api-fixture` | Non-browser (pytest+FastAPI) test suite. Proves `test-automation-author.md`'s API/unit paradigm branch generalizes with zero page-object/DOM transplant. |
| `agentic-os-angular-mssql` | `~/git/test/agentic-os-angular-mssql` | Angular+Express+mssql, near-empty/greenfield (manifest only, no source files). Full-mode honest-degradation anchor (step 2) — proves low-confidence + `unresolved` beats a confident wrong guess. |
| `agentic-os-fastapi-alembic` | `~/git/test/agentic-os-fastapi-alembic` | FastAPI+SQLAlchemy+Alembic, populated (real migration + model + REST routes). Non-curated `migration-managed` generation anchor (step 3) — proves persistence generalizes beyond the three curated SQL stacks. |
| `agentic-os-express-mongoose` | `~/git/test/agentic-os-express-mongoose` | Express+Mongoose, populated (real schema files + REST routes, zero migration files). `model-defined-no-migration` generation anchor (step 3) — the schemaless make-or-break case: proves `gen/schema-architect` writes model files (not migrations) and `gen/migration-validator` correctly gates off. |
| `agentic-os-sveltekit` | `~/git/test/agentic-os-sveltekit` | SvelteKit, populated (real components + design tokens, zero backend). Non-curated `ui`/`component-framework` generation anchor (step 3) — proves `gen/component-generator` generalizes beyond React with zero React/Tailwind vocabulary transplant, despite sharing `schema-architect.md` (a persistence-focused file) as its only available structural exemplar. |
| `agentic-os-express-ejs` | `~/git/test/agentic-os-express-ejs` | Express+EJS, populated (real view + partial + route, zero client-side framework). Non-curated `ui`/`template-engine` generation anchor (step 3) — proves `gen/component-generator`'s claimed `template-engine` coverage (previously grounded only in the curated `rails.md` profile) also holds on a non-curated stack, with zero React/component-framework vocabulary transplant. |

Fixtures live outside this repo (own git history, throwaway) — see
`tests/README.md` § Known limitations for why nothing model-driven is
committed as a full fixture here.

## Stage 1 golden run (recorded result, not re-executed by CI)

Both steps above were run against the fixtures at Stage 1 shipping time:

- **Confirm-only** (`agentic-os-fresh-install`, matched profile
  `nextjs-supabase`): produced `capabilities.persistence.write_scope =
  "supabase/migrations/**"` and `capabilities.persistence.migrations_dir =
  "supabase/migrations/"` — an exact match to the profile's
  `{{MIGRATIONS_DIR}}` default. `server_writes`/`ui`/`i18n` confidence 95
  (re-run after a blind-review fix made the `gen/i18n-agent` conditional
  check explicit in `stack-discovery.md` § Process step 3 — `i18n.applies:
  false`, backed by a real manifest check: no `next-intl`/`next-i18next`
  dependency, no `messages/`/`locales/` dir). Zero `unresolved` entries.
- **Full mode** (`agentic-os-angular-mssql`, no Tier-1 match): `persistence`
  confidence 30, `server_writes` confidence 50, `ui` confidence 55 — all
  correctly below the 80 halt threshold, each with an `unresolved` entry
  naming the real ambiguity (e.g. "only the raw `mssql` driver dependency and
  an empty `server/db` directory exist; no migrations directory, no
  model/entity files" — candidates `migration-managed` |
  `model-defined-no-migration`). `i18n.applies: false` confidence 85 (clean
  absence check). No fabricated evidence anywhere.

## Stage 2 golden run (recorded result, not re-executed by CI)

The two highest-priority items from this program's fixture matrix — "backend
dev on an existing non-curated backend" and "schemaless Mongo, make-or-break
for the schemaless claim" — were run end-to-end (discovery → capability-driven
applicability → generation → independent audit):

- **`agentic-os-fastapi-alembic`** (no Tier-1 match, `full` mode): discovery
  resolved `persistence.paradigm = migration-managed` (confidence 90, real
  Alembic migration + matching SQLAlchemy models) and `server_writes.applies
  = true` (confidence 95, REST). Per the new Phase 5 applicability table this
  correctly makes `gen/schema-architect` **and** `gen/migration-validator`
  applicable. Generated `gen/schema-architect`: **95/100** on first audit
  (19/20 verified), zero Postgres/Supabase RLS vocabulary transplanted from
  the shared exemplar despite this repo having nothing to do with either —
  the one unverified claim (a reference to "the subagent gate") was a
  testing-methodology artifact (this fixture wasn't run through a full Phase
  4 scaffold, so the hook it referenced genuinely doesn't exist here — in a
  real install it would).
- **`agentic-os-express-mongoose`** (no Tier-1 match, `full` mode, the
  make-or-break schemaless case): discovery resolved
  `persistence.paradigm = model-defined-no-migration` (confidence 90, two
  real Mongoose schema files, explicitly confirmed **no** migrations
  directory anywhere). Per the applicability table `gen/schema-architect`
  applies but `gen/migration-validator` correctly does **not** (paradigm ≠
  `migration-managed`) — verified directly by asking the discovery run to
  state the applicability answer, not just infer it. Generated
  `gen/schema-architect` scored 90/100 on first audit (one self-referential
  claim — "no `.agentic/guides/` exists, verified by `find .agentic`" — false
  the instant the file itself was written under `.agentic/`, the same class
  of quine bug found in Stage 0's initial schema-architect regen). Fixed via
  the standard regenerate-with-findings retry (narrowed to `find
  .agentic/guides`) → re-audited at **95/100**, which also caught a *second*,
  new issue live: a rule citing `variable_defaults.GATE_COMMANDS` (an
  installer-internal field name) as its evidence — exactly the
  discovery-record-citation violation the Stage 1 rubric check was added to
  catch. Fixed (cited the real repo fact — `package.json` has no `scripts`
  key — instead of the internal variable name) → clean. **The
  migration-vocabulary-contamination check (the make-or-break test) passed
  on the very first generation**: zero instructions to write, verify, or
  reference a migration file/directory/diff-command anywhere in the
  generated contract.

Both fixtures prove the same thing from two directions: capability-driven
Phase 5 applicability correctly turns on/off the right slots per paradigm,
the paradigm-neutral exemplar generalizes to stacks with nothing in common
with the six curated ones, and the Stage 1 evidence-guarantee rubric check is
not just documented — it has already caught a real generation-time mistake
live, before this ever reached a real user's repo.

## Decision: paradigm fragments not added (Stage 3)

The original design for this universal-stack-support program reserved a seam
for **paradigm fragments** — pre-written, paradigm-specific rule blocks the
installer could append to a generated contract — but shipped zero of them,
with an explicit condition for adding any: only if a Stage 2 audit showed the
paradigm-neutral exemplar skeleton (Stage 0) still let a wrong-paradigm rule
through. Both
Stage 2 golden runs above included that exact check (Postgres/Supabase RLS
vocabulary on the Alembic fixture; migration-file vocabulary on the
schemaless Mongo fixture) and **both came back clean on first generation** —
the neutral skeleton alone was sufficient in both directions tested. Per
YAGNI, fragments stay unbuilt. This is a standing decision, not a gap: if a
future fixture (or a real install) surfaces a transplant the neutral skeleton
missed, that's the trigger to revisit it, not a schedule.

## What's proven vs. still open (as of Stage 3.2)

`generic-fallback.md`'s wording was corrected in Stage 3 to describe what
Stage 2's shipped code actually does — that's a documentation-accuracy fix,
safe regardless of fixture coverage, since it doesn't change behavior. It is
**not** the same claim as "the full capability-driven generation path is
proven end-to-end." What's actually verified by a live fixture run, as of
Stage 3.2:

- **Proven**: `persistence` (both `migration-managed` and
  `model-defined-no-migration`), `server_writes`, and `ui` in **both**
  paradigms (`component-framework` per Stage 3.1, `template-engine` per
  Stage 3.2 below) — every capability's every paradigm value now has at
  least one non-curated live proof.
- **Not yet run**: `i18n`/`gen/i18n-agent` on a non-curated fixture, and a
  zero-capability install (`pm-delivery`/`qa`-only role preset,
  `generated: []`) through this specific discovery-front-end path. The
  latter is lower risk than the rest of this list — Phase 5's "skip entirely
  when the union's `generated` set is empty" is unconditional, pre-existing
  logic this program never touched, and its role-preset combinatorics are
  already covered by the deterministic `check-presets.py` (T3) — but it has
  never been driven through a live `/agentic-init` run end-to-end either.

Re-run this procedure with those remaining fixtures before treating the
capability-driven generation path as fully proven across all four
capabilities and every paradigm within them.

## Stage 3.1 golden run — `ui` capability (recorded result, not re-executed by CI)

The highest-remaining-priority gap from the list above — `ui`/
`gen/component-generator` on a non-curated fixture — was closed:

- **`agentic-os-sveltekit`** (no Tier-1 match, `full` mode): discovery
  resolved `ui.paradigm = component-framework` (confidence 95, two real
  Svelte components with props/slots, a design-token CSS file consumed via
  `var(--...)`, and a route composing them) and correctly resolved
  `persistence`/`server_writes`/`i18n` all `applies: false` (confidence 90
  each — this fixture is a pure frontend, no backend at all). Generated
  `gen/component-generator` scored **100/100 on first audit** (25/25
  verified) — notably, this is the first capability whose generation slot
  has **no dedicated exemplar at all**: `gen/component-generator` shares
  `schema-architect.md` (a persistence-focused file) as its only available
  structural few-shot input, per the pre-existing (unchanged by this
  program) Phase 5 step 3 convention. The generated contract transplanted
  zero React/JSX/hooks/Tailwind vocabulary and zero
  persistence/migration/access-control vocabulary from that exemplar —
  grounding every rule in the real Svelte components instead (design-token
  ownership as the structural analog to the exemplar's access-control
  section). This is the strongest evidence yet that the paradigm-neutral
  *structure* Stage 0 established, not stack-specific *content*, is what
  actually generalizes.

## Stage 3.2 golden run — `ui` template-engine paradigm (recorded result, not re-executed by CI)

The remaining `ui` gap — `template-engine` had only ever been exercised on
the curated `rails.md` profile, never on a non-curated stack — was closed:

- **`agentic-os-express-ejs`** (no Tier-1 match, `full` mode): discovery
  resolved `ui.paradigm = template-engine` (confidence 98, a real EJS view
  including a real EJS partial via `<%- include(...) %>`, a route calling
  `res.render`, and `app.js` wiring `view engine`/`views`) and correctly
  resolved `persistence`/`i18n` `applies: false` (confidence 95 each — no
  ORM, no locale catalog) and `server_writes.applies: true` (confidence 85,
  the one Express route). Generated `gen/component-generator` scored
  **100/100 on first audit** (22/22 verified) — zero React/JSX/hooks/
  component-framework vocabulary and zero persistence/migration vocabulary
  transplanted from the shared `schema-architect.md` exemplar; every rule
  grounded in this repo's real EJS conventions (partial reuse, `res.render`
  locals as the data boundary, escaped-vs-unescaped output). Combined with
  Stage 3.1, both `ui` paradigm values now have independent non-curated
  proof — the Capability map's "`gen/component-generator` covers both
  `component-framework` and `template-engine`" claim is no longer grounded
  in the curated profiles alone.
