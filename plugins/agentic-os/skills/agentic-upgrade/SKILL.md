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

**Agent registry (`.agentic/guides/agent-registry.md`, `owner: "managed"`,
`template: "governance/agent-registry"`)** — handled specially, **never**
through the plain `owner: "managed"` branch above, even when
`CURRENT == RECORDED`, and **after** every `owner: "generated"` regeneration
decision in this same upgrade pass has been finalized (same "process this
after its dependency" pattern as the `template: "derived"` pointer-file
branch above) — a slot regenerated in this pass needs its row's text
refreshed before this section reconciles the file, not after: this file is a
hybrid — the table row whose first cell is the literal
`<!-- generated-agent-rows -->` marker and everything above it is ordinary
template output (the curated preset rows); every table row strictly
**after** that marker row is orchestrator-appended state from init Phase 5
step 6 (one row per generated writer/gate agent) — state the
template render has no knowledge of and would silently discard.
- Split `CURRENT` **at the line immediately after** the marker row (the
  marker row itself stays with the static half, so it is never duplicated
  or dropped on reassembly): `static_current` = everything through and
  including the marker row; `generated_rows` = every table row after it,
  verbatim, byte-for-byte (empty when nothing has been generated yet).
- Compute `NEWRENDER` from the `NEW` template as usual, then split it the
  same way — `static_newrender` (through and including its own marker row;
  a bare template render has nothing after that row, since nothing has been
  generated yet in an upgrade-only pass).
- Reconcile **only** `static_current` vs. `static_newrender` using the same
  spirit as the `owner: "managed"` diff-and-ask rule above (untouched preset
  rows ⇒ overwrite that portion; user-edited preset rows ⇒ show diff, ask) —
  the marker row itself is part of this diff like any other row, so a
  genuine upstream template change to it (should one ever happen) still
  surfaces normally instead of being silently frozen. **One deviation from
  that rule, and it matters**: the "keep mine" outcome must **never** flip
  this file's journal `owner` to `"user"` the way it does for an ordinary
  managed file. This file's `owner` stays `"managed"` /
  `template: "governance/agent-registry"` **permanently**, regardless of any
  static-portion diff answer — because `owner: "user"` means "never touched
  again" (see the generic `owner: "user"` rule above), and that would
  silently and permanently stop this file from ever reconciling
  `generated_rows` on every future upgrade too, disabling the very feature
  this whole section exists to provide, with no warning. A declined
  static-portion update just leaves that portion as-is for this pass — the
  same diff is offered again on the next upgrade; that's an acceptable
  minor repetition, not a workaround for a real problem.
- Reassemble: reconciled static portion (**already ends with the marker
  row** — do not insert it again) **immediately followed by** `generated_rows`
  unchanged, and write that back. Never run the reconciled generated-agent
  rows through `AskUserQuestion` — they are not the user's content to diff
  against a template, they are this feature's own state, already governed by
  init Phase 5 step 6's insert-or-replace-by-path rule.
- **Re-stamp both the journal and the scorecard** for this file, same as
  init Phase 5 step 7 — this write changed the file's bytes just as surely
  as an install-time append does, and the failure mode is identical if you
  skip either: journal `sha256` stale ⇒ every future `/agentic-upgrade` sees
  a false "user-modified" and asks needlessly; scorecard `content_sha256`
  stale ⇒ `.claude/hooks/instruction_gate.py` hard-blocks the spawn of
  `dispatcher` (and any other agent citing this guide) with "stale" until a
  human runs `/instruction-auditor` — on the very next spawn after this
  upgrade, not eventually. Scorecard entry stays `composite_score: 100`,
  `source: "template-inherited"` (same rationale as init: the reconciled
  static portion is template output, the preserved/replaced rows follow a
  strict mechanical format, neither needs a fresh audit pass).
- **Same-pass regeneration**: before starting the split above (per the
  ordering rule at the top of this section), for every slot whose canonical
  contract was regenerated in this pass (the `owner: "generated"` branch
  above), re-apply Phase 5 step 6's replace-by-path logic to that slot's row
  in `CURRENT` — so `static_current`/`generated_rows` are computed from a
  file whose rows already reflect the regenerated contract's actual
  triggers, not stale text from before this upgrade.
- **Marker missing from `CURRENT` entirely** (a repo installed under a
  plugin version that predates this marker — every install before this fix
  shipped) ⇒ **do not guess where the split is.** Same rule as the CLAUDE.md
  managed-block's "markers missing entirely" case above: ask before doing
  anything. Show the user `CURRENT` in full and ask whether it contains any
  hand-appended stack-specific rows worth preserving; if yes, have them
  point out which lines, treat those as `generated_rows` for this pass and
  everything else as `static_current`, then proceed with the normal
  reconcile/reassemble steps above (this also retroactively adds the marker,
  so every later upgrade of this file takes the fast, unattended path). If
  no rows exist yet, treat the whole file as `static_current` with an empty
  `generated_rows` and proceed normally — this is the common case for a repo
  that installed before any capability ever applied.

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
