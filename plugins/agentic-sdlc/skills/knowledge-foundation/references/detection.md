# Audit and Detection — Phase 1 Reference

Read-only audit of repository documentation, AI assistant setup, existing agentic infrastructure, project shape, modules, AI tool target, tech stack, and category evidence. No writes.

## Audit first

Before any repository analysis, planning, generation, or entrypoint wiring, Phase 1 must invoke or consume `knowledge-auditor` output. Running or validating the audit is the first action of knowledge-foundation.

- If `knowledge-auditor` is available in the host skill list, invoke it and use its structured `# Knowledge Audit Report` as the required Phase 1 input.
- If the user supplies a recent `knowledge-auditor` result, consume it only if it contains the required top-level audit sections, foundation readiness actions, and evidence table.
- If neither is available, perform the read-only audit inline using the same output contract as `knowledge-auditor`; clearly label this as a fallback audit.

The audit must include these sections before Phase 2 can begin:

- `# Knowledge Audit Report`
- `## Executive Summary`
- `## Documentation Map`
- `## Documentation Analysis`
- `## Assistant Setup Analysis`
- `## Agentic Infrastructure Analysis`
- `## Conflict And Overlap Analysis`
- `## Foundation Readiness And Next Steps`
- `## Evidence Appendix`

Preserve the no-write gate: do not create, update, format, delete, or stage files until the audit is complete, the Phase 2 incorporation and merge plan is presented, and the user explicitly approves.

## Audit-derived inputs

Use the audit as the source of truth for:

- Existing assistant entrypoints such as `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md`.
- Existing tool-specific directories such as `.claude/`, `.codex/`, `.agents/`, `.gemini/`, `.github/`, `.copilot/`, and similar assistant setup.
- Existing GitHub Copilot setup such as `.github/copilot-instructions.md`, workspace instructions, or custom prompt files.
- Documentation surfaces and references discovered across `*.md` files, including docs that point to other docs or external runbooks.
- Existing agentic-sdlc state such as `.agentic/guides/`, `.agentic/runs/`, `.agentic/agentic-sdlc/`, and managed regions when the audit includes them.
- Documentation and setup findings that indicate current, partial, stale, missing, or conflicting evidence.
- Foundation actions from `Foundation Readiness And Next Steps`: `preserve`, `incorporate`, `replace`, `merge`, `skip`, `ask user`, or `halt`.

If audit evidence is weak, missing, ambiguous, or conflicting for a guide category, command, target file, or managed region, do not convert it into confident generated guidance. Ask the user, skip the area, or halt according to the audit recommendation.

## Project shape

Single repo unless any of these monorepo signals are present:

| Signal | Where to look | Implies |
|---|---|---|
| `pnpm-workspace.yaml` | repo root | pnpm monorepo |
| `lerna.json` | repo root | Lerna monorepo |
| `turbo.json` | repo root | Turborepo |
| `nx.json` | repo root | Nx workspace |
| `workspaces` array in root `package.json` | repo root | npm/yarn workspaces |
| Multiple `package.json` files (excluding `node_modules`) | recursive | JS multi-package |
| Multiple `pom.xml` with `<modules>` | recursive | Maven multi-module |
| Multiple `build.gradle` / `settings.gradle` `include` lines | recursive | Gradle multi-project |
| `[workspace]` section in root `Cargo.toml` | repo root | Cargo workspace |
| `go.work` | repo root | Go workspaces |
| 2+ top-level dirs each containing their own `src/` + manifest | recursive | Heuristic monorepo |

If none → single repo.

## Modules (monorepo only)

For each module, capture:
- Path (relative to repo root)
- Language (from manifest)
- Framework (from manifest dependencies)
- Build/test commands (from manifest scripts)

## AI tool target

| Signal | Target file |
|---|---|
| `.claude/` exists | `CLAUDE.md` |
| `AGENTS.md` exists or `.codex/` exists | `AGENTS.md` |
| `.gemini/` exists or `GEMINI.md` exists | `GEMINI.md` |
| `.github/copilot-instructions.md` or `.copilot/` exists | `.github/copilot-instructions.md` |
| Multiple of the above | All matched targets (one diff per target in Phase 4) |
| None | Ask user; default `CLAUDE.md` |

## Existing docs to read through the audit (do not edit)

- Existing entrypoint(s): `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` at root.
- Existing Copilot entrypoint(s): `.github/copilot-instructions.md`, `.copilot/`.
- Existing guides: `.agentic/guides/`, `<module>/.agentic/guides/` when included by the audit.
- `README.md`, `CONTRIBUTING.md`, `docs/`, `*.md` ADRs, runbooks, architecture notes, onboarding guides, and Markdown files that contain documentation references.

## Tech stack per scope

For root (single) or each module (monorepo), extract:
- Language + version (from `package.json` engines, `requirements.txt`/`pyproject.toml` python_requires, `pom.xml` java.version, `go.mod` go directive, `Cargo.toml` rust edition).
- Framework + version (from primary dependency, e.g. `react`, `next`, `express`, `fastapi`, `spring-boot`, `axum`).
- Build tool (`vite`, `webpack`, `tsup`, `gradle`, `maven`, `cargo`).
- Test framework (`vitest`, `jest`, `pytest`, `junit`, `go test`, `cargo test`).
- Lint tool (`eslint`, `ruff`, `golangci-lint`, `clippy`).

If confidence is below 80% for any of these → halt before Phase 2 and ask user to confirm.

## Category evidence

Required: every category in the plan must have a concrete `file:line` reference from the codebase.

| Category | Evidence signals |
|---|---|
| Architecture | Layer/folder organization, module boundaries, dependency direction |
| API | Route registrations, controllers, endpoint decorators, OpenAPI/GraphQL schemas |
| Data | ORM model files, migration files, repository classes, raw SQL files |
| Testing | Test directories, test framework configs (`vitest.config.*`, `jest.config.*`, `pytest.ini`, `cargo test` targets) |
| Development | Custom error classes, logger setup, shared utilities, component conventions |
| Integration | API clients, SDK usages, queue producers/consumers, webhook handlers |
| Workflows | State machines, workflow definitions, domain orchestrators |
| Security | Auth middleware, authorization checks, input validators, secret handling |
| Standards | Lint configs, formatter configs, commit conventions, branch conventions |

Categories without evidence are **dropped before Phase 2** and never reach generation unless the audit recommendation is `ask user` and the user supplies concrete evidence before approving the plan.

Audit ratings affect categories as follows:

| Audit rating | Plan posture |
|---|---|
| `strong` | Preserve as source of truth unless the audit says foundation should incorporate it into factory-owned guidance. |
| `partial` | Merge with generated guidance after approval. |
| `weak` | Ask the user for context or skip; do not generate confident guidance from weak docs alone. |
| `missing` | Generate only from concrete repository evidence after approval; otherwise skip. |
| `conflicting` | Ask the user or halt before planning writes that would encode the conflict. |

## Phase 1 output (used by Phase 2)

A structured discovery summary:

```
audit: {
  report_title: "# Knowledge Audit Report",
  documentation_map: [paths, purpose, freshness signal, foundation action],
  documentation_analysis: [topic, source, reliable evidence, gaps, foundation action],
  assistant_setup_analysis: [surface, role, authority, problems, foundation action],
  agentic_infrastructure_analysis: [asset group, inventory, role, alignment, foundation action],
  conflict_and_overlap_analysis: [conflict, evidence, impact, required decision],
  foundation_readiness_and_next_steps: [area, finding, foundation action, next step],
  evidence_appendix: [list of {claim, evidence, confidence}]
}
shape: single | monorepo
modules: [list of {path, language, framework, build, test}]   # monorepo only
entrypoint_targets: [CLAUDE.md | AGENTS.md | GEMINI.md ...]
existing_entrypoint_files: [paths]
existing_guides: [paths]
documentation_sources_to_incorporate: [list of {source, factory_destination, decision_needed}]
stack_per_scope: { <scope>: {language, framework, version, build, test, lint} }
categories_with_evidence: { <scope>: { <category>: [file:line, ...] } }
confidence: {stack: %, categories: %, audit: high|medium|low}
```

## Ticket Adapter Detection

Run these checks before asking the user anything about ticket configuration. Results feed directly into `project.md` Step A.

### Detection signals (check in this order)

| Signal | How to check | What to extract |
|---|---|---|
| Existing `.agentic/guides/project.md` | Read `## Ticket Adapter` section | Already configured — but check for staleness: if any field outside Status/Adapter/Lookup/Create/Output is present, OR if `**Adapter**` encodes an underlying CLI command rather than a skill/MCP invocation → mark as stale, propose corrected values, and confirm with user before writing. Do not silently preserve stale configs. |
| Existing entrypoint (`AGENTS.md`, `CLAUDE.md`) | Grep for `jira`, `linear`, `github issues`, `ticket`, `work.item`, `MCP`, adapter skill name | Prior adapter instructions; incorporate into the section |
| `.mcp.json` at repo root | Read and scan `mcpServers` keys and `command`/`url` values | Match against provider keywords below |
| `.claude/settings.json` → `mcpServers` | Read and scan keys/values | Same |
| Available skill list shown in the conversation | Check for names containing `jira`, `brianna`, `linear`, `issue`, `ticket` | Skill-based adapter |
| Recent commit messages | `git log --oneline -20` | Ticket key prefix pattern `[A-Z]+-\d+` (e.g. `EPM`, `PROJ`) |
| Recent branch names | `git branch -a` | Same prefix pattern |
| `README.md`, `CONTRIBUTING.md` | Grep for `jira`, `linear`, `github issues`, `tracker`, `board` | Provider name and project key |

### Provider keyword mapping

| Keyword found | Provider |
|---|---|
| `jira`, `atlassian`, `confluence` | Jira |
| `linear` | Linear |
| `github` + (`issue` or `project`) | GitHub Issues |
| `azuredevops`, `ado`, `azure devops` | Azure DevOps |
| `asana` | Asana |
| `notion` | Notion |

### Translating a detected MCP server into adapter instructions

When an MCP server is found:
1. Read its `command` or `url` to identify the server binary or endpoint.
2. List what tool names the server exposes (e.g. `get_issue`, `update_issue`, `create_issue`).
3. Write the adapter instructions as exact tool call patterns — for example: `Call mcp__<server-id>__get_issue with issue_key=<ticket-id>`.

When a skill is found in the skill list:
- Write all five Ticket Adapter fields using this exact template (substitute `<skill-name>`):

  ```
  **Status**: configured
  **Adapter**: Invoke the `<skill-name>` skill via the Skill tool.
  **Lookup**: Invoke the `<skill-name>` skill with the ticket key and a request for summary, description, acceptance criteria, and links.
  **Create**: Invoke the `<skill-name>` skill with the complete ticket payload or approved story file as the argument.
  **Output**: Ticket key and URL returned by the skill.
  ```

  > **Never** research or encode the underlying command, binary, assistant ID, or any CLI flags the skill uses internally. The invocation is always via the Skill tool — no CLI parameters of any kind belong in the adapter spec.

### Confidence and fallback

- If a ticket key prefix is found in commits/branches but no adapter source is identified → status `not configured`, note the detected prefix, add a prompt asking the user if they have an adapter.
- If conflicting adapters are found (e.g. both an MCP server and a skill claim to handle Jira) → present both, ask user to choose before writing.
- If no signals found at all → status `not configured`, no prompting required.

### Output (feeds into project.md Step A)

```
ticket_detection: {
  provider: "Jira | Linear | GitHub Issues | Azure DevOps | none | unknown",
  key_prefix: "<PROJECT-KEY or null>",
  adapter_source: "mcp:<server-id> | skill:<skill-name> | none",
  adapter_instructions: "<exact call pattern or not configured>",
  lookup_op: "<exact lookup call or not configured>",
  create_op: "<exact create call or not configured>",
  output_format: "<ticket key/URL format or not configured>",
  confidence: "high | medium | low | none",
  conflicts: ["<description if any>"]
}
```

High confidence: adapter source identified AND key prefix confirmed.
Medium confidence: provider identified but adapter source unclear.
Low confidence: only a key prefix was found.

---

## Halt conditions

Halt before Phase 2 if any of:
- Tech-stack confidence < 80% for any required field.
- `knowledge-auditor` or fallback audit output is incomplete.
- Any planting recommendation is `halt`.
- Conflicting evidence affects assistant entrypoint authority, managed-region integrity, guide source of truth, or quality gate commands.
- No AI-tool signals AND user declines to choose a target.
- The repo is empty (no manifests, no source files) — nothing to generate guides about.
