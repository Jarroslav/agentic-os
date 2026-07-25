# Install

`agentic-sdlc` is a governed, adapter-driven SDLC pipeline for coding agents,
distributed through the `agentic-os` marketplace. It runs on Claude Code, Codex
CLI, and Cursor. This document covers install, verification, and first-run
configuration for all three.

> Read the whole prerequisites section before you start. The single most
> common install failure is skipping the `superpowers` floor version.

## 1. Prerequisite: `superpowers` >= 6.1.0

`agentic-sdlc` halts at startup if `superpowers` is missing, and its init
routine independently checks the version floor against
`plugins/agentic-os/manifest/dependencies.json` when you run `/agentic-init`.
Install or upgrade `superpowers` before touching `agentic-sdlc`.

Two marketplace sources are documented:

| Marketplace | Role |
|---|---|
| `anthropics/claude-plugins-official` | Official, primary source |
| `obra/superpowers-marketplace` | Fallback / community source |

Claude Code and Codex CLI:

```
/plugin marketplace add anthropics/claude-plugins-official
/plugin install superpowers@claude-plugins-official
```

If the official marketplace doesn't carry the version you need, add
`obra/superpowers-marketplace` the same way and install from there instead.

Cursor: pull `superpowers` from Cursor's own Browse Marketplace tab, or let it
inherit configuration imported from a tool that already has `superpowers`
installed.

Confirm the version before proceeding:

```
/plugin list
```

You should see `superpowers` at `>= 6.1.0`. If it's below that, upgrade it —
`agentic-sdlc` will not install or start against an older copy.

## 2. Install `agentic-sdlc`

The plugin ships from the `agentic-os` marketplace, described by
`.claude-plugin/marketplace.json` at the root of the `agentic-os` git repo.
Claude Code and Codex CLI both read this same descriptor; Cursor cannot
discover it publicly and needs a manual marketplace registration.

### Claude Code

```
/plugin marketplace add https://github.com/<owner>/agentic-os.git
/plugin install agentic-sdlc@agentic-os
```

Use the `.git` clone URL, not the browser URL — the marketplace add step
fails silently on the latter. The plugin reference is scoped: `agentic-sdlc`
qualified with the `agentic-os` marketplace name.

### Codex CLI

```
/plugin marketplace add https://github.com/<owner>/agentic-os.git
/plugin install agentic-sdlc
```

Codex resolves the plugin unscoped (bare `agentic-sdlc`, no `@agentic-os`
suffix), against the path `./plugins/agentic-sdlc` inside the same descriptor.

Codex additionally gates bundled hooks behind a feature flag. Add this block
to `~/.codex/config.toml`:

```toml
[features]
plugin_hooks = true
```

Restart Codex after editing the file. Once restarted, the plugin's hooks are
reviewable and trustable under `/plugin` or `/hooks`. Skip this step and
hook-driven behavior (including the doctor and init skills' automatic
triggers) will silently not run.

### Cursor

Cursor can't see the `agentic-os` marketplace through its Browse tab. Register
it as a custom/user-level marketplace source instead, pointing at the same
git URL (`https://github.com/<owner>/agentic-os.git`), then install from the
User tab.

`agentic-sdlc` expects the governance scaffold that `agentic-os` provides via
`/agentic-init`. If you're setting up on Cursor and only install
`agentic-sdlc`, also install the `agentic-os` plugin itself — don't skip it
because it looks like a marketplace container rather than a real dependency.

> Cursor doesn't set `${CLAUDE_PLUGIN_ROOT}`. The `agentic-init` skill handles
> this itself: when the variable is unset, it resolves its plugin root from
> the skill file's own location instead. No configuration change is needed on
> your end to make this work.

## 3. Local development install (any host)

Working from a clone of the repo rather than a remote URL? Use a filesystem
path as the marketplace source instead of a git URL — the same pattern works
on all three hosts:

```
claude plugin marketplace add .
```

or, from inside the relevant agent's slash-command surface:

```
/plugin marketplace add .
```

Run this from the repo root (where `.claude-plugin/marketplace.json` lives),
then install `agentic-sdlc` exactly as in section 2 for your host.

## 4. Verify the install

Run the `sdlc-doctor` skill. It checks three prerequisites — `superpowers`,
`node`, `git` — and writes a status file as proof of a healthy environment:

```
.agentic/agentic-sdlc/doctor.json
```

A healthy install shows a green check for all three on every run. Re-run
`sdlc-doctor` any time you suspect drift (a `node` upgrade, a `superpowers`
downgrade, a fresh clone) — it overwrites `doctor.json` fresh each time rather
than trusting a cached result.

## 5. First run: initialize the governance scaffold

`agentic-sdlc` depends on run-artifact conventions and gate wiring set up by
`agentic-os`. Initialize it once per repo:

```
/agentic-init
```

Interactive init will prompt you through choices. For a fast, opinionated
setup that accepts built-in defaults everywhere, use:

```
/agentic-init --defaults
```

Both forms independently re-check the `superpowers` version floor against
`plugins/agentic-os/manifest/dependencies.json` before proceeding — this is
the second enforcement point beyond the startup halt in section 1.

## 6. Troubleshooting

**Symptom**: install or startup fails with a message resembling

```
Failed to load marketplace "agentic-os" ... Marketplace file not found
```

**Cause**: a stale marketplace registration under the name `agentic-os` —
typically left over from a prior clone path or URL that no longer resolves.

**Fix**: don't retry the install blindly. List marketplaces first to confirm
the stale entry, remove it, and re-add the correct source:

```
/plugin marketplace list
```

Remove the broken `agentic-os` entry, re-run the appropriate `marketplace
add` command from section 2 or 3 for your setup, then reinstall
`agentic-sdlc`.

## 7. Repo hygiene: `.gitignore`

`agentic-sdlc` writes run state, doctor output, and daily memory logs that
should not be committed. Add:

```
.agentic/agentic-sdlc/
.agentic/runs/
.agents/memory/sdlc/daily/
docs/superpowers/runs/
```

Two directories are the exception — keep these tracked in git, since they
hold the spec/plan artifacts the pipeline produces as durable output, not
scratch state:

```
docs/superpowers/specs/
docs/superpowers/plans/
```

## 8. Optional configuration

`agentic-sdlc` runs entirely on built-in defaults with no config file
present. To customize behavior, create:

```
.agentic/agentic-sdlc/config.json
```

Every key is optional — set only what you want to override.

| Key | Example |
|---|---|
| `schema` | `1` |
| `mode_defaults.autonomous.escalate_on` | `["security", "breaking-change"]` |
| `mode_defaults.autonomous.max_clarifying_questions_per_phase` | `3` |
| `memory.role` | `"sdlc"` |
| `memory.auto_write_on` | `["spec.approved", "plan.approved", "qa.passed"]` |
| `review.strategy` | `"final-two-round"` |
| `review.max_fix_rounds` | `2` |
| `feature_verification.allow_dynamic_playwright` | `true` |
| `feature_verification.app_start_command` | `"npm run dev"` |
| `feature_verification.base_url` | `"http://localhost:3000"` |
| `integrations.ticket.enabled` | `true` |
| `integrations.ticket.adapter` | documented in `.agentic/guides/project.md` |
| `integrations.github.enabled` | `true` |
| `integrations.github.command` | `"gh"` |
| `doctor.ttl_days` | `7` |

> `mode_defaults.autonomous.escalate_on` and `max_clarifying_questions_per_phase`
> shape how far autonomous mode goes before it hands a judgment gate back to
> you. `review.max_fix_rounds` caps how many fix cycles the review flow will
> run before it stops and surfaces the diff as-is.

## 9. Optional integrations

Ticket-system and GitHub integrations are resolved lazily — checked only when
an actual input requires them, not proactively at install or init time.
Nothing in sections 1–8 requires either to be configured.

- **Ticket adapter**: not hardcoded to any backend. The adapter (a skill, an
  MCP server, a command, or a tool) is documented per-project at
  `.agentic/guides/project.md`. If `integrations.ticket.enabled` is `true`
  and a phase needs a ticket lookup, that guide is where the pipeline looks
  for how to reach it.
- **GitHub**: gated by `integrations.github.enabled` and the configured
  `integrations.github.command` (default `"gh"`). Before relying on it,
  confirm the CLI is authenticated:

  ```
  gh auth status
  ```

  This is only checked when a phase actually needs GitHub — not at setup.
