# Stack profile: playwright-taf

A dedicated test-automation framework (TAF) repo: the codebase *is* the test
suite, targeting an application deployed elsewhere. Derived from a production
TAF, generalized.

## Detection markers

- `playwright.config.ts` / `playwright.config.js` (or the config of
  `{{TEST_FRAMEWORK}}` when the interview overrides it — cypress.config.*)
- `@playwright/test` (or equivalent) in `package.json`
- Repo dominated by test assets: `tests/` + `pages/` (page objects) with
  little or no application source

## Variable defaults

| Variable | Default |
|---|---|
| `{{MIGRATIONS_DIR}}` | empty — no managed schema; migration hooks skipped |
| `{{GATE_COMMANDS}}` | `npm run lint` · `npx tsc --noEmit` (when TypeScript). **Test execution is NOT a gate command** — under the QA preset's strict policy agents recommend test commands, humans/CI run them |
| `{{MIGRATION_DIFF_COMMAND}}` | empty |
| `{{ENV_CHECK_COMMANDS}}` | `node --version` · check auth-state/storage-state files exist (path from the framework config) without reading them |
| `{{APP_START_COMMAND}}` | none — the app under test runs elsewhere; `{{BASE_URL}}` comes from the framework config / interview |
| `{{TEST_FRAMEWORK}}` | `playwright` |

## Generated-agent slots that apply

`gen/stack-guides` only (test-architecture facts feed the guides). The QA
writer agents are **templates**, not generated slots: `agents/test-case-generator`,
`agents/test-automation-author`, `agents/test-case-syncer`,
`agents/test-failure-triage`, `agents/work-item-creator` (see the qa preset).
No schema/api/component/i18n slots.

## Stack facts for the generators

- **Layering**: spec files (tests) → page objects → helpers/fixtures →
  API service classes. New page objects are re-exported from the domain
  index; reuse before creating.
- **Selector priority**: test-id attribute → role → text/label → CSS with a
  justifying comment. Auto-generated classes and tooltip attributes are
  never primary selectors.
- **Parallelism model**: default parallel; specs that mutate shared state
  (roles, settings, tenant-level records) carry the repo's serial /
  no-parallel tag and route to the matching config project.
- **Traceability**: test titles embed the tracker ID
  (`{{TICKET_PREFIX}}-<id> - ...`) so the configured work-item reporter can
  match results back to Test Case work items in `{{TICKET_ADAPTER}}`.
- **Logging**: a shared logging helper is mandatory in specs, page objects,
  and API layers — raw `console.log` is a review blocker.
- **Autonomy boundaries** (qa preset defaults): agents author code and run
  lint only; test execution is recommend-only; tracker writes are
  human-confirmed; size ceiling {{MAX_LOC}} LOC / {{MAX_FILES}} files per
  change; staging CRUD, production read-only.
