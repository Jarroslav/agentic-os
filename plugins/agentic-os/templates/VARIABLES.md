# Template variable & ID registry (append-only)

This file is the shared contract between parallel workstreams. **Append new entries;
never rename or repurpose existing ones without agreement across all active sessions.**

> Output-contract parser merged: `subagent_gate.py.tmpl` (strict fail-closed on
> SubagentStop, lenient on plain Stop); t0 cases in `tests/t0/run-output-contract.sh`
> (11 green). The verbatim `.py` interim copy has been removed. (Extension done by the
> orchestrator on the HITL gate's behalf.)

## Rendering convention

Templates ending in `.tmpl` contain `{{VAR}}` placeholders replaced literally by
`/agentic-init` at scaffold time (plain string substitution — no logic in templates;
conditionals live in the installer skill). Files without `.tmpl` are copied verbatim.
Exception for `.json.tmpl` files: list-valued variables (e.g. `{{ESCALATE_ON}}`,
`{{GATE_COMMANDS}}`) are rendered as JSON array elements — each item quoted,
comma-separated — so `[{{ESCALATE_ON}}]` becomes `["security","breaking-change",…]`.

## Variables

| Variable | Meaning | Default |
|---|---|---|
| `{{PROJECT_NAME}}` | Human name of the target project | git repo dir name |
| `{{STACK_SUMMARY}}` | One-paragraph detected stack description | stack-fact record (`stack_discovery.stack_summary`) |
| `{{DEFAULT_BRANCH}}` | Integration branch agents sync/PR against | detected (`main`/`dev`) |
| `{{AGENTS_CANONICAL_DIR}}` | Canonical agent-contract directory | `.agentic/agents/` |
| `{{SCORECARD_PATH}}` | Instruction-quality scorecard JSON | `docs/audits/instruction-scorecard.json` |
| `{{SCORE_THRESHOLD}}` | Default instruction-quality gate threshold (per-agent overrides recorded in scorecard) | `95` |
| `{{GATE_COMMANDS}}` | Quality-gate commands (lint/typecheck/test), newline list | stack-fact record (`variable_defaults.GATE_COMMANDS`) |
| `{{HUMAN_GATED_COMMANDS}}` | Shell commands always blocked pending human action, newline list | `git push origin {{DEFAULT_BRANCH}}` + interview |
| `{{GUARDED_WRITE_PATHS}}` | Paths writable only via a named flow, newline list | empty + interview |
| `{{SECRET_DENY_PATTERNS}}` | File patterns agents must never read, newline list (only ever rendered inside fenced blocks / deny arrays) | `.env*`, `.auth/**`, `*token*.env` |
| `{{MIGRATIONS_DIR}}` | DB migrations directory (empty ⇒ migration hooks skipped) | stack-fact record (`capabilities.persistence.migrations_dir`) |
| `{{PERSISTENCE_WRITE_SCOPE}}` | Change-unit location for `gen/schema-architect`'s `write_scope` — the discovery record's `capabilities.persistence.write_scope`. Equals `{{MIGRATIONS_DIR}}**` for `migration-managed`; a model/schema directory for `model-defined-no-migration`; empty for `external-or-none` (slot suppressed). Diverges from `{{MIGRATIONS_DIR}}` only in the no-migration case — see `generators/stack-discovery.md`. | stack-fact record (Stage 1 defines it; Phase 5 starts consuming it in Stage 2) |
| `{{MIGRATION_DIFF_COMMAND}}` | Command to verify schema drift after migration edits | stack-fact record (`capabilities.persistence.migration_diff_command`) |
| `{{ENV_CHECK_COMMANDS}}` | SessionStart environment checks, newline list | stack-fact record (`variable_defaults.ENV_CHECK_COMMANDS`) |
| `{{HITL_MODE}}` | `strict` \| `gated-autonomous` \| `autonomous` | `gated-autonomous` (QA preset: `strict`) |
| `{{MAX_LOC}}` / `{{MAX_FILES}}` | AI-change size ceiling (breach ⇒ escalate) | `250` / `10` |
| `{{ESCALATE_ON}}` | Risk flags that force human escalation, comma list | `security,breaking-change,migration,spend` |
| `{{ROLE_PRESETS_ACTIVE}}` | Installed role presets, comma list | from interview |
| `{{TICKET_ADAPTER}}` | Work-item system + access method (ADO / Linear MCP / Jira / GitHub / GitLab / none) | interview |
| `{{TICKET_PREFIX}}` | Work-item reference prefix in commits/titles | interview |
| `{{MR_ADAPTER}}` | MR/PR mechanism (`gh` / `glab` / MCP / none) | detected |
| `{{TEST_FRAMEWORK}}` | E2E/test framework for QA preset (playwright / cypress / other) | stack-fact record (`variable_defaults.TEST_FRAMEWORK`) |
| `{{APP_START_COMMAND}}` | Command to launch the app for verification | stack-fact record (`variable_defaults.APP_START_COMMAND`) |
| `{{BASE_URL}}` | Local base URL for feature verification | stack-fact record (`variable_defaults.BASE_URL`), fallback `http://localhost:3000` |
| `{{OUTPUT_CONTRACT_SECTIONS}}` | Agent output contract section list parsed by subagent-gate | `Summary,Why,Blocking,Non-blocking,Escalate to human` |
| `{{STAGING_ENV_NAME}}` | Name of the mutable (CRUD-allowed) environment | interview |
| `{{AGENTIC_OS_VERSION}}` | Product version stamped into managed blocks + install journal | plugin version |

## The stack-fact record (journal state, not a `{{VAR}}`)

`generators/stack-discovery.md` (Phase 1 step 4) produces a structured JSON
record — `journal.stack_discovery` — not a scalar template variable. It seeds
several of the scalars above (`{{STACK_SUMMARY}}`, `{{MIGRATIONS_DIR}}`,
`{{PERSISTENCE_WRITE_SCOPE}}`, `{{MIGRATION_DIFF_COMMAND}}`,
`{{GATE_COMMANDS}}`, `{{ENV_CHECK_COMMANDS}}`, `{{APP_START_COMMAND}}`,
`{{BASE_URL}}`, `{{TEST_FRAMEWORK}}`) but is itself richer: per-capability `applies` /
paradigm / `evidence` / `confidence` for `persistence`, `server_writes`,
`ui`, `i18n`. Full schema and derivation rules live in
`generators/stack-discovery.md` — do not duplicate the schema here, it will
drift.

## Template IDs

IDs are the stable names role presets and the installer reference. **ID → file mapping**
(the `.tmpl` suffix applies when the file contains `{{VAR}}` placeholders):

| ID prefix | Directory | Example |
|---|---|---|
| `hooks/<name>` | `templates/hooks/claude/` | `hooks/instruction-gate` → `templates/hooks/claude/instruction_gate.py.tmpl` |
| `hooks/settings-fragment` | `templates/hooks/` | `templates/hooks/settings-fragment.json.tmpl` |
| `githooks/<name>` | `templates/githooks/` | `templates/githooks/pre-commit` |
| `scripts/<name>` | `templates/scripts/` | `templates/scripts/install-git-hooks.sh` |
| `governance/<name>` | `templates/governance/` | `templates/governance/AGENTS.md.tmpl` |
| `policy/<name>` | `templates/policy/` | `templates/policy/ai-policy.md.tmpl` |
| `guides/<name>` | `templates/guides/standards/` | `templates/guides/standards/git-workflow.md` |
| `agents/<name>` (core set) | `templates/agents/core/` | `templates/agents/core/dispatcher.md.tmpl` |
| `agents/<name>` (QA set) | `templates/agents/qa/` | `templates/agents/qa/test-automation-author.md.tmpl` |
| `commands/<name>` | `templates/commands/core/` | `templates/commands/core/dispatch.md.tmpl` |
| `sdlc/<name>` | `templates/sdlc/` | `templates/sdlc/config.json.tmpl` |

Hook IDs map to these exact filenames (all other IDs map to their name verbatim):
`hooks/precommit-review-gate` → `precommit_review_gate.py` ·
`hooks/subagent-gate` → `subagent_gate.py.tmpl` ·
`hooks/instruction-gate` → `instruction_gate.py.tmpl` ·
`hooks/instruction-stale-notice` → `instruction_stale_notice.py` ·
`hooks/write-scope-guard` → `write_scope_guard.py.tmpl` ·
`hooks/session-bootstrap` → `session_start_bootstrap.py.tmpl` ·
`hooks/precompact-checkpoint` → `precompact_checkpoint.py`.

**Hooks** — `hooks/precommit-review-gate`, `hooks/subagent-gate`, `hooks/instruction-gate`,
`hooks/instruction-stale-notice`, `hooks/write-scope-guard`, `hooks/session-bootstrap`,
`hooks/precompact-checkpoint`, `hooks/settings-fragment`, `hooks/human-gated-commands`
(→ `human_gated_commands.py.tmpl`, consumes `{{HUMAN_GATED_COMMANDS}}`),
`hooks/guarded-write-paths` (→ `guarded_write_paths.py.tmpl`, consumes
`{{GUARDED_WRITE_PATHS}}`; entries support an optional ` => <flow>` suffix naming the
allowed flow), `hooks/migration-notice` (→ `migration_notice.py.tmpl`, consumes
`{{MIGRATIONS_DIR}}` + `{{MIGRATION_DIFF_COMMAND}}`; installer skips it when
`{{MIGRATIONS_DIR}}` is empty).

> **Note**: `settings-fragment.json.tmpl` is valid JSON with no placeholders — the
> newline-list variables live in the three companion hook templates above (injecting lists
> into JSON-escaped inline `python -c` strings was rejected as unrenderable by plain
> substitution). `{{SECRET_DENY_PATTERNS}}` defaults are baked into the fragment's
> `permissions.deny`; interview-provided extras are set-unioned in by the installer's
> deep-merge.
**Git layer** — `githooks/pre-commit`, `scripts/install-git-hooks`.
**Governance** — `governance/claude-section`, `governance/agents`, `governance/patterns`,
`governance/agent-registry`.
**Policy** — `policy/ai-policy`, `policy/escalation-policy`, `policy/safety-policy`.
**Guides** — `guides/git-workflow`, `guides/code-quality`, `guides/quality-gates`,
`guides/instruction-quality-rubric`, `guides/working-with-agents`, `guides/qa-strategy-stub`,
`guides/test-design-pattern`, `guides/flaky-protocol`.
**Agents (core)** — `agents/dispatcher`, `agents/blind-code-reviewer`, `agents/security-reviewer`,
`agents/instruction-auditor`, `agents/pr-pipeline-gate`.
**Agents (QA)** — `agents/test-case-generator`, `agents/test-automation-author`,
`agents/test-case-syncer`, `agents/test-failure-triage` (read-only debugger: classify →
ledger → root-cause; pairs with `guides/flaky-protocol`), `agents/work-item-creator`
(adapter-driven ticket/bug creation via `{{TICKET_ADAPTER}}`, human-confirmed writes).
**Commands** — `commands/pipeline-orchestrator`, `commands/dispatch`.
**SDLC adapters** — `sdlc/config`, `sdlc/project`.

**Generated slots** (produced by `generators/agent-generator.md`, not templates):
`gen/schema-architect`, `gen/api-author`, `gen/component-generator`, `gen/migration-validator`,
`gen/i18n-agent`, `gen/stack-guides`.
