#!/usr/bin/env python3
"""Every scaffolded hook must *load*, not merely compile.

Executable twin of `/agentic-doctor` Check 2b. `py_compile` cannot catch a
badly-rendered scalar: plain substitution of an answer like
`alembic revision --autogenerate -m "<msg>"` yields

    MIGRATION_DIFF_COMMAND = "alembic revision --autogenerate -m "<msg>""

which Python parses as the chained comparison `"..." < msg > ""`. It compiles,
`py_compile` exits 0, and it raises `NameError` the first time the module loads.
Every in-literal placeholder in the template set sits in a module-level statement
(an assignment, or a docstring), so importing is enough to detect all of them.

Import, do not execute. `main()` may `git fetch`/merge (`session_start_bootstrap`)
or run `ENV_CHECK_COMMANDS` through `subprocess(shell=True)`. Skipping it is safe
only because every hook guards its entry point — so a hook *without* an
`if __name__ == "__main__":` guard is itself the failure, and must not be imported
to find out.

With `--round-trip`, also assert the rendered constants still equal the answers
they were rendered from. Compiling proves the escape did not *break* the file; a
lossy escape (one that strips `"` and `\\`) also compiles and imports, while
silently disarming the two PreToolUse block hooks.

Usage: check-hooks-import.py <TARGET_REPO> [--round-trip]
"""
import importlib.util
import json
import pathlib
import sys
import traceback

from render_rule import MAIN_GUARD, ROUND_TRIP

target = pathlib.Path(sys.argv[1])
round_trip = "--round-trip" in sys.argv[2:]

# Only hooks the installer owns. `.claude/hooks/` in a mature repo also holds the
# team's own hooks: Claude Code runs those as `python3 hook.py`, where a missing
# `__main__` guard is perfectly correct — importing them would be neither safe nor
# our business. Scope comes from the install journal, not from the glob.
#
# `owner` is the filter, not the path prefix. A mature repo whose own hook collides
# with one of ours is journalled at our path with `owner: "user"` (the installer
# skips it rather than overwrite). Keying on the prefix alone would import that file
# and fail the install over a file we never wrote.
journal = json.loads((target / ".agentic/agentic-os/install.json").read_text(encoding="utf-8"))
managed = {f for f, meta in journal["files"].items()
           if f.startswith(".claude/hooks/") and f.endswith(".py")
           and meta.get("owner") == "managed"}

hooks_dir = target / ".claude/hooks"
hooks = sorted(h for h in hooks_dir.glob("*.py")
               if str(h.relative_to(target)) in managed)
if not hooks:
    print("  no agentic-os-managed hooks found under %s" % hooks_dir)
    sys.exit(1)

broken = []
seen = set()
for hook in hooks:
    if not MAIN_GUARD.search(hook.read_text(encoding="utf-8")):
        # A *managed* hook without a guard is our bug: we cannot verify it without
        # executing it, and every template has one.
        broken.append("%s: no __main__ guard — importing it would run its side effects"
                      % hook.name)
        continue
    spec = importlib.util.spec_from_file_location("agentic_hook_" + hook.stem, hook)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except KeyboardInterrupt:
        raise
    except BaseException:
        # BaseException, not Exception: a module that calls sys.exit() at import
        # raises SystemExit, which `except Exception` lets through — the harness
        # would inherit the exit code, skip every later hook, and report success.
        broken.append("%s: %s" % (hook.name, traceback.format_exc().strip().splitlines()[-1]))
        continue

    if round_trip:
        for name, expected in ROUND_TRIP.items():
            if not hasattr(module, name):
                continue
            seen.add(name)
            actual = getattr(module, name)
            if actual != expected:
                broken.append("%s: %s round-tripped lossily\n      expected %r\n      got      %r"
                              % (hook.name, name, expected, actual))

if round_trip:
    # Without this, a hook that stops defining one of these constants silently
    # loses its assertion instead of failing — the check would keep passing while
    # quietly covering less.
    missing = sorted(set(ROUND_TRIP) - seen)
    if missing:
        broken.append("no scaffolded hook defines %s — ROUND_TRIP is stale, or the "
                      "scaffold dropped a constant" % missing)

for b in broken:
    print("  " + b)
sys.exit(1 if broken else 0)
