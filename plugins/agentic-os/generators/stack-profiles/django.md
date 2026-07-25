# Stack profile: django

Python web application on Django (optionally Django REST Framework).

## Detection markers

- `manage.py` at repo root
- `django` in `pyproject.toml` / `requirements*.txt` / `Pipfile`
- `settings.py` (or a settings package) with `INSTALLED_APPS`

## Variable defaults

| Variable | Default |
|---|---|
| `{{MIGRATIONS_DIR}}` | `<app>/migrations/` per Django app (glob: `**/migrations/*.py`) — list the actual apps at install time |
| `{{GATE_COMMANDS}}` | `python manage.py check` · linter from config (`ruff check .` / `flake8`) · `pytest` (or `python manage.py test` when pytest is absent) |
| `{{MIGRATION_DIFF_COMMAND}}` | `python manage.py makemigrations --check --dry-run` |
| `{{ENV_CHECK_COMMANDS}}` | `python --version` · `python manage.py check` |
| `{{APP_START_COMMAND}}` | `python manage.py runserver` |
| `{{BASE_URL}}` | `http://localhost:8000` |
| `{{HUMAN_GATED_COMMANDS}}` (recommended addition) | `python manage.py migrate` against a shared/staging/production database — applying migrations there is a standing human-gate for this stack (see "Stack facts" below); surface this addition explicitly at Screen 5 rather than assuming the generic default covers it |

## Generated-agent slots that apply

`gen/schema-architect` (writes models + runs `makemigrations` conceptually:
the agent edits `models.py` and generates the migration file for human
review), `gen/api-author`, `gen/migration-validator`, `gen/i18n-agent` (only
if `USE_I18N`/`locale/` directories are in use), `gen/stack-guides`.
`gen/component-generator` applies only when a JS frontend (its own
`package.json` with a framework dep) is detected alongside.

## Capability map

Structured counterpart to "Generated-agent slots that apply" above, in the
exact field names `generators/stack-discovery.md`'s confirm-only mode emits
— read this table directly instead of re-deriving it from prose.

| Capability | `applies` | paradigm / style | `write_scope` |
|---|---|---|---|
| `persistence` | `true` | `migration-managed`; `access_control_style: "Django auth + permission classes/decorators"` | `**/migrations/**` (per-app) |
| `server_writes` | `true` | `api_style: "DRF ViewSet/APIView"` when DRF is installed, else `"Django views + forms"` | `**/views.py`, `**/serializers.py`, `**/urls.py` |
| `ui` | conditional — `true` only when a separate JS frontend (`package.json` with a framework dependency) is detected alongside, else `false` | `component-framework` (when present) | the JS frontend's own component directory |
| `i18n` | conditional — `true` only when `USE_I18N`/`locale/` directories are in use, else `false` | `catalog_format: "Django gettext .po"` | `locale/**` |

## Stack facts for the generators

- **ORM**: Django ORM. Schema changes go through `models.py` +
  auto-generated migrations — hand-written migration files only for data
  migrations (`RunPython`) and must be reversible where possible.
  `migrate` against shared databases is human-gated.
- **API idiom**: DRF `ViewSet`/`APIView` with serializers when DRF is
  installed; plain Django views + forms otherwise. Validation lives in
  serializers/forms, never inline in views.
- **Auth/access**: Django auth + permission classes / decorators
  (`login_required`, DRF permissions). Look for custom permission classes
  before inventing checks.
- **Test runner**: pytest + pytest-django when present, else Django's
  test runner. Fixtures/factories (factory_boy) preferred over raw fixtures.
- **Settings/secrets**: env-driven settings (django-environ or similar);
  agents never read `.env*`.
