# Changelog

All notable changes to `agentic-os-mcp`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Releases are tagged `agentic-os-mcp-v<X.Y.Z>`.

## [Unreleased]

### Added
- **Packaging for publication (Phase 3).** `LICENSE` and `NOTICE` now ship
  in the npm tarball (copied from the repo root at build time), and the
  orphaned `.map` files that used to leak in are gone — both pinned by
  `mcp/tests/package.test.ts`, which also asserts the tarball contains
  every `content-index.json` entry and only those.
- `server.json` (MCP Registry server descriptor) and `manifest.json` (`.mcpb`
  bundle manifest), plus `mcp/scripts/build-mcpb.mjs` and `.mcpbignore`,
  producing a production-only `.mcpb` bundle (no devDependencies, no
  `tests/`/`src/`/`scripts/`) that unpacks and serves all 7 tools from the
  unpacked layout. `package.json`, `server.json`, and `manifest.json` are
  asserted to agree on version, name, and identifier by the same test file
  — proven to fail on drift.
- `.github/workflows/release.yml` — a tag-triggered (`agentic-os-mcp-v*`)
  release workflow: reruns the full repo gate (now including the Inspector
  CLI smoke), asserts the tag matches `package.json`'s version, logs in to
  the MCP Registry and asserts the granted permission covers `server.json`'s
  `name` *before* publishing anything (`mcp/scripts/check-registry-permission.mjs`,
  closing a failure mode where a namespace-case mismatch would otherwise 403
  at the Registry only after npm publish already succeeded and burned the
  version), publishes to npm with provenance, polls `registry.npmjs.org` for
  the published version to propagate, and only then publishes `server.json`
  to the MCP Registry (via a freshly re-authenticated
  `mcp-publisher login github-oidc`, since its JWT is short-lived) and
  attaches the built `.mcpb` to a GitHub release. A `workflow_dispatch` input
  resumes just the post-npm steps if one of them fails, without skipping the
  gate or re-running `npm publish`. See `mcp/RELEASE.md` for the maintainer
  runbook this workflow implements, including how the Registry namespace
  case (`io.github.Jarroslav/agentic-os`, matching the real GitHub owner
  login exactly) was confirmed.
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
- **Bundle surface widened**: `content.ts`'s loader dropped its `md|json|txt`
  extension filter so `plan_install`'s template lookups (and the resources
  they point at) stop silently failing for any template that wasn't a plain
  `.md` file. This makes ~70 additional `content-index.json` entries
  servable through `get_document` and the public
  `agentic-os://file/{+path}` resource template — hook scripts (`.py`/`.sh`
  and six extensionless git hooks), `.tmpl` template sources, and one-off
  files such as `scaffold.ps1`, `sdlc.html`, `run-hook.cmd`, and
  `.shellcheckrc`. Verified: 326 total index entries, 256 of which end in
  `.md`/`.json`/`.txt`, so exactly 70 previously-unservable entries are now
  reachable. Index membership remains the entire access-control model — no
  extension-based gate was reintroduced.
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
