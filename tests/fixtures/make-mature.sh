#!/usr/bin/env bash
# Build a mature polyglot fixture: existing CLAUDE.md, own settings hook, a
# colliding agent file, Django+Node markers, a pre-existing pre-commit hook.
# Arg 1 = target dir (wiped + recreated).
set -euo pipefail
DIR="$1"
rm -rf "$DIR"; mkdir -p "$DIR"
cd "$DIR"
git init -q -b main
git config user.email t@t.t; git config user.name t

cat > CLAUDE.md <<'MD'
# House Rules

This is the team's own hand-written guidance. It must survive the install verbatim.
MD

# polyglot markers
cat > package.json <<'JSON'
{ "name": "mature-fixture", "dependencies": { "react": "18.0.0" } }
JSON
cat > manage.py <<'PY'
# Django entrypoint marker
PY
mkdir -p .claude/hooks .claude/agents
cat > .claude/settings.json <<'JSON'
{
  "hooks": {
    "PostToolUse": [
      { "matcher": "Write", "hooks": [ { "type": "command", "command": "python3 .claude/hooks/team_notify.py" } ] }
    ]
  }
}
JSON
# a colliding agent file with sentinel content
echo "SENTINEL: team's own security-reviewer — must not be overwritten" \
  > .agentic-preexist-marker.txt
mkdir -p .agentic/agents
echo "SENTINEL team security-reviewer" > .agentic/agents/security-reviewer.md

# pre-existing foreign pre-commit hook
mkdir -p .git/hooks
cat > .git/hooks/pre-commit <<'SH'
#!/usr/bin/env bash
echo "TEAM-PRECOMMIT-RAN"
exit 0
SH
chmod +x .git/hooks/pre-commit

echo "node_modules" > .gitignore
git add -A && git commit -qm "mature fixture base"
echo "mature fixture at $DIR"
