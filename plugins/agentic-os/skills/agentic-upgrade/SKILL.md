---
name: agentic-upgrade
description: Upgrade a repo's scaffolded agentic-os layer to the currently installed plugin version — per-file three-way reconciliation via the install journal's recorded sha256 (unchanged managed files overwritten, user-modified files diffed and prompted, managed blocks replaced wholesale, generated agents offered regeneration plus re-audit — never a silent overwrite), then doctor re-run and journal stamp bump. Use when the user says "/agentic-upgrade", "upgrade agentic-os", "update the scaffolded agents/hooks", or after updating the agentic-os plugin.
version: 0.1.0
license: Apache-2.0
---

# agentic-upgrade — scaffold updater

You reconcile the target repo's scaffold with the newer plugin templates.
The **install journal is the third point of the three-way merge**: it records
what agentic-os last wrote (`sha256`), from which template (`template`), and
who owns the file now (`owner`). **Never overwrite silently** — every
destructive choice is either provably safe (hash-identical to what we wrote)
or user-confirmed.

Conventions (`PLUGIN`, `TARGET`, journal shape, rendering rules incl. the
`.json.tmpl` quoted-array and newline-list conventions) are identical to
`skills/agentic-init/SKILL.md` — read its "Conventions" section first.
Like init: never `git add`/`git commit` in the target repo.

## Phase 1 — Version gate

1. Read `TARGET/.agentic/agentic-os/install.json`. Missing ⇒ stop: "no install
   journal — run /agentic-init".
2. `NEW` = `"version"` from `PLUGIN/.claude-plugin/plugin.json`; `OLD` =
   `journal.agentic_os_version`.
3. `NEW == OLD` ⇒ nothing to upgrade; offer a refresh (Phase 2 with
   unchanged-only rules) or just `/agentic-doctor`, then stop.
   `NEW < OLD` ⇒ stop and escalate (plugin downgraded — human decision).
4. Re-load `journal.answers` — every re-render uses the **journaled answers**;
   the upgrade never re-interviews (changing answers is an `/agentic-init`
   re-run).

## Phase 2 — Per-file three-way reconciliation

For every journal entry with a template ID (the destination map lives in
`skills/agentic-init/SKILL.md` Phase 4), compute:
`RECORDED` = journaled sha256, `CURRENT` = sha256 of the file on disk,
`NEWRENDER` = the `NEW` template rendered with `journal.answers` (including
init's installer-side conditionals: the warn-only git-sync patch when
`answers.git_sync_mode` is `warn-only`, migration-notice skip on empty
migrations dir, registry row pruning). Entries with `template: "derived"`
have **no template to render** — handle them in the derived branch below,
never via a template diff.

Then per `owner` / `template`:

**`template: "derived"` (synthesized pointer files —
`.claude/agents/<name>.md` and `.claude/commands/<name>.md` for templated
agents; init Phase 4 step 7)**
- Handle these **after** their canonical contract
  (`.agentic/agents/<name>.md`) has been reconciled.
- Canonical unchanged in this upgrade ⇒ skip the pointer.
- Canonical rewritten/regenerated ⇒ re-synthesize the pointer from the new
  canonical using the same synthesis rule as init (the pointer formats in
  `PLUGIN/generators/agent-generator.md` §2/§3): `CURRENT == RECORDED` →
  overwrite and update the journal sha; `CURRENT != RECORDED`
  (user-modified pointer) → show current → re-synthesized diff and ask
  keep (→ `owner: "user"`) / re-synthesize.

**`owner: "managed"` (regular files)**
- File deleted on disk ⇒ ask: restore from `NEWRENDER` or journal as removed.
- `CURRENT == RECORDED` (untouched since we wrote it) ⇒ **overwrite** with
  `NEWRENDER`, update the journal sha. Report one line per file.
- `CURRENT != RECORDED` (user-modified) ⇒ **show the template-old→new diff
  and ask**. Old render recovery: the plugin installs from a git marketplace,
  so try `git -C PLUGIN_REPO show v<OLD>:<template path>` (where
  `PLUGIN_REPO` = the marketplace clone containing `PLUGIN`; tags may be
  `v<OLD>` or `<OLD>`), render it with `journal.answers`, and diff old-render
  → new-render — that shows the user exactly what the *template* changed,
  separate from their local edits. If the old version is unrecoverable, fall
  back to diffing `CURRENT` → `NEWRENDER` and say so explicitly (that diff
  mixes their edits with template changes). AskUserQuestion per file:
  **keep mine (default)** → journal flips to `owner: "user"`;
  **take new** → overwrite, stays `managed`;
  **merge by hand** → write `NEWRENDER` to `<path>.ao-new` beside it, journal
  a follow-up, leave the live file alone.

**Managed blocks (`CLAUDE.md`, and `AGENTS.md` when it was installed as an
appended block on a mature repo)**
- Replace the content between `<!-- agentic-os:begin v… -->` and
  `<!-- agentic-os:end -->` **wholesale** with the newly rendered block (the
  begin marker carries the new version stamp — it is rendered from
  `{{AGENTIC_OS_VERSION}}` in
  `PLUGIN/templates/governance/CLAUDE.section.md.tmpl`). Content outside the
  markers is never touched, even if the user edited inside the markers (the
  markers say "do not edit inside" — still, mention in the report when the
  replaced block had drifted).
- Markers missing entirely (user deleted the block) ⇒ ask before re-appending.

**`owner: "user"`**
- Never touched. If the corresponding template changed between `OLD` and
  `NEW`, add one report line ("template <ID> changed upstream; your file
  <path> is user-owned — diff available on request").

**`owner: "generated"`**
- **Never auto-overwritten.** If the generator inputs changed in `NEW`
  (`PLUGIN/generators/agent-generator.md`, `guide-generator.md`, the matching
  stack profile, or the exemplars) — or unconditionally, as a cheap default —
  **offer regeneration**: re-run init Phase 5 for that slot (same subagent
  prompt assembly, same ≤2-retry audit loop against
  `.agentic/guides/standards/instruction-quality-rubric.md`, same decision-6
  relaxed fallback) and update `docs/audits/instruction-scorecard.json`
  (`content_sha256` + `composite_score`, per-agent `gate_threshold` only when
  relaxed). Declined ⇒ leave the contract, but if its scorecard entry is now
  stale the instruction gate will block its spawn — warn about that
  explicitly.

**New/removed template IDs**
- Template IDs newly present in `NEW`'s preset union (re-resolve the union
  from `journal.answers` presets against `PLUGIN/presets/roles/*.json`) but
  absent from the journal ⇒ scaffold them exactly as init Phase 4 does
  (collision prompts included).
- Journaled IDs no longer shipped ⇒ never auto-delete; list them as
  "orphaned — safe to remove manually".

## Phase 3 — Settings + git hooks refresh

1. Re-run init's settings deep-merge with the `NEW`
   `PLUGIN/templates/hooks/settings-fragment.json.tmpl` (append-if-absent,
   set-union, pruning rule for unscaffolded hook scripts, **diff shown and
   confirmed before write**).
2. If `.githooks/pre-commit` or `scripts/install-git-hooks.sh` was updated in
   Phase 2, re-run `bash scripts/install-git-hooks.sh` (idempotent; chains a
   foreign hook as `pre-commit.local`, never replaces it).

## Phase 4 — Verify and stamp

1. Re-run the `agentic-doctor` skill; it rewrites
   `.agentic/agentic-os/doctor.json`. Fix-or-report any `failures`.
2. Bump the journal: `agentic_os_version` = `NEW`, refresh every touched
   file's `sha256`, append `follow_ups` for merge-by-hand files
   (`<path>.ao-new`), declined regenerations, and orphaned templates.
3. Report: files overwritten / prompted / kept / regenerated / newly
   scaffolded / orphaned, the managed-block version bump, the doctor verdict,
   and the reminder that committing the upgrade diff is the human's call.
