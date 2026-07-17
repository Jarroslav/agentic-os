# Repo survey: detecting stack, structure, and existing knowledge

Phase 1 reference for the repo-guides workflow. This pass is a read-only
reconnaissance: consume an audit, classify the repo shape, inventory modules, pin AI-tool
targets, extract the tech stack, gather per-category evidence, and detect the ticket adapter.
Its structured output is the sole input to Phase 2 planning.

> Blast radius: **R0** for the entire phase. You read; you never write. No file is created,
> edited, formatted, moved, deleted, or staged here — not even the discovered docs and
> entrypoints. Writes begin only in later phases, and only behind approval.

Downstream consumers: Phase 2 (planning/merge), Phase 4 (per-target diffs), and
`project.md` Step A (ticket-adapter fields). Upstream contract: the `repo-audit-guides` skill,
whose report format is shared verbatim (see below).

---

## 0. The no-write gate

Hold every write until all three hold:

1. the audit is complete,
2. the Phase 2 merge plan has been presented, and
3. the user has explicitly approved it.

Until then you operate strictly R0. There is no partial exception — a "quick fix" to a
malformed config, a "harmless" doc touch-up, and staging a rename are all writes and all wait.

---

## 1. Obtain the audit — first action, no exceptions

The audit is the single source of truth for assistant entrypoints, tool-specific directories,
Copilot setup, documentation surfaces across markdown files, prior agentic-sdlc state, evidence
quality flags, and the per-area foundation action. Get it before anything else, by the first
matching route:

| Order | Route | Condition |
|-------|-------|-----------|
| 1 | Invoke the `repo-audit-guides` skill | skill is listed |
| 2 | Accept a user-supplied recent report | it carries **all** required sections, readiness actions, and an evidence table — otherwise reject |
| 3 | Run an inline read-only audit under the identical output contract | no skill, no valid report; label the result **fallback** explicitly |

Never blend routes. A user report missing any required section is not "close enough" — fall
through to route 3.

### Required report sections (exact headings, verbatim)

```
# Knowledge Audit Report
## Executive Summary
## Documentation Map
## Documentation Analysis
## Assistant Setup Analysis
## Agentic Infrastructure Analysis
## Conflict And Overlap Analysis
## Foundation Readiness And Next Steps
## Evidence Appendix
```

### Evidence-quality flags and their posture

Each audited area carries a flag; the flag dictates how its material may enter a plan.

| Flag | Rating vocab | Plan posture |
|------|--------------|--------------|
| current | `strong` | keep as source of truth (unless the audit says `incorporate`) |
| partial | `partial` | merge only after approval |
| stale / weak | `weak` | ask, or skip |
| missing | `missing` | generate only from concrete repo evidence, post-approval; else skip |
| conflicting | `conflicting` | ask, or halt before encoding the conflict |

> Weak, ambiguous, or conflicting evidence is never upgraded into confident generated
> guidance. Ask, skip, or halt as the audit directs.

Foundation action vocabulary (the only allowed verbs per area): `preserve`, `incorporate`,
`replace`, `merge`, `skip`, `ask user`, `halt`.

---

## 2. Paths read during discovery

All read-only. Absence of a path is itself signal, not an error.

```
.agentic/guides/
.agentic/runs/
.agentic/agentic-sdlc/
<module>/.agentic/guides/
.agentic/guides/project.md          (section: ## Ticket Adapter)
.mcp.json
.claude/settings.json               (mcpServers)
.github/copilot-instructions.md
.copilot/
.claude/
.codex/
.agents/
.gemini/
AGENTS.md
CLAUDE.md
GEMINI.md
```

---

## 3. Repo shape

Classify as `monorepo` if **any** signal fires; otherwise `single`.

| Signal | Implication |
|--------|-------------|
| `pnpm-workspace.yaml` (root) | pnpm workspace |
| `lerna.json` (root) | Lerna |
| `turbo.json` (root) | Turborepo |
| `nx.json` (root) | Nx |
| `workspaces` array in root `package.json` | npm/yarn workspaces |
| multiple `package.json` excl. `node_modules` | JS multi-package |
| multiple `pom.xml` with `<modules>` | Maven multi-module |
| multiple `build.gradle` / `settings.gradle` include lines | Gradle multi-project |
| `[workspace]` in root `Cargo.toml` | Cargo workspace |
| `go.work` (root) | Go workspaces |
| 2+ top-level dirs each with own `src/` + manifest | heuristic monorepo |

---

## 4. Module inventory (monorepo only)

For each module, read its manifest and record one row. Single repos skip this entirely.

| Field | Source |
|-------|--------|
| path | module root |
| language | manifest |
| framework | manifest / dependency set |
| build | manifest scripts / build config |
| test | manifest scripts / test config |

Schema: `modules` `[{path, language, framework, build, test}]`.

---

## 5. AI-tool targeting

Detect which assistant surfaces exist and map each matched signal to its target entrypoint file.

| Signal present | Target file |
|----------------|-------------|
| `.claude/` | `CLAUDE.md` |
| `AGENTS.md` or `.codex/` | `AGENTS.md` |
| `.gemini/` or `GEMINI.md` | `GEMINI.md` |
| `.github/copilot-instructions.md` or `.copilot/` | `.github/copilot-instructions.md` |

Resolution:

- **Multiple matches** → all targets are in scope; each gets exactly one diff in Phase 4.
- **No match** → ask the user which target to adopt. Default to `CLAUDE.md` if they decline
  to choose — but a decline with an otherwise-empty signal set is a halt condition (§9).

Record `entrypoint_targets` and `existing_entrypoint_files`.

---

## 6. Tech-stack extraction

Per scope (repo root, and per module in a monorepo), pull the five required fields from standard
manifests:

| Field | Where to read |
|-------|---------------|
| language + version | `package.json` `engines`, `pyproject.toml` / `requirements.txt`, `pom.xml`, `go.mod`, `Cargo.toml` |
| framework + version | dependency declarations in the same manifests |
| build tool | manifest / build config |
| test framework | manifest / test config |
| lint tool | lint/formatter config |

Schema per scope: `stack_per_scope` `{language, framework, version, build, test, lint}`.

> Confidence bar: if confidence on **any** required stack field is below 80%, halt before
> Phase 2 and ask. Do not guess a version, framework, or runner to fill the slot.

---

## 7. Category evidence collection

Every guide category you intend to plant needs a concrete `file:line` citation. A category with
no evidence is dropped before Phase 2 — the sole exception is when the audit says `ask user` for
that category and the user then supplies evidence before approval.

Signals that count as evidence, per category:

| Category | Counts as evidence |
|----------|--------------------|
| Architecture | layer/folder layout, module boundaries, dependency direction |
| API | route registrations, controllers, endpoint decorators, OpenAPI/GraphQL schemas |
| Data | ORM models, migrations, repository classes, raw SQL |
| Testing | test dirs, framework configs (`vitest.config.*`, `jest.config.*`, `pytest.ini`, cargo test targets) |
| Development | custom error classes, logger setup, shared utils, component conventions |
| Integration | API clients, SDK usage, queue producers/consumers, webhook handlers |
| Workflows | state machines, workflow definitions, domain orchestrators |
| Security | auth middleware, authorization checks, input validators, secret handling |
| Standards | lint/formatter configs, commit and branch conventions |

Record `categories_with_evidence` as `scope → category → [file:line]`. Never fabricate a
citation to keep a category alive; a category without a real `file:line` is dropped.

---

## 8. Ticket-adapter detection

Run this **before** asking the user any question about ticket configuration. Results populate
`project.md` Step A.

### Signal order

1. existing `project.md` `## Ticket Adapter` section
2. grep entrypoints for `jira` / `linear` / `github issues` / `ticket` / `work-item` / MCP or skill names
3. `.mcp.json` `mcpServers`
4. `.claude/settings.json` `mcpServers`
5. skill list names containing `jira` / `linear` / `issue` / `ticket`
6. `git log --oneline -20` for a key prefix
7. `git branch -a` for a prefix
8. grep `README` / `CONTRIBUTING` for tracker keywords

Ticket key regex: `[A-Z]+-\d+` (e.g. `ABC-123`, `PROJ-42`).

Provider keyword map:

| Keyword | Provider |
|---------|----------|
| jira / atlassian / confluence | Jira |
| linear | Linear |
| github + (issue \| project) | GitHub Issues |
| azuredevops / ado / azure devops | Azure DevOps |
| asana | Asana |
| notion | Notion |

### Confidence and disposition

| Confidence | Condition | Disposition |
|------------|-----------|-------------|
| high | adapter source **and** key prefix both confirmed | configure |
| medium | provider known, adapter source unclear | configure provisionally; note the gap |
| low | prefix only | status `not configured`; note the prefix; prompt the user |
| none | zero signals | status `not configured`; **no** prompt |

Conflicting adapters — e.g. an MCP server and a skill both claim Jira — are not auto-resolved:
present both and let the user choose. Record the clash in `conflicts`.

### Adapter invocation shapes

**MCP adapter** — call pattern:

```
Call mcp__<server-id>__get_issue with issue_key=<ticket-id>
```

**Skill adapter** — five-field template, substitute `<skill-name>` (verbatim):

```
**Status**: configured
**Adapter**: Invoke the `<skill-name>` skill via the Skill tool.
**Lookup**: Invoke the `<skill-name>` skill with the ticket key and a request for summary, description, acceptance criteria, and links.
**Create**: Invoke the `<skill-name>` skill with the complete ticket payload or approved story file as the argument.
**Output**: Ticket key and URL returned by the skill.
```

> Skill-based adapters never expose the wrapped binary, the assistant ID, or CLI flags.
> Invocation is only through the Skill tool. Do not encode the underlying command anywhere.

### Stale stored config

A stored `## Ticket Adapter` config is **stale** if either:

- it carries fields **beyond** Status / Adapter / Lookup / Create / Output, or
- its `Adapter` line embeds a raw CLI command instead of a skill/MCP invocation.

On stale config: propose corrections and confirm with the user before any write. Never silently
keep a stale config, and never silently rewrite it.

---

## 9. Halt conditions (stop before Phase 2 and ask)

Halt on any one of:

- stack confidence < 80% on any required field;
- incomplete audit output;
- any `halt` planting recommendation from the audit;
- conflicting evidence touching entrypoint authority, managed-region integrity, guide source of
  truth, or quality-gate commands;
- no AI-tool signals **and** the user declines to pick a target;
- empty repo (no manifests, no source).

---

## 10. Output schemas

### Phase 1 output

```
{
  audit: {
    report_title,
    documentation_map,
    documentation_analysis,
    assistant_setup_analysis,
    agentic_infrastructure_analysis,
    conflict_and_overlap_analysis,
    foundation_readiness_and_next_steps,
    evidence_appendix: [{ claim, evidence, confidence }]
  },
  shape: "single | monorepo",
  modules: [{ path, language, framework, build, test }],
  entrypoint_targets,
  existing_entrypoint_files,
  existing_guides,
  documentation_sources_to_incorporate: [{ source, factory_destination, decision_needed }],
  stack_per_scope: { language, framework, version, build, test, lint },
  categories_with_evidence: { scope → category → [file:line] },
  confidence: { stack: "%", categories: "%", audit: "high | medium | low" }
}
```

### Ticket-detection output

```
{
  ticket_detection: {
    provider: "Jira | Linear | GitHub Issues | Azure DevOps | none | unknown",
    key_prefix,
    adapter_source: "mcp:<server-id> | skill:<skill-name> | none",
    adapter_instructions,
    lookup_op,
    create_op,
    output_format,
    confidence: "high | medium | low | none",
    conflicts
  }
}
```

---

## 11. Non-goals

- No file creation, editing, formatting, deletion, or staging in this phase.
- No editing of discovered docs or entrypoints — read-only through the audit.
- No guessing of stack or categories below the confidence bar; no fabricated evidence.
- No encoding of underlying CLI commands, flags, or binaries for skill-based ticket adapters.
- Not a user-facing tutorial — this is an executable reference for the pipeline phase.
