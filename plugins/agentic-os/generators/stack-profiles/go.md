# Stack profile: go

Go service or CLI.

## Detection markers

- `go.mod` at repo root (module path names the project)
- `main.go` or `cmd/<name>/main.go`

## Variable defaults

| Variable | Default |
|---|---|
| `{{MIGRATIONS_DIR}}` | `migrations/` or `db/migrations/` when present (golang-migrate / goose / atlas); **empty when absent** ⇒ migration hooks skipped |
| `{{GATE_COMMANDS}}` | `go vet ./...` · `go test ./...` · `golangci-lint run` (only when `.golangci.*` config exists) · `go build ./...` |
| `{{MIGRATION_DIFF_COMMAND}}` | tool-specific when a migration tool is detected (`migrate`, `goose status`, `atlas migrate validate`); empty otherwise |
| `{{ENV_CHECK_COMMANDS}}` | `go version` · `go build ./...` |
| `{{APP_START_COMMAND}}` | `go run .` (or `go run ./cmd/<name>` when `cmd/` layout is used) |
| `{{BASE_URL}}` | `http://localhost:8080` |

## Generated-agent slots that apply

`gen/api-author`, `gen/stack-guides` always. `gen/schema-architect` and
`gen/migration-validator` only when a migrations directory + tool is
detected. `gen/component-generator` and `gen/i18n-agent` normally do not
apply (no frontend); include only if a JS frontend module is detected
alongside.

## Capability map

Structured counterpart to "Generated-agent slots that apply" above, in the
exact field names `generators/stack-discovery.md`'s confirm-only mode emits
— read this table directly instead of re-deriving it from prose.

| Capability | `applies` | paradigm / style | `write_scope` |
|---|---|---|---|
| `persistence` | conditional — `true` only when a migrations directory + tool is detected, else `false` (`external-or-none` — plenty of Go services genuinely have no schema in-repo) | `migration-managed` (when present); `access_control_style`: no framework default, check for existing auth middleware first | `{{MIGRATIONS_DIR}}**` |
| `server_writes` | `true` | `api_style: "net/http handlers or the detected router (chi/gin/echo)"` | `internal/**`, `cmd/**` (respect existing package boundaries) |
| `ui` | conditional — `true` only when a JS frontend module is detected alongside, else `false` (no UI by default — Go services are typically API-only) | `component-framework` (when present) | the JS frontend's own component directory |
| `i18n` | conditional — same detection as `ui`, else `false` | n/a unless a JS frontend is present | n/a unless a JS frontend is present |

## Stack facts for the generators

- **Data access**: often no ORM — `database/sql` + sqlc/sqlx, or GORM/ent
  when the go.mod shows it. Match the existing choice; never introduce an
  ORM into a stdlib codebase.
- **API idiom**: `net/http` handlers or the router in go.mod (chi, gin,
  echo). Request validation explicit at the handler boundary; errors
  returned, not panicked; context.Context threaded through.
- **Project layout**: respect the existing layout (`cmd/`, `internal/`,
  `pkg/`) — `internal/` boundaries are import-enforced, generated agents'
  write scopes should follow package boundaries.
- **Test runner**: `go test` with table-driven tests; testify only when
  already a dependency. Golden files under `testdata/`.
- **Formatting**: `gofmt`/`goimports` is non-negotiable — gate agents flag
  unformatted diffs as `## Blocking`.
