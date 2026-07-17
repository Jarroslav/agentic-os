# Cursor install smoke tests

Validates that the Cursor plugin packaging loads the same skills the installer
expects, and that a fresh target repo scaffolds correctly after install.

## Automated

```bash
bash tests/cursor/run-cursor-e2e.sh
```

By default this creates/recreates:

```text
../test/agentic-os-cursor-fresh-install
```

(relative to the agentic-os repo root — i.e. `~/git/test/agentic-os-cursor-fresh-install`).

Override the target:

```bash
TARGET=/path/to/repo bash tests/cursor/run-cursor-e2e.sh
```

## What is covered

| Step | Asserts |
|---|---|
| `check-cursor-packaging.py` | `.cursor-plugin/marketplace.json` resolves; each plugin manifest points at real `skills/` (and `agents/` for sdlc) |
| `make-fresh.sh` | Empty Next.js-marker git repo |
| `refinstall.py` | Deterministic `/agentic-init --defaults` Phase 4 scaffold |
| Post-checks | hooks compile/import, settings JSON, scorecard, registry, pre-commit gate |

## What is not automated

- Cursor UI marketplace registration (Settings → Plugins)
- Model-driven `/agentic-init` interview screens and Phase 5 generation

After the automated run passes, open the target repo in Cursor with both plugins
installed and run `/agentic-init --defaults` to complete the manual half.
