# Changelog

Notable changes to the `agentic-os` plugin, as distributed here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this distribution uses
Semantic Versioning. The plugin version lives in
[`.claude-plugin/plugin.json`](.claude-plugin/plugin.json).

## [0.6.0] — Required contract blocks retrofitted onto every shipped agent template

Closes the 2026-07-27 role-grading baseline's cross-cutting D3 finding: the
0.4.0 contract-hardening wave added the rubric's § Required contract blocks to
the generator and exemplars, but none of the pre-0.5.0 shipped templates
carried them. All 10 now do; no behavior was added — every new block restates
rules its contract already stated in prose.

### Added

- **`## Decision rules` DO/DON'T table on all 10 pre-0.5.0 agent templates**
  (`blind-code-reviewer`, `dispatcher`, `instruction-auditor`,
  `pr-pipeline-gate`, `security-reviewer`, `test-automation-author`,
  `test-case-generator`, `test-case-syncer`, `test-failure-triage`,
  `work-item-creator`), 4–6 rows each, grounded in each contract's existing
  rules. The `test-automation-author` and `test-failure-triage` tables digest
  guide rules and are wrapped in `agentic-os:rules` provenance markers naming
  `test-design-pattern.md` and `flaky-protocol.md` respectively.
- **`## Stop and ask when`** on `instruction-auditor` (ungovernable input,
  missing rubric, unmatchable `content_sha256`) and `pr-pipeline-gate` (no
  open MR/PR, wrong target branch, adapter unavailable) — the two templates
  that lacked it.
- **Escalate-never-decide list on all 10 templates**: each contract's
  negative-scope section now states the always-human-owned decisions as a
  list sourced from `.agentic/guides/policy/escalation-policy.md`
  (previously prose-only equivalents); templates without a negative-scope
  section gained `## What this agent does NOT do`.
- **`{{BA_PO_GUIDE_ROWS}}`** derived variable: `PATTERNS.md` index rows for
  `ba-po-operating-model.md` and `mcp-onboarding.md`, emitted only when those
  guides are installed — so multi-role unions that include the ba-po guides
  no longer leave them unindexed (registered in `templates/VARIABLES.md`,
  substituted in `agentic-init` Phase 4, slotted in
  `templates/governance/PATTERNS.md.tmpl`).

### Fixed

- **`test-failure-triage`'s inlined failure-class taxonomy** (the
  TIMING/SELECTOR/…/PROPAGATION table digested from
  `flaky-protocol.md`) now carries the required `agentic-os:rules` marker
  pair; it was the one guide digest shipping without provenance
  (`working-with-agents.md` § Rule provenance markers).

## [0.5.0] — Read-only incident triage for the devops role

First role-capability wave driven by the blind role-grading baseline
(2026-07-27): the devops preset gains an incident-triage capability, and the
baseline's one hard checker failure is fixed.

### Added

- **`agents/incident-triage`** — read-only incident reporter for
  production/runtime incidents: exactly three ranked root-cause hypotheses,
  each with a confidence label, its evidence lines, and the cheapest
  read-only next diagnostic; shortfalls stated ("1 of 3 slots
  evidence-backed") with unsupported slots labeled `speculative — no direct
  evidence`; number+unit runtime bounds with the
  `AGENTIC_INCIDENT_TRIAGE_DISABLED=1` kill-switch; allowlist-only tooling.
  Never mutates cluster or infra state — fixes are human-executed. Carries
  the full required-contract-block set (Decision rules table, Stop and ask
  when, counted PASS criteria, provenance-marked guide digests).
- **`guides/incident-triage`** — the binding triage standards the agent
  digests: read-only principle, three-hypothesis rule (governed by
  evidence-integrity's no-padding rule), runtime bounds ("a bound without a
  unit is not a bound"), allowlist-not-denylist, human-owned escalation.
  Indexed in `PATTERNS.md` via the new conditional `{{OPS_GUIDE_ROWS}}`
  variable — only installs that carry the guide index it.
- **`presets/evals/devops.json`** — eight counted triage scenarios (second
  preset-level eval fixture after ba-po), shape-checked by the new
  deterministic `check-incident-triage.py` in the acceptance matrix (T3d),
  including isolation (a developer-only install must not receive the guide).
- devops preset installs the pair; its description, README row, and setup-page
  entry now say so.

### Fixed

- **`guides/evidence-integrity` registered in `templates/VARIABLES.md`** — it
  was claimed by every preset since 0.4.0 but never registered, so
  `validate-presets.sh` failed on all seven presets (unnoticed because that
  script is not wired into CI; `check-presets.py` only checks the reverse
  direction).

## [0.4.0] — Contract hardening, evidence integrity, rule provenance

Tightens the authoring standards every agent contract is built and graded
against, and gives inlined rule digests a declared source of truth.

### Added

- **`guides/evidence-integrity`** — new blocking standards guide
  (`.agentic/guides/standards/evidence-integrity.md`) against fabricated
  compliance: no self-citation, quotes verified verbatim before presenting,
  classification/approval tags only from durable owner-authored records, no
  padding lists to a required count (shortfalls stated, extras labeled
  `speculative — no direct evidence`), sourced/unverified tags preserved across
  documents, and a counted self-check. Installed by every role preset and
  indexed in `PATTERNS.md`.
- **Required contract blocks** section in the instruction-quality rubric — the
  normative structural list for agent contracts: a `Not for:` routing clause in
  the description, a `## Decision rules` DO/DON'T table, an
  escalate-never-decide list, `## Stop and ask when` triggers, and counted
  (recomputable) verification criteria. The agent-generator skeleton, both
  exemplars, and all ten shipped agent templates now carry these blocks;
  the instruction-auditor grades against the list.
- **Rule provenance markers** — inlined guide-rule digests in generated
  contracts are wrapped in `agentic-os:rules source="…" topic="…"` marker
  pairs (spec: `working-with-agents.md` § Rule provenance markers; index note
  in `PATTERNS.md`). The agent-generator emits them; a deterministic CI check
  validates marker syntax and that standards/policy sources map to shipped
  templates.

### Changed

- The three skill descriptions (`agentic-init`, `agentic-doctor`,
  `agentic-upgrade`) gained explicit `Not for:` routing clauses; new skills
  must include one (CI-enforced; pre-existing sdlc skills are grandfathered
  with a visible warning).
- Upgraders: expect `/agentic-upgrade` diff prompts on the rubric,
  `working-with-agents.md`, `PATTERNS.md`, and any locally modified agent
  templates; the new evidence-integrity guide arrives automatically as a new
  preset template.

## [0.3.0] — BA/PO onboarding and MCP access

Makes `ba-po` a first-class role rather than a preset that installed no guidance
of its own, and gives the business roles a supported path to data that does not
assume a working MCP connection.

### Added

- **Screen 2 — MCP access** in the `/agentic-init` interview: a required
  single-choice screen (`connect now` / `configure later` / `continue without
  MCP`) recorded as `answers.mcp_state` (`configured`, `deferred`,
  `without-mcp`). MCP stays optional — the no-MCP path is supported by pasted
  tables, CSV extracts, screenshots, and manually supplied findings — and an
  unavailable server is recorded as `unavailable` rather than blocking the
  install. Connecting now surfaces the easiest available route and host-specific
  verification commands in the generated MCP onboarding guide. This makes the
  installer seven screens: the HITL dial, autonomy matrix, gates, stack confirm
  and adapter screens shift from 2–6 to 3–7.
- **`guides/mcp-onboarding`** — the shared, host-specific MCP guidance for the
  business roles, generated to `.agentic/guides/standards/mcp-onboarding.md`.
  Installed only when a selected preset declares it, so a developer-only install
  is unaffected.
- **`guides/ba-po-operating-model`** — the role-specific BA/PO entrypoint. It
  delegates to the existing product-owner, requirements-intake and adapter
  contracts rather than defining a second orchestration system beside them.
- **`{{TICKET_ADAPTER_STATUS}}`**, derived from `{{TICKET_ADAPTER}}`, so a
  generated guide can state the adapter's real state instead of asserting one.
- An eval set for the `ba-po` preset (`presets/evals/ba-po.json`).

### Changed

- The `ba-po` preset installs the two new guides, so a `ba-po`-only install now
  scaffolds its own operating model instead of leaving the role undocumented.
- **Role selection is explicit.** The installer never silently selects
  `developer`, `ba-po`, or any other role: Screen 1 asks unless `--presets` was
  passed. `--defaults` accepts detected stack and autonomy defaults only — it
  does not invent a role selection, and is valid only alongside an explicit
  `--presets` or an existing journal.
- Role changes are documented as additive for this lifecycle. Removing a role is
  not automatic, because its files may have been edited by the user; removal
  needs an explicit future migration flow.

### Fixed

- The generated `sdlc/project.md` hard-coded **Status: configured** for the
  ticket adapter. An install that selected no adapter therefore claimed one was
  configured and hid the local-work-item fallback; it now renders the derived
  status and makes that fallback visible.
- The same template hard-coded **Status: configured** for the MR adapter, which
  is equally optional (`gh` / `glab` / MCP / **none**), so a repo with no review
  path was handed a guide asserting one existed. The generated value could never
  be `not configured`, even though that is half of the documented schema — which
  left the consumers' fallbacks unreachable: `qa-e2e-generator` would attempt
  MR-diff steps instead of dropping to commit search, and `mr-creator`'s
  infer-from-remote recovery never triggered. Added `{{MR_ADAPTER_STATUS}}`,
  derived from `{{MR_ADAPTER}}` exactly as the ticket adapter's status is.

## [0.2.0] — mature fleet adoption and native Codex packaging

### Added

- Native Codex plugin metadata, so the governance plugin installs on Codex the
  same way it does elsewhere.
- A deterministic, fail-closed adoption probe
  (`scripts/detect-adoption.py`) for repositories that already treat `.agents/`
  as their canonical agent, skill, hook and state layer. It reports a conflict
  rather than guessing, and a conflict stops the install.
- An `origin` field in the install journal, distinguishing assets adopted from
  a fleet the repo already had from the ones agentic-os wrote or generated —
  `owner` alone could not express that difference.
- `{{SKILLS_CANONICAL_DIR}}` and `{{ORCHESTRATION_STATE_DIR}}`, so templates can
  address an adopted layout instead of assuming `.agentic/`.
- Codex-aware dependency, adapter, hook, rule and doctor requirements.

### Changed

- `/agentic-init` adopts an existing neutral fleet rather than generating a
  competing `.agentic/agents/` tree beside it.
- `/agentic-upgrade` and `/agentic-doctor` resolve the canonical directories
  from the journal, and treat adopted assets as user-owned: verified and
  reported on, never rewritten.

### Fixed

- The git-workflow guide template now instantiates under `.agentic/guides/`,
  matching the directory every other guide template uses.

## [0.1.0] — initial public release

First public version.

### Added

- **Six-screen installer** (`/agentic-init`): role presets, HITL dial, autonomy
  matrix, gates, stack confirm, ticket/MR adapter. `--defaults` accepts every
  detected default. Local hook/session state (`.claude/.review-stamp`,
  `.claude/checkpoints/`, `.agentic/state/`) is gitignored at install.
- **Seven role presets** (developer, QA, BA/PO, architect, devops, PM/delivery,
  portfolio), additive — install several and their template sets union
  (strictest HITL wins).
- **The HITL enforcement pillar**: policy files (autonomy matrix + escalation
  ladder), the output-contract parser, and hard exit-2 PreToolUse gates
  (blind pre-commit review, write-scope guard, guarded write paths, human-gated
  commands, instruction-quality spawn gate). Block gates fail closed on input
  they cannot evaluate.
- **Evidence-grounded stack discovery**: six curated profiles (Next.js/Supabase,
  Django, Spring, Rails, Go, Playwright) recognized instantly; anything else gets
  a full from-scratch inspection, not a degraded stub.
- **Generated, audited agent contracts** and stack guides for the detected stack,
  each graded against the instruction-quality rubric before being armed.
- **Advisory + safety hooks**, installed per preset:
  - *Prompt-scan guard* (UserPromptSubmit) — catches secrets pasted into
    prompts before they are sent, using generic shape classes only (private-key
    blocks, JWTs, credential assignments, basic-auth URLs, Luhn-valid card
    numbers, high-entropy tokens near credential keywords) plus warn-only email
    PII; modes `warn`/`block`/`audit`, masked audit trail, fails open.
  - *Context-monitor* (PostToolUse, advisory-only) — announces context usage
    at 65%/75% thresholds ahead of the PreCompact checkpoint hook.
  - *Lint-on-save* (PostToolUse Write/Edit) — fix-then-recheck on each saved
    source file; remaining errors surface in the same turn. Fails open on
    missing, broken, or unconfigured linters.
  - *Session-learnings notice* (Stop, advisory-only) — detects correction
    signals in the transcript and nudges capturing the lesson into the durable
    memory store.
- **SDLC host config** (`sdlc/config.json.tmpl`): `context_boundaries`
  (plan→implementation fresh-session notice) and `model_tiers`
  (`economy`/`standard`/`premium`, all defaulting to `"inherit"` — concrete
  model IDs are user-supplied values only; the repo's neutrality scan enforces
  that none ships).
- **`/agentic-doctor`** verification pass (imports each managed hook, not just
  `py_compile`) and **`/agentic-upgrade`** three-way reconciliation
  (see [`docs/UPGRADING.md`](docs/UPGRADING.md)).

No upgrade path from a prior version — this is the first release.
