---
name: sdlc-doctor
description: Forces a fresh agentic-sdlc environment check and rewrites .agentic/agentic-sdlc/doctor.json. Use it when asked to verify the agentic-sdlc setup, re-run the doctor check, confirm superpowers/node/git, or when a host that uses skills instead of commands needs the legacy sdlc:doctor behavior.
version: 0.1.0
license: Apache-2.0
discoverable: false
authors:
  - agentic-os
---

# sdlc-doctor

Skill entry point for the agentic-sdlc environment check, standing in for the old `sdlc:doctor` command on hosts such as Codex that lack command support.

## Behavior

Unconditionally re-runs the Phase 0 checks and rewrites `.agentic/agentic-sdlc/doctor.json`, ignoring TTL and any existing fingerprint cache.

## Steps

1. Confirm the host project root with `pwd`.
2. Check whether the `superpowers` plugin is present, failing if `superpowers:brainstorming` can't be invoked.
3. Capture `node --version` and `git --version`.
4. Compute `fingerprint = hash(node + superpowers version + plugin version)`.
5. Write `.agentic/agentic-sdlc/doctor.json`:

   ```json
   {
     "schema": 1,
     "checked_at": "<ISO now>",
     "passed": true,
     "checks": {
       "superpowers": { "present": true, "version": "<x.y.z>" },
       "node": { "version": "<vX.Y.Z>", "ok": true },
       "git": { "version": "<X.Y.Z>", "ok": true }
     },
     "fingerprint": "<hash>"
   }
   ```

6. Print a green or red summary table, and when `passed: false`, list exactly which check failed and how to fix it.

## Constraints

- Optional ticket adapters and related CLIs aren't checked here — `requirements-intake` checks them lazily, only when needed.
- Never auto-install `superpowers`; print the install hint and stop instead.
- Do not modify project guide files.
