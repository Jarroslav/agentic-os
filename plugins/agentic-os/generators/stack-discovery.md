# stack-discovery — prompt template for the stack-fact record

`/agentic-init` Phase 1 step 4 runs this prompt as a subagent **once per
install**, after the orchestrating skill has computed a cheap **Tier-1
marker prior** (see below). The installer substitutes the `{{VAR}}`
placeholders and appends the input block described below before spawning.
Its output is the **structured stack-fact record** — installer journal state,
not a rendered file — that seeds `{{VAR}}`s (including the new
`{{PERSISTENCE_WRITE_SCOPE}}`, registry: `../templates/VARIABLES.md`), Phase 2
Screen 5, and (from Stage 2 onward) Phase 5's applicability filter.

## Why two tiers

A full repo inspection on every install is slow and, for the six curated
stacks, redundant — their `generators/stack-profiles/*.md` files already
encode accurate facts from real production repos. Tier 1 is a cheap,
deterministic check the *orchestrating skill* runs itself (no subagent): test
each curated profile's "Detection markers" section, in the fixed order
`nextjs-supabase`, `django`, `spring`, `rails`, `go`, `playwright-taf`, first
match wins. This produces a **prior**: a matched profile ID, or `none`.

Tier 2 is this subagent. The prior selects its **mode** — a purely
deterministic handoff, no confidence judgment involved: Tier 1 either matched
a curated profile or it didn't.

- **`confirm-only`** — a Tier-1 prior matched. Translate that profile's
  existing prose (Variable defaults + Stack facts sections) into the
  structured record below; do a light verification pass (confirm the
  detection markers are real, not stale — see Process step 1 below), not a
  full re-inspection. For the six curated stacks this must produce a record
  whose derived facts are **identical in substance** to what the installer
  already does today — this mode exists so curated-stack installs stay
  byte-unchanged, not so they get cheaper at the cost of accuracy. If your own
  step-1 re-check finds a marker is stale, fall back to `full` mode yourself
  (a concrete fact, not a judgment call) — Tier 1 does not pre-empt this by
  grading its own match strength.
- **`full`** — no Tier-1 match. Inspect the target repo directly —
  Glob/Grep/Read, no assumptions — and derive every field from real evidence.
  This is the path that makes a non-curated stack (a NestJS+TypeORM backend, a
  Svelte frontend, a schemaless Mongo service, or no stack at all for a
  PM/BA/QA-only install) produce a real record instead of falling through to
  `generic-fallback.md`.

## Inputs (appended below this prompt by the installer)

1. **Mode**: `confirm-only` or `full`.
2. **Tier-1 prior** (confirm-only only): the matched profile ID and the full
   text of `PLUGIN/generators/stack-profiles/<profile>.md`.
3. **Role preset union's `generated` set** (installer-owned; from Phase 2
   Screen 1) — **in the current installer flow this is always `null`**:
   Phase 1 step 4 (this subagent's caller) always runs before Phase 2, so
   there is never a resolved union to pass yet (see SKILL.md § Phase 1 step 4
   "Sequencing note"). The field is defined for a caller that *does* have the
   union available (a future phase-ordering change, or a direct invocation
   outside the normal install flow) — treat non-null as which of the four
   capabilities below are even relevant to ask about. A `pm-delivery`/`ba-po`/
   `qa`-only union has `generated: []` — skip straight to emitting a record
   with every capability `applies: false` and `confidence: 100` (there is
   nothing to discover; this is a true fact, not
   a guess), and do not spend tool calls inspecting for code capabilities
   the installed role will never use.

## The four capabilities (not a registry — these are the existing `gen/*` slots)

Each capability maps 1:1 to an existing generated-agent slot from Phase 5's
slot table (`skills/agentic-init/SKILL.md` § Phase 5 step 2). Discovery does
not invent a fifth: test-authoring stays the QA preset's template agents
(`agents/test-automation-author` etc.), never a `gen/*` slot, so it is out of
scope here.

- **`persistence`** → `gen/schema-architect` (+ `gen/migration-validator`).
  Paradigm enum:
  - `migration-managed` — schema lives in versioned migration files (SQL
    migrations, Alembic, EF Core, Flyway, ActiveRecord, golang-migrate,
    Prisma Migrate, TypeORM migrations, …). Evidence: a migrations directory
    with timestamped/sequential files.
  - `model-defined-no-migration` — schema lives in model/entity/schema
    definitions applied by the framework, not versioned migration files
    (Mongoose schemas, Prisma `db push`, TypeORM `synchronize: true`,
    repo-visible IaC for a managed datastore). Evidence: model files with no
    sibling migrations directory, or an explicit `synchronize`/`db push`
    config.
  - `external-or-none` — no schema representation in this repo at all
    (console-managed datastore, or the service is stateless). Evidence:
    absence — no ORM, no migrations dir, no model files, and (for `full`
    mode) no `gen/schema-architect`-relevant dependency in the manifest.
- **`server_writes`** → `gen/api-author`. No paradigm enum — just
  `applies: bool` plus a descriptive `api_style` (`REST`, `GraphQL`, `RPC`,
  `Server Actions`, …). Evidence: route/controller/resolver/action files.
- **`ui`** → `gen/component-generator`. Paradigm enum:
  - `component-framework` — React, Vue, Svelte, Angular, SolidJS, … Evidence:
    the framework dependency + component files under a conventional dir.
  - `template-engine` — server-rendered views (Rails views, Django
    templates, Blade, Razor, Jinja, …). Evidence: template files + a
    rendering call in the framework's controller/handler layer.
  - `none` — no UI surface in this repo (API-only service, CLI, TAF).
- **`i18n`** → `gen/i18n-agent`. No paradigm enum — `applies: bool` plus a
  descriptive `catalog_format` (`next-intl JSON`, `rails-i18n YAML`,
  `gettext .po`, …). Evidence: a locale/message catalog directory or an i18n
  library dependency.

## Process — `confirm-only` mode

1. Read the matched profile's "Detection markers" section; confirm each
   marker is actually present in the target repo (`Glob`/`Read` — do not
   trust the Tier-1 prior blindly, it is a cheap heuristic, not a guarantee).
   If a marker turns out stale (file absent despite the prior match), **fall
   back to `full` mode** — do not emit a confirm-only record built on a false
   premise.
2. Read the profile's "Capability map" section (all six curated profiles have
   one) — it already carries `applies`/paradigm/`write_scope` in this
   record's exact field names, so this step is a **direct copy**, not
   interpretation. A profile without a "Capability map" (only possible for a
   future 7th curated profile added before its own map is written) falls
   back to translating "Variable defaults" + "Stack facts for the
   generators" prose instead — same result, more work, more room for drift;
   the map exists precisely to avoid needing this fallback. Also read
   "Variable defaults" for everything the Capability map doesn't restate:
   the five generic `variable_defaults.*` scalars (`GATE_COMMANDS`,
   `ENV_CHECK_COMMANDS`, `APP_START_COMMAND`, `BASE_URL`, `TEST_FRAMEWORK`)
   plus the persistence-scoped `migrations_dir`/`migration_diff_command`
   fields (`{{MIGRATIONS_DIR}}`/`{{MIGRATION_DIFF_COMMAND}}` in that table —
   capability-scoped per the note below the JSON schema, not generic
   scalars, but still sourced from this section, not the Capability map).
   Every confirm-only field's evidence is "the matched profile `<id>`,
   confirmed against `<the real marker file>`," not a fresh repo-wide
   search.
3. `confidence: 95` for every capability the map marks unconditional (high,
   not 100 — a curated profile is a strong prior, not a certainty; Screen 5
   still surfaces it for confirmation). A capability the map marks `false`
   gets `confidence: 100` (their absence is the profile's own explicit
   claim). **A capability the map marks conditional** (e.g. nextjs-supabase's
   i18n row: "`true` only when `next-intl`/`next-i18next` is in the
   manifest") is not unconditional — actually check that condition against
   the real manifest (one `Read`/`Grep` call, not a full re-inspection)
   rather than defaulting to `applies: true`; set `confidence: 95` either way
   since the *check itself* is a real fact, only the boolean result depends
   on it.

## Process — `full` mode

1. Read the target repo's manifest(s) (`package.json`, `pyproject.toml`,
   `pom.xml`, `Gemfile`, `go.mod`, `Cargo.toml`, `*.csproj`, …) and top-level
   structure first — this alone resolves most capabilities' `applies` flag
   before any deeper search.
2. For each of the four capabilities the role union's `generated` set makes
   relevant (input 3): search for the evidence signals under "The four
   capabilities" above. `Glob`/`Grep`/`Read` — never assume a paradigm from
   the language alone (e.g. a Node repo is not automatically
   `migration-managed`; confirm an actual migrations directory or ORM
   `synchronize` config exists).
3. **Evidence discipline** (same rule as the generator prompts consume from
   this record — see below): every non-null field carries at least one real
   `file:line` (or `file` for a directory/config-presence fact) in its
   `evidence` array. A field with no evidence is `null`, not guessed.
4. **Confidence scoring per capability**: `0-100`, roughly — a single strong,
   unambiguous signal (a real migrations dir with real files) scores 85-95;
   a signal that requires interpretation (e.g. one model file, no migrations
   dir, ambiguous whether that's `model-defined-no-migration` or an
   unfinished `migration-managed` setup) scores 40-70; no signal at all for a
   capability that plausibly *could* apply scores below 40.
5. **Below 80 → do not silently pick one.** Set the field to your best guess
   but add an entry to the record's top-level `unresolved` array naming the
   capability, the ambiguity, and the candidate values — Phase 2 Screen 5
   (from Stage 2 onward) asks the human this specific question instead of a
   generic "confirm the stack" screen. This mirrors the bundled
   `agentic-sdlc` repo-guides skill's halt-below-80 convention,
   reimplemented here rather than invoked at runtime (no cross-plugin
   coupling).
6. A capability whose `applies` is unambiguously `false` (nothing in the
   manifest or file tree suggests it) still needs a positive absence check,
   not silence — state what you checked and found nothing (e.g. "no ORM
   dependency, no migrations dir, no model files — checked `package.json`
   dependencies and did a repo-wide `Glob` for `**/migrations/**` and
   `**/models/**`").

## Output — the structured stack-fact record

Your final message is a short human-readable summary (2-4 sentences: mode,
matched profile if any, capabilities found, anything unresolved), followed by
exactly one fenced ` ```json ` block containing:

```json
{
  "mode": "confirm-only | full",
  "matched_profile": "<profile-id> | null",
  "stack_summary": "<one paragraph>",
  "capabilities": {
    "persistence": {
      "applies": true,
      "paradigm": "migration-managed | model-defined-no-migration | external-or-none | null",
      "write_scope": "<glob, e.g. supabase/migrations/**> | null",
      "migrations_dir": "<path> | null",
      "migration_diff_command": "<command> | null",
      "access_control_style": "<short descriptive string, e.g. 'Postgres RLS'> | null",
      "evidence": ["<path:line>", "..."],
      "confidence": 0
    },
    "server_writes": {
      "applies": true,
      "api_style": "<REST | GraphQL | RPC | Server Actions | ...> | null",
      "write_scope": "<glob> | null",
      "evidence": ["<path:line>", "..."],
      "confidence": 0
    },
    "ui": {
      "applies": true,
      "paradigm": "component-framework | template-engine | none | null",
      "write_scope": "<glob> | null",
      "evidence": ["<path:line>", "..."],
      "confidence": 0
    },
    "i18n": {
      "applies": true,
      "catalog_format": "<short descriptive string> | null",
      "write_scope": "<glob> | null",
      "evidence": ["<path:line>", "..."],
      "confidence": 0
    }
  },
  "variable_defaults": {
    "GATE_COMMANDS": "<newline-list or empty>",
    "ENV_CHECK_COMMANDS": "<newline-list or empty>",
    "APP_START_COMMAND": "<command or empty>",
    "BASE_URL": "<url or empty>",
    "TEST_FRAMEWORK": "<name or empty>"
  },
  "unresolved": ["<capability>.<field> — <why, and the candidate values>", "..."]
}
```

`{{PERSISTENCE_WRITE_SCOPE}}` is `capabilities.persistence.write_scope`
verbatim (empty when `applies` is `false`). `{{MIGRATIONS_DIR}}` stays
`capabilities.persistence.migrations_dir` — the two diverge only for
`model-defined-no-migration`, where there is a write location but no
migrations directory. `{{MIGRATION_DIFF_COMMAND}}` is
`capabilities.persistence.migration_diff_command` verbatim — it lives under
`capabilities.persistence`, not `variable_defaults`, because it is
persistence-scoped (empty when `persistence.applies` is `false`), unlike the
other five `variable_defaults` scalars, which apply regardless of which
capabilities the repo has.

## Evidence guarantee — for the generator prompts that consume this record

`generators/agent-generator.md` and `generators/guide-generator.md` treat
every field in this record as an **unverified hint**, never a fact to cite
directly: they re-verify each cited path/paradigm against the live repo and
cite `file:line` in the *generated* contract. A generated contract may never
say "per the stack-discovery record" as its evidence — only a real repo
citation counts. This record exists to save the generator a rediscovery pass
and to catch cases where its own confidence was too low to trust silently
(the `unresolved` array); it is not a source of truth to quote.

## Self-check before finishing

- Every `evidence` entry is a real `path:line` you actually read (verify
  with a tool call, not memory) — or a real directory/config-presence fact
  for a signal that isn't line-addressable.
- No capability has non-null `paradigm`/`api_style`/`catalog_format` with an
  empty `evidence` array.
- `confirm-only` mode: you re-confirmed the Tier-1 marker before trusting it;
  if it was stale, you switched to `full` mode and said so in the summary.
- The JSON block is valid JSON (no trailing commas, no comments) and contains
  exactly the keys shown above — the installer parses it structurally.
