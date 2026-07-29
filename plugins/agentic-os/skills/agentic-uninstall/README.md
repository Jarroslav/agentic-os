# agentic-uninstall — role remover

Removes one or more role presets from a repo's scaffolded agentic-os layer, or
the whole layer with `--all`. It does not delete the files a preset lists —
presets are additive unions, so most of what `qa` carries is also carried by
`developer`. Instead it recomputes what `/agentic-init` would produce for the
roles that remain and converges the repo to that state, so the result equals a
fresh install of the roles you kept:

    install(developer,qa) → uninstall(qa)  ==  install(developer)

That invariant is asserted directly by the acceptance harness (`T9` in
`tests/run-matrix.sh`), not just claimed here.

## Use It For

- Dropping a role you tried and don't want — `qa`, `devops`, `design` — while
  every other role keeps working exactly as before.
- Backing the whole layer out (`--all`), leaving the repo re-installable with
  any role as if it had never been scaffolded.
- Seeing what a removal *would* do before committing to it (`--dry-run`),
  including the settings diff and the git-hook actions.

## How To Ask

- "/agentic-uninstall qa"
- "Remove the devops role."
- "We don't need the design preset any more."
- "Show me what removing qa would delete." *(→ `--dry-run`)*
- "Uninstall agentic-os from this repo." *(→ `--all`)*

## What It Needs

- **An install journal** — `.agentic/agentic-os/install.json`. It is the
  authoritative record of what agentic-os wrote, which template each file came
  from, and who owns it now. No journal, nothing to remove.
- **A clean-ish working tree.** Nothing is committed for you, so `git diff` is
  your undo. A dirty tree makes that diff harder to read.
- **You available for the prompts.** Every destructive choice is either
  provably safe (the file is byte-identical to what agentic-os wrote) or
  user-confirmed. Files you edited are never deleted without asking, and
  files marked `owner: user` are never offered at all.
- **A decision on governance if it would loosen.** Removing the only `strict`
  preset lowers the repo's HITL default; the skill asks rather than assuming.

## What It Will Not Do

- Delete anything `owner: "user"` or adopted from a pre-existing agent fleet.
- Remove a template a remaining role still claims.
- Leave the commit gate wired to a script it just deleted (settings are
  un-wired *before* scripts are removed, deliberately).
- Discard your repo's own pre-commit hook — one displaced to `pre-commit.local`
  at install time is moved back.
- `git add` or `git commit` anything.
