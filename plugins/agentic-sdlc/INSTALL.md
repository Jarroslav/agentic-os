# Installation

## 1. Make superpowers available (required)

`agentic-sdlc` requires `superpowers` >= 5.0.7.

Install `superpowers` before installing `agentic-sdlc`:

```text
/plugin marketplace add obra/superpowers
/plugin install superpowers
```

The plugin halts at startup if `superpowers` is not present.

## 2. Install agentic-sdlc

Use the commands for the agent you are installing into.

### Claude Code

From any Claude Code session:

```text
/plugin marketplace add obra/superpowers
/plugin install superpowers
/plugin marketplace add https://github.com/Jarroslav/agentic-os.git
/plugin marketplace list
/plugin install agentic-sdlc@agentic-os
/plugin list
```

Use the Git clone URL ending in `.git`, not the browser URL. Claude clones the repository and reads `.claude-plugin/marketplace.json` from the repo root.

This marketplace is registered under the name `agentic-os` (see `.claude-plugin/marketplace.json`).

For local development from a clone of this repository, you can add the local marketplace path instead:

```bash
claude plugin marketplace add .
```

Then open Claude Code and run:

```text
/plugin install agentic-sdlc@agentic-os
```

### Codex CLI

From any Codex CLI session:

```text
/plugin marketplace add obra/superpowers
/plugin install superpowers
/plugin marketplace add https://github.com/Jarroslav/agentic-os.git
/plugin marketplace list
/plugin install agentic-sdlc
/plugin list
```

Use the Git clone URL ending in `.git`, not the browser URL.

Codex resolves this plugin from the same `.claude-plugin/marketplace.json`, at `./plugins/agentic-sdlc`.

For local development from a clone of this repository, use `/plugin marketplace add .` instead of the Git URL.

Codex plugin-bundled hooks are opt-in. To make the agentic-sdlc hooks visible
under `/plugin` and `/hooks`, enable plugin hooks in `~/.codex/config.toml`:

```toml
[features]
plugin_hooks = true
```

Restart Codex after changing the feature flag, then open `/plugin` or `/hooks`
to review and trust the newly visible hooks.

## 3. Verify

```text
Use the sdlc-doctor skill
```

Expected output: green check for `superpowers`, `node`, `git` and a freshly written `.agentic/agentic-sdlc/doctor.json`.

If Claude Code reports a different marketplace name while installing, remove that stale marketplace entry and retry:

```text
/plugin marketplace list
/plugin install agentic-sdlc@agentic-os
```

The stale-entry symptom looks like: `Failed to load marketplace "agentic-os" ... Marketplace file not found`.

## 4. (Recommended) Update `.gitignore`

Add the plugin's local-state paths so they don't leak into commits:

```gitignore
# agentic-sdlc local state
.agentic/agentic-sdlc/
.agentic/runs/
.agents/memory/sdlc/daily/
docs/superpowers/runs/
```

`docs/superpowers/specs/` and `docs/superpowers/plans/` should remain checked-in (they're the artifacts of your runs).

## 5. (Optional) Configure

Create `.agentic/agentic-sdlc/config.json`:

```json
{
  "schema": 1,
  "mode_defaults": {
    "autonomous": {
      "escalate_on": ["security", "breaking-change"],
      "max_clarifying_questions_per_phase": 3
    }
  },
  "memory": {
    "role": "sdlc",
    "auto_write_on": ["spec.approved", "plan.approved", "qa.passed"]
  },
  "review": {
    "strategy": "final-two-round",
    "max_fix_rounds": 2
  },
  "feature_verification": {
    "allow_dynamic_playwright": true,
    "app_start_command": "npm run dev",
    "base_url": "http://localhost:3000"
  },
  "integrations": {
    "ticket": {"enabled": true, "adapter": "documented in .agentic/guides/project.md"},
    "github": {"enabled": true, "command": "gh"}
  },
  "doctor": {
    "ttl_days": 7
  }
}
```

All keys are optional; absent file -> built-in defaults.

## 6. (Optional integrations)

- **Ticket systems**: document the ticket adapter in `.agentic/guides/project.md` or a related integration guide. The adapter may be a skill, MCP server, command, or tool.
- **GitHub**: ensure `gh` CLI is authenticated (`gh auth status`).

These are checked lazily — only when an input requires them.
