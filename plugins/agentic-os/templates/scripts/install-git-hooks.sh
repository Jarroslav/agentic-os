#!/usr/bin/env bash
# Install the repo's tracked git hooks (.githooks/*) into the active hooks dir.
#
# Idempotent and non-destructive: it only copies the files that live in
# .githooks/, so other local hooks (e.g. post-merge) are left untouched. A
# pre-existing hook with the same name that is NOT ours (no "agentic-os:" marker)
# is preserved as <name>.local and chained by the installed hook after the gate
# passes — never overwritten. Run this once per clone — git hooks live under
# .git/ and are not themselves versioned.
#
#   bash scripts/install-git-hooks.sh
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
# Resolve from the repo root and force an absolute path so the install works no
# matter which directory the script is run from.
HOOKS_DIR="$(cd "$ROOT" && git rev-parse --git-path hooks)"
case "$HOOKS_DIR" in /*) ;; *) HOOKS_DIR="$ROOT/$HOOKS_DIR" ;; esac
mkdir -p "$HOOKS_DIR"
count=0
for src in "$ROOT"/.githooks/*; do
  [ -f "$src" ] || continue
  name="$(basename "$src")"
  case "$name" in *.local) continue ;; esac
  dst="$HOOKS_DIR/$name"
  if [ -f "$dst" ] && ! grep -q "agentic-os:" "$dst"; then
    # Foreign hook — preserve it once as the chained .local hook.
    if [ -f "$dst.local" ]; then
      echo "NOTE: $dst.local already exists; leaving both it and $name untouched." >&2
      echo "      Merge them manually, then re-run this installer." >&2
      continue
    fi
    mv "$dst" "$dst.local"
    chmod +x "$dst.local"
    echo "preserved existing hook: $name -> $name.local (chained after the gate)"
  fi
  cp "$src" "$dst"
  chmod +x "$dst"
  echo "installed git hook: $name -> $dst"
  count=$((count + 1))
done
echo "done — $count hook(s) installed."
