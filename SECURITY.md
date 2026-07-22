# Security policy

## Reporting a vulnerability

Please **do not** open a public GitHub issue for a suspected security
vulnerability. Instead, use
[GitHub's private vulnerability reporting](https://github.com/Jarroslav/agentic-os/security/advisories/new)
for this repository, or email the maintainer directly at the address on the
[owner's GitHub profile](https://github.com/Jarroslav).

Include:

- What you found and why it's a security issue (not just a bug).
- Steps to reproduce, ideally against a throwaway repo (see the README's
  "Try it in two minutes" fixture) rather than a real project.
- The plugin version (`plugins/agentic-os/.claude-plugin/plugin.json` /
  `plugins/agentic-sdlc/.claude-plugin/plugin.json`) you tested against.

You should get an initial response within a few days. This project is
solo-maintained; there is no formal SLA, but security reports are
prioritized above other work.

## What counts as a security issue here

`agentic-os` scaffolds enforcement hooks (git hooks, Claude Code hooks) and
governance policy into a target repository, and its `agentic-sdlc` plugin can
run subagents autonomously under the `gated-autonomous`/`autonomous` HITL
modes. Reports of particular interest:

- A way to make an enforcement hook (write-scope guard, blind pre-commit
  review gate, instruction-quality spawn gate) silently pass when it
  shouldn't — i.e., a bypass of a gate documented as hard/fail-closed in
  [`docs/PRINCIPLES.md`](docs/PRINCIPLES.md).
- A way for scaffolded content (a generated agent contract, a rendered
  template) to cause command injection, path traversal outside the declared
  `write_scope`, or exfiltration of secrets from the target repo.
- A way for the decision-router's autonomous mode to escalate to
  human-equivalent trust (e.g., resolve a `security`/`breaking-change`
  risk-flagged gate) without actually meeting the documented escalation
  condition.
- Any script under `.claude/hooks/`, `.githooks/`, or `scripts/` that
  executes untrusted input unsafely.
- A way to make the MCP server (`mcp/`) serve a path that is not a literal
  key of its build-time `content-index.json` — that membership check is its
  entire access-control model (no path arithmetic, so this is meant to make
  traversal and absolute paths inexpressible), and a bypass of it is a
  security bug.

Prompt-injection resistance of the underlying LLM is out of scope for this
project specifically — report those upstream to the model provider — but a
case where this project's *own* enforcement layer fails to catch a
consequence of prompt injection (e.g., a hook that should have blocked a
scope violation but didn't) is in scope.

## Supported versions

Only the latest published version of each plugin (`agentic-os`,
`agentic-sdlc`, `agentic-qe`) and of the `agentic-os-mcp` server (tagged
`agentic-os-mcp-v<X.Y.Z>`) receives security fixes. There is no
long-term-support branch at this stage of the project.
