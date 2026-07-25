# agentic-upgrade — scaffold updater

Brings a repo's scaffolded agentic-os layer up to the currently installed
plugin version via per-file three-way reconciliation against the install
journal: unmodified managed files are overwritten, user-modified files are
diffed and prompted, managed blocks (CLAUDE.md/AGENTS.md) are replaced
wholesale inside their markers, and generated agents are offered regeneration
plus re-audit. Never a silent overwrite; finishes with a doctor re-run.

## Use It For

- Upgrading the scaffold after updating the agentic-os plugin to a newer
  version.
- Refreshing unmodified managed files at the same version (offered when there
  is no version gap).
- Seeing exactly what the *templates* changed, separate from your local
  edits — with release tags present, the diff shown for a user-modified file
  is template-old → template-new, not current → new.

## How To Ask

- "/agentic-upgrade"
- "Upgrade agentic-os."
- "Update the scaffolded agents and hooks."

## What It Needs

- The install journal (`.agentic/agentic-os/install.json`) with the journaled
  answers — the upgrade re-renders from those and never re-interviews
  (changing answers is an `/agentic-init` re-run).
- The newer plugin installed (a downgrade stops and escalates).
- You available for the prompts: every destructive choice is either provably
  safe (hash-identical to what agentic-os wrote) or user-confirmed.
