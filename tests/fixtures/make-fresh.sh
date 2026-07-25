#!/usr/bin/env bash
# Build a fresh Next.js-marker fixture repo. Arg 1 = target dir (wiped + recreated).
set -euo pipefail
DIR="$1"
rm -rf "$DIR"; mkdir -p "$DIR"
cd "$DIR"
git init -q -b main
git config user.email t@t.t; git config user.name t
cat > package.json <<'JSON'
{ "name": "fresh-fixture", "dependencies": { "next": "15.0.0", "@supabase/supabase-js": "2.0.0" } }
JSON
mkdir -p supabase/migrations
echo "node_modules" > .gitignore
git add -A && git commit -qm "fixture base"
echo "fresh fixture at $DIR"
