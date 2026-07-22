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
