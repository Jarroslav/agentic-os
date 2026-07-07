# SDLC Doctor

Verifies the agentic-sdlc environment — superpowers plugin presence, Node.js version, and Git version — and rewrites the cached doctor report at `.agentic/agentic-sdlc/doctor.json`.

## Use It For

- Diagnosing why an SDLC run failed to start.
- Verifying all prerequisites are installed after a new machine setup.
- Re-running environment checks after upgrading the superpowers plugin or Node.js.

## How To Ask

Examples:

- "Run SDLC doctor."
- "Check SDLC setup."
- "Verify the agentic-sdlc environment."
- "Re-run doctor checks."

## What It Needs

- superpowers plugin >= 5.0.7 installed and resolvable.
- Node.js installed (any recent LTS version).
- Git installed.
