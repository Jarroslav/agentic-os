# Stack profile: rails

Ruby on Rails application.

## Detection markers

- `Gemfile` with `rails`
- `config/application.rb`
- `bin/rails`

## Variable defaults

| Variable | Default |
|---|---|
| `{{MIGRATIONS_DIR}}` | `db/migrate/` |
| `{{GATE_COMMANDS}}` | `bundle exec rubocop` (when configured) · `bin/rails test` or `bundle exec rspec` (per detected framework) |
| `{{MIGRATION_DIFF_COMMAND}}` | `bin/rails db:migrate:status` + verify `db/schema.rb` (or `structure.sql`) is committed in sync — a dirty schema file after migrate is drift |
| `{{ENV_CHECK_COMMANDS}}` | `ruby -v` · `bundle check` |
| `{{APP_START_COMMAND}}` | `bin/rails server` |
| `{{BASE_URL}}` | `http://localhost:3000` |
| `{{HUMAN_GATED_COMMANDS}}` (recommended addition) | `RAILS_ENV=production bin/rails db:migrate` (and any other shared-environment name in use, e.g. `RAILS_ENV=staging bin/rails db:migrate`) — running migrations against a shared database is a standing human-gate for this stack (see "Stack facts" below). Use the environment-qualified form, not the bare `bin/rails db:migrate`: the bare form is a substring of this same profile's own `{{MIGRATION_DIFF_COMMAND}}` (`bin/rails db:migrate:status`), and the human-gated-command hook blocks on plain substring match — gating the bare form would also block that safe, read-only status check |

## Generated-agent slots that apply

`gen/schema-architect`, `gen/api-author`, `gen/component-generator`
(views/Hotwire/ViewComponent when the app renders HTML),
`gen/migration-validator`, `gen/i18n-agent` (Rails i18n is built in — apply
when `config/locales/` has more than the default file), `gen/stack-guides`.

## Capability map

Structured counterpart to "Generated-agent slots that apply" above, in the
exact field names `generators/stack-discovery.md`'s confirm-only mode emits
— read this table directly instead of re-deriving it from prose.

| Capability | `applies` | paradigm / style | `write_scope` |
|---|---|---|---|
| `persistence` | `true` | `migration-managed`; `access_control_style: "Pundit/CanCanCan policy objects (reuse the existing policy layer; never inline role checks when one exists)"` | `{{MIGRATIONS_DIR}}**` |
| `server_writes` | `true` | `api_style: "RESTful controllers, strong params"` | `app/controllers/**` |
| `ui` | `true` | `template-engine` (views/Hotwire/ViewComponent) — the one curated profile where `gen/component-generator` targets server-rendered views, not a component-framework | `app/views/**`, `app/components/**` |
| `i18n` | conditional — `true` only when `config/locales/` has more than the default file, else `false` | `catalog_format: "Rails i18n YAML"` | `config/locales/**` |

## Stack facts for the generators

- **ORM**: ActiveRecord. Migrations are timestamped
  `YYYYMMDDHHMMSS_<description>.rb`, reversible (`change` or explicit
  `up`/`down`); never edit an applied migration — add a new one.
  `db/schema.rb` is generated — agents never hand-edit it. Running
  migrations against shared databases is human-gated.
- **API idiom**: RESTful controllers, strong parameters
  (`params.require(...).permit(...)`) at every write boundary; serializers
  (jbuilder / ActiveModel::Serializer) per repo convention.
- **Auth/access**: whatever the Gemfile shows (Devise, Pundit/CanCanCan
  policies) — reuse policy objects, never inline role checks in controllers
  when a policy layer exists.
- **Test runner**: minitest (`test/`) or RSpec (`spec/`) — detect by
  directory; factories via FactoryBot when present.
- **Background jobs**: ActiveJob adapter per config — job classes, not
  inline threads.
