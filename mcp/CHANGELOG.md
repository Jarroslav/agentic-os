# Changelog

All notable changes to `agentic-os-mcp`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Releases are tagged `agentic-os-mcp-v<X.Y.Z>`.

## [Unreleased]

### Added
- `list_presets` — the seven agentic-os role presets with HITL default,
  orchestration mode, and SDLC skills.
- `list_qe_blueprints` — the 28 Quality Engineering blueprints, filterable by
  STLC stage.
- `list_sdlc_phases` — the SDLC pipeline phase map with its judgment gates.
- Resource URI aliases `agentic-os://presets/{role}` and
  `agentic-os://qe/blueprints/{stage}/{id}`.
- `plan_install` — composes one or more role presets into an ordered file
  manifest (template id, source `agentic-os://` uri, owner), applying
  strictest-HITL-wins and unioning every orchestration style across the
  selected roles. Returns a plan only; the caller performs the writes.
- `run_doctor` — audits an agentic-os install in a target repo the caller
  names. Adds the server's second filesystem reader, `mcp/src/target.ts`,
  gated by root containment (canonicalized, symlinks resolved) rather than
  the bundle reader's build-time index — see SECURITY.md for the full
  access-control writeup and its one accepted risk (a TOCTOU window between
  containment validation and read, scoped to an attacker who already has
  write access to the repo being audited). Six of the doctor's checks run
  natively as pure file inspection; the three that require executing Python
  (hook compile+import, canned-event dry-runs, HITL smoke) come back as
  exact commands in `host_must_run` for the host to run itself — the server
  never executes code from a target repository. `verdict: "incomplete"` is
  the expected result of a server-side-only run, not a failure signal.
- Tool surface now stands at 7 of the documented 8-tool cap.
- `mcp/tests/readonly.test.ts` extended to prove no source file writes to
  the filesystem or spawns a process (banning both write APIs and the
  `child_process` module specifier in any quoting) across `mcp/src/**`, and
  that exercising every tool — including `run_doctor` against a live target
  — leaves `plugins/` byte-identical.

## [0.1.0]

### Added
- Read-only stdio MCP server on `@modelcontextprotocol/sdk` v1.x, spec
  `2025-11-25`.
- `search_methodology` and `get_document`.
- 31 skill resources, an `agentic-os://file/{+path}` template, and six
  workflow prompts.
- Content pipeline with a committed sha256 drift index enumerated from
  `git ls-files`, gated in CI before the build.

Not published to npm.
