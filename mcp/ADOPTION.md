# Adoption runbook

How to get `agentic-os-mcp` discovered, once it is published. This is a
maintainer runbook — every step here is an action **you** take from your own
accounts. Nothing in it can or should be automated by CI, because each channel
verifies that the submitter owns the repo.

**Do none of this until the package is actually published.** The prerequisite
is [RELEASE.md](RELEASE.md): npm shows the version (`npm view agentic-os-mcp`)
and the MCP Registry lists `io.github.Jarroslav/agentic-os`. Every directory
below either ingests from the Registry or links to a live package; submitting
earlier produces dead listings.

## Do this first: remove the "not yet published" caveat

The moment the first release is live, delete the unpublished-package block at
the top of [README.md](README.md)'s Install section (the `> **Not yet
published.**` blockquote and its local-dev alternative). Leaving it up after
publishing is the one thing that will actively cost installs — a reader who
sees "not published" stops there.

Commit that as its own small change, e.g. `docs(mcp): package is published —
drop the pre-release caveat`, and add an npm version badge to the README top
now that it will resolve:

```
[![npm](https://img.shields.io/npm/v/agentic-os-mcp)](https://www.npmjs.com/package/agentic-os-mcp)
```

## Discovery order

The official Registry is the root of the graph — the directories feed from it —
so the release itself does most of the work. Do the channels in this order,
because each later one is easier once the earlier ones exist:

1. **Official MCP Registry** — already handled by the release workflow
   (`mcp-publisher publish` runs on the tag). Confirm the listing resolves
   before doing anything else here.
2. **Glama** — auto-syncs from GitHub after a one-time ownership submission.
3. **mcp.so** and **Smithery** — manual submissions.
4. **`awesome-mcp-servers`** — a pull request under your account.
5. **PulseMCP** — the highest-signal launch channel; pitch it last, once the
   listings above give it something to point at.

---

## 1. Glama

Glama does **not** blanket-index every server; a maintainer with write/admin
access submits the repo and authenticates through GitHub OAuth, after which
Glama clones and continuously syncs the Git history (updates land within
minutes of a push).

- Go to <https://glama.ai/mcp/servers> and use the add/submit flow; sign in
  with the GitHub account that owns `Jarroslav/agentic-os`.
- Point it at `https://github.com/Jarroslav/agentic-os`.

**One caveat worth knowing:** Glama's build step wants a `Dockerfile`, either
in the repo or inferred by its tooling. This server has none — it is an
`npx`/stdio package, not a container. Glama can usually infer a Node build, but
if the listing's build fails, the fix is a minimal `Dockerfile` in `mcp/`
(`FROM node:20-slim`, copy the package, `npm ci --omit=dev`, `ENTRYPOINT
["node","dist/index.js"]`). Treat that as a follow-up only if Glama's inferred
build actually fails — do not add it speculatively.

## 2. mcp.so

- Submit via the **Submit** button on <https://mcp.so>, or open an issue on
  their GitHub submissions repo.
- Give the npm package name `agentic-os-mcp` and the repo URL.

## 3. Smithery

- <https://smithery.ai> — submit the server; Smithery offers a CLI installer
  and a hosted-remote option. This server is stdio-only, so it lists as a
  local/CLI-installed server, which is correct.

## 4. `awesome-mcp-servers` pull request

Repo: <https://github.com/punkpeye/awesome-mcp-servers>. House rules: entries
sit under a category, **alphabetically by the linked repo**, one per line,
name linked to the repo, concise description, matching the file's existing
style. The legend uses emoji for language / scope / OS.

**Category:** `Developer Tools` (its section heading is `💻`; the file's own
table of contents inconsistently shows `🛠️`, so search for the words, not the
glyph — the anchor is `#developer-tools`).

**Markers for this server**, from the legend:
- `📇` TypeScript codebase
- `🏠` Local service (stdio, runs on your machine)
- `🍎 🪟 🐧` cross-platform (pure Node, no native dependencies)
- no `🎖️` — this is not an official Anthropic implementation

**Ready-to-paste entry** (place it alphabetically among the `J` repos in the
Developer Tools section):

```
- [Jarroslav/agentic-os](https://github.com/Jarroslav/agentic-os) 📇 🏠 🍎 🪟 🐧 - Read-only server exposing the agentic-os governance, SDLC, and QE methodology to any MCP host; never writes to your repo and never executes code. Ships install planning and install verification.
```

Keep the description to one line and factual — over-claiming is the fastest way
to get a PR bounced. The "never writes / never executes" phrasing is the
server's genuine differentiator and is worth keeping.

## 5. PulseMCP

<https://www.pulsemcp.com> is hand-reviewed and run by people close to the MCP
Steering Committee; its weekly newsletter is the single highest-signal launch
channel. Submit through their site once the Registry listing and at least one
directory are live, so the entry has corroborating links. A short, honest pitch
— read-only, never-executes, a real test suite behind it — fits their editorial
bar better than a feature dump.

---

## The one differentiator to lead with everywhere

Every other MCP server that touches a repo can write to it. This one is
architecturally read-only and never executes code from a target repo — the
`run_doctor` tool hands verification commands back to the host rather than
running them, and a static test bans the write and process APIs in `src/`. That
is the line worth putting first in every submission, because no competing
listing can truthfully say it.

## After the first wave

Track, in rough order of signal: npm weekly downloads, the Registry and
directory listing states, the PulseMCP newsletter pickup, GitHub stars/issues,
and — uniquely for this project — the public CI pass rate as a trust signal.
None of that is a code task; it is why the testing story — the `mcp/tests`
suite and the `mcp` CI job in [ci.yml](../.github/workflows/ci.yml) — is worth
writing up publicly when there is something live to point at. No such write-up
exists yet; that is the natural first piece of content once the package is out.
