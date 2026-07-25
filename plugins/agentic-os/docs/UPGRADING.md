# Upgrading agentic-os

The plugin and the files it scaffolds into your repo version **independently**:

- **Plugin version** — updated by the Claude Code marketplace (`/plugin` update
  flow). This refreshes the skills, templates, and generators in the plugin
  cache. It does not touch your repo.
- **Scaffold version** — recorded per file in your repo's install journal at
  `.agentic/agentic-os/install.json` (`agentic_os_version` plus each file's
  `sha256`, `template`, and `owner`).

Run `/agentic-upgrade` after a plugin update to reconcile the two. It is a no-op
when the stamps already match.

## What `/agentic-upgrade` does

For every file in the journal it compares the file's current `sha256` against the
recorded one and acts by ownership:

| Case | Action |
|---|---|
| `owner: managed`, unmodified since install | overwrite with the new template |
| `owner: managed`, you edited it | show a template-old → template-new diff and ask before writing |
| `CLAUDE.md` / `AGENTS.md` managed block | the block between the `agentic-os:` markers is replaced wholesale; content outside the markers is never touched |
| `owner: generated` (stack agents from Phase 5) | never auto-overwritten — you are offered a regeneration + re-audit |
| `owner: user` (a file that pre-existed or a declined collision) | never touched |
| `template: "derived"` (thin pointers) | regenerated from the canonical contract only when that contract changed |

After reconciling, it re-runs `/agentic-doctor` and bumps the journal stamp.

The old-template side of a diff is recovered from a marketplace **tag**
(`git show agentic-os-v<OLD>:<path>`), which lets the upgrade show you what the
*template* changed, separate from your local edits. Releases are tagged
per-plugin — `agentic-os-v<X.Y.Z>` — because the plugins in this
marketplace version independently (see `CONTRIBUTING.md` § Releasing; the
policy is active since the first release). For any version you upgrade *from*
that predates its tag, the recovery falls back to a clearly labeled
`CURRENT → new` diff — which mixes your edits with the template's changes, and
the upgrade says so explicitly.

## Version history

The plugin version lives in
[`.claude-plugin/plugin.json`](../.claude-plugin/plugin.json); per-version notes
are in the [CHANGELOG](../CHANGELOG.md). The first public release is
**0.1.0** (no upgrade path from a prior version).
