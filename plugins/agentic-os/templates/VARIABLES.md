# Template variable & ID registry (append-only)

This file is the contract every template and every installer step reads.
**Append new entries; never rename or repurpose existing ones.**

## Rendering convention

Templates ending in `.tmpl` contain `{{VAR}}` placeholders replaced by
`/agentic-init` at scaffold time (no logic in templates; conditionals live in the
installer skill). Files without `.tmpl` are copied verbatim.

**Escaping is not optional.** In `.py.tmpl` and `.json.tmpl`, substitute a scalar
`{{VAR}}` with the **JSON-escaped body** of its value:

```python
json.dumps(value, ensure_ascii=False)[1:-1]
```

— the value with `"`, `\`, and control characters (including newlines) escaped, and
**no surrounding quotes**. The template already supplies the quotes; leave them
alone. JSON's escape syntax is a subset of Python's for these characters, so one
encoding serves both file types and every position: a whole literal
(`X = "{{VAR}}"`), an interpolated one (`"… ({{VAR}})"`), a triple-quoted block, or
a comment.

> **`ensure_ascii=False` is load-bearing.** With the default, an astral character
> such as U+1F600 is emitted as the surrogate pair `\ud83d\ude00`. A JSON reader
> recombines it; a **Python** string literal does not — the constant becomes two
> lone surrogates that compare unequal to the answer and raise `UnicodeEncodeError`
> when printed. Templates are written as UTF-8, so the character can stay itself.
> `check-render-escaping.py` fails if this is dropped.

> **Templates must quote with `"`, never `'`.** `json.dumps` does not escape an
> apostrophe, so `X = '{{VAR}}'` with the value `it's a repo` is a `SyntaxError`
> while `X = "{{VAR}}"` is fine. `check-render-escaping.py` **tokenises** every
> `.py.tmpl` and rejects a placeholder in a single-quoted string wherever it sits —
> including `ROOT / 'a/{{VAR}}'`, which a regex for `'{{VAR}}'` would miss. The same
> pass rejects a placeholder in *no* string at all (see `{{SCORE_THRESHOLD}}` below).
> JSON has no single-quoted strings, so `.json.tmpl` is unaffected.

Plain substitution here is a **silent, shipped bug**, not a style preference. Real
interview answers carry quotes:

| Answer | Plain substitution yields | Symptom |
|---|---|---|
| `alembic revision --autogenerate -m "<msg>"` | `X = "alembic … -m "<msg>""` | **`py_compile` exits 0** — Python reads the chained comparison `"…" < msg > ""` — then `NameError` at runtime. `/agentic-doctor` Check 2 reports green. |
| `test -n "$DATABASE_URL"` (last in a newline list) | `X = """…"$DATABASE_URL""""` | `SyntaxError`. Reorder the list and it compiles — the bug is *order-dependent*. |
| `sh -c "npm run dev"` | `"app_start_command": "sh -c "npm run dev""` | `sdlc/config.json` no longer parses. |

`tests/lib/check-render-escaping.py` renders every `.py.tmpl`/`.json.tmpl` under
these exact answers and asserts the output compiles, imports, parses, **and
round-trips** — every rendered constant still equal to the answer it came from.
Parsing alone is not enough: an escape that merely *strips* `"` also compiles and
parses, turning `sh -c "npm run dev"` into a different command and quietly disarming
the two `PreToolUse` block hooks. `tests/lib/check-hooks-import.py`, run against a
scaffold rendered from the same answers, asserts the reference installer applies the
rule end to end.

**Everywhere else, substitute the plain value.** `.md.tmpl` prose and fenced blocks
take no escaping — a Windows path would render as `C:\\dir` and a newline-list as
one `\n`-joined line. (No `.sh`/`.yml` template carries a placeholder today; if one
ever does, it needs its own quoting rule, not this one.)

Placeholders in `#` comments take the same escaping — harmlessly, and on purpose: a
newline in an unescaped comment would spill code into prose.

**Two positions are not string literals.** One is a genuine exemption; the other is
a security boundary:

- **List-valued variables in `.json.tmpl`** — the exemption. Rendered as JSON array
  elements, each item passed through `json.dumps` in full (**with** its quotes),
  comma-separated, so `[{{ESCALATE_ON}}]` becomes `["security","breaking-change",…]`.
- **`{{SCORE_THRESHOLD}}`** — the only placeholder in the whole template set that
  lands in a *code* position (`SCORE_THRESHOLD = {{SCORE_THRESHOLD}}`, in
  `instruction_gate.py.tmpl`, which Claude Code executes on `SubagentStart`).
  Escaping is a harmless no-op here and **could not protect it anyway**: any value
  that is a valid Python statement runs. `SCORE_THRESHOLD = 95; import os` compiles,
  imports cleanly, and passes every `/agentic-doctor` check. (Non-code garbage is
  caught by luck, not by a control: `high` raises `NameError` on import, `9 5` is a
  `SyntaxError`.)

  **Today this is latent, not live**: `/agentic-init` derives it as the constant
  `95` on no interview screen, so no user input reaches it. If it ever becomes an
  answer, validate at intake that it is a number — nothing downstream will.

  It is also the *only* sanctioned code position. `check-render-escaping.py`'s
  tokeniser fails any `.py.tmpl` placeholder that sits outside a string literal and
  is not listed in `render_rule.CODE_POSITION_VARS`, so a second sink cannot be added
  by accident.

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
| `{{GATE_ENTRIES}}` | **Derived** (not collected): the installer expands `{{GATE_COMMANDS}}` into one Markdown gate block each — the body of `quality-gates.md.tmpl § Gates`. Empty list ⇒ an "add a gate" note, never a blank registry. See `agentic-init/SKILL.md` Phase 4 step 5. | expanded from `{{GATE_COMMANDS}}` |
| `{{QA_GUIDE_ROWS}}` | **Derived** (not collected): the `PATTERNS.md` index rows for `test-design-pattern.md` and `flaky-protocol.md`, emitted **only when those guides are installed** (the `qa` preset). Empty otherwise — a preset that does not install them must not index them. Each row ends in a newline; the empty value collapses without breaking the GFM table. | the two rows if `guides/test-design-pattern` + `guides/flaky-protocol` are in the union, else empty |
| `{{HUMAN_GATED_COMMANDS}}` | Shell commands always blocked pending human action, newline list | `git push origin {{DEFAULT_BRANCH}}` + interview |
| `{{GUARDED_WRITE_PATHS}}` | Paths writable only via a named flow, newline list | empty + interview |
| `{{SECRET_DENY_PATTERNS}}` | File patterns agents must never read, newline list (only ever rendered inside fenced blocks / deny arrays) | `.env*`, `.auth/**`, `*token*.env` |
| `{{MIGRATIONS_DIR}}` | DB migrations directory (empty ⇒ migration hooks skipped) | stack-fact record (`capabilities.persistence.migrations_dir`) |
| `{{PERSISTENCE_WRITE_SCOPE}}` | Change-unit location for `gen/schema-architect`'s `write_scope` — the discovery record's `capabilities.persistence.write_scope`. Equals `{{MIGRATIONS_DIR}}**` for `migration-managed`; a model/schema directory for `model-defined-no-migration`; empty for `external-or-none` (slot suppressed). Diverges from `{{MIGRATIONS_DIR}}` only in the no-migration case — see `generators/stack-discovery.md`. | stack-fact record (Stage 1 defines it; Phase 5 starts consuming it in Stage 2) |
| `{{MIGRATION_DIFF_COMMAND}}` | Command to verify schema drift after migration edits | stack-fact record (`capabilities.persistence.migration_diff_command`) |
| `{{LINT_FIX_COMMAND}}` | Auto-fix lint command run on each saved source file (file path appended); empty ⇒ no fix pass | interview, stack-suggested (e.g. `npx eslint --fix` for JS/TS stacks) |
| `{{LINT_CHECK_COMMAND}}` | Lint check command re-run after the fix pass; remaining errors feed back into the same turn (exit 2). Empty ⇒ `hooks/lint-on-save` skipped | interview, stack-suggested (e.g. `npx eslint`) |
| `{{ENV_CHECK_COMMANDS}}` | SessionStart environment checks, newline list | stack-fact record (`variable_defaults.ENV_CHECK_COMMANDS`) |
| `{{HITL_MODE}}` | `strict` \| `gated-autonomous` \| `autonomous` | `gated-autonomous` (QA preset: `strict`) |
| `{{MAX_LOC}}` / `{{MAX_FILES}}` | AI-change size ceiling (breach ⇒ escalate) | `250` / `10` |
| `{{AUTONOMY_OVERRIDES}}` | **Derived** (not collected as a scalar): the `ai-policy.md` per-repo override block, one bullet per Screen-3 capability set stricter than its active-mode cell. `--defaults`/no-tightening ⇒ the "no overrides" note. See `agentic-init/SKILL.md` Screen 3 + Phase 4 step 5. | the "no overrides" note |
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
`hooks/precompact-checkpoint` → `precompact_checkpoint.py` ·
`hooks/session-learnings-notice` → `session_learnings_notice.py` ·
`hooks/context-monitor` → `context_monitor.py` ·
`hooks/prompt-scan-guard` → `prompt_scan_guard.py`.

**Hooks** — `hooks/precommit-review-gate`, `hooks/subagent-gate`, `hooks/instruction-gate`,
`hooks/instruction-stale-notice`, `hooks/write-scope-guard`, `hooks/session-bootstrap`,
`hooks/precompact-checkpoint`, `hooks/session-learnings-notice` (Stop advisory: detects
correction signals in the session transcript and nudges capturing the lesson via the
memory store; `AGENTIC_LEARNINGS_DISABLED=1` disables), `hooks/context-monitor`
(PostToolUse advisory: samples the transcript tail every 5th call and announces 65%/75%
context-usage thresholds once per level; early warning ahead of the PreCompact
checkpoint; env-tunable via `AGENTIC_CONTEXT_*`, `AGENTIC_CONTEXT_MONITOR_DISABLED=1`
disables), `hooks/prompt-scan-guard` (UserPromptSubmit: generic-shape secret/PII
detection — private keys, JWTs, credential assignments, basic-auth URLs, Luhn card
numbers, high-entropy tokens near credential keywords, natural-language disclosure,
emails; modes `warn` (default) / `block` / `audit` via `AGENTIC_PROMPT_SCAN_MODE`;
masked findings appended to `.agentic/state/prompt-scan-audit.jsonl`; complements the
`Read(.env*)` deny rules by covering the paste path), `hooks/settings-fragment`,
`hooks/human-gated-commands`
(→ `human_gated_commands.py.tmpl`, consumes `{{HUMAN_GATED_COMMANDS}}`),
`hooks/guarded-write-paths` (→ `guarded_write_paths.py.tmpl`, consumes
`{{GUARDED_WRITE_PATHS}}`; entries support an optional ` => <flow>` suffix naming the
allowed flow), `hooks/migration-notice` (→ `migration_notice.py.tmpl`, consumes
`{{MIGRATIONS_DIR}}` + `{{MIGRATION_DIFF_COMMAND}}`; installer skips it when
`{{MIGRATIONS_DIR}}` is empty), `hooks/lint-on-save` (→ `lint_on_save.py.tmpl`,
consumes `{{LINT_FIX_COMMAND}}` + `{{LINT_CHECK_COMMAND}}`; fix-then-check on
PostToolUse Write/Edit, exit 2 feeds remaining errors back same-turn, fails open
when the tool is missing; installer skips it when `{{LINT_CHECK_COMMAND}}` is
empty; `AGENTIC_LINT_ON_SAVE_DISABLED=1` disables at runtime).

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
