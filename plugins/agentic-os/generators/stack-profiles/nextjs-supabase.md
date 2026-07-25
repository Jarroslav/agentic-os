# Stack profile: nextjs-supabase

Next.js (App Router) frontend + Supabase (Postgres, Auth, Storage, Realtime)
backend. Derived from a production forum codebase.

## Detection markers

- `package.json` with `next` dependency **and** (`@supabase/supabase-js` or `@supabase/ssr` dependency or `supabase/config.toml` present)
- `supabase/migrations/` directory
- `app/` directory (App Router) — `pages/` alone means older Next.js; profile still applies

## Variable defaults

| Variable | Default |
|---|---|
| `{{MIGRATIONS_DIR}}` | `supabase/migrations/` |
| `{{GATE_COMMANDS}}` | `npx tsc --noEmit` · `npm run lint -- --max-warnings 0` · `npm test` (prefer a repo-defined aggregate like `npm run gate` when the manifest has one) |
| `{{MIGRATION_DIFF_COMMAND}}` | `npx supabase db diff` (prefer a repo alias like `npm run supabase:diff`) |
| `{{ENV_CHECK_COMMANDS}}` | `node --version` · check `.env.local` exists · `npx supabase status` (local stack, if `supabase/config.toml` present) |
| `{{APP_START_COMMAND}}` | `npm run dev` |
| `{{BASE_URL}}` | `http://localhost:3000` |
| `{{HUMAN_GATED_COMMANDS}}` (recommended addition) | `supabase db push --linked` — applying migrations to a linked/remote database is a standing human-gate for this stack (see "Stack facts" below); the installer's own generic default is `git push origin {{DEFAULT_BRANCH}}` alone, so surface this addition explicitly at Screen 5 rather than assuming the generic default covers it |

## Generated-agent slots that apply

`gen/schema-architect`, `gen/api-author`, `gen/component-generator`,
`gen/migration-validator`, `gen/i18n-agent` (only if an i18n library such as
`next-intl` / `next-i18next` is in the manifest), `gen/stack-guides`.

## Capability map

Structured counterpart to "Generated-agent slots that apply" above, in the
exact field names `generators/stack-discovery.md`'s confirm-only mode emits
— read this table directly instead of re-deriving it from prose.

| Capability | `applies` | paradigm / style | `write_scope` |
|---|---|---|---|
| `persistence` | `true` | `migration-managed`; `access_control_style: "Postgres RLS"` | `{{MIGRATIONS_DIR}}**` |
| `server_writes` | `true` | `api_style: "Server Actions"` (+ `app/api/**` routes when present) | `app/_actions/**`, `app/api/**` |
| `ui` | `true` | `component-framework` (React) | `components/**`, `app/**/*.tsx` |
| `i18n` | conditional — `true` only when `next-intl`/`next-i18next` is in the manifest, else `false` | `catalog_format: "next-intl/next-i18next JSON"` | `messages/**` |

## Stack facts for the generators

- **Database**: Postgres via Supabase. Row Level Security is the access-control
  layer — every `CREATE TABLE` ships RLS enablement + policies in the same
  migration file. Migration naming: `YYYYMMDDHHmmss_<description>.sql`.
  Applying to a linked/remote database (`supabase db push --linked`) is
  human-gated.
- **Server writes**: Next.js Server Actions are the mutation idiom —
  validation (typically Zod) at the top, structured `{ ok } | { error }`
  returns, never throw across the boundary. API routes (`app/api/`) follow a
  request-validated, enveloped-response pattern.
- **Auth**: Supabase Auth; session read server-side via cookies. Look for a
  `requireProfile()`/`getUser()`-style helper and reuse its semantics.
- **Frontend**: React server + client components; Tailwind is common — check
  for a design-token contract before hardcoding colors.
- **Test runner**: vitest or jest for unit (check manifest), Playwright for
  e2e when `playwright.config.*` exists.
- **Types**: a generated DB types file (e.g. `lib/supabase/types.ts` via
  `supabase gen types`) is the typed schema reference — generated agents read
  it, never edit it.
