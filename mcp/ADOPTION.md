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

## 1. Glama — listed; scoring needs a release

**Listed:** <https://glama.ai/mcp/servers/Jarroslav/agentic-os> (submitted and
approved 2026-07-23). Glama clones and continuously syncs the repo from here on,
so pushes land in the listing without further action.

Notes for anyone repeating this, or listing a future server:

- Glama does **not** blanket-index every server. A maintainer with write/admin
  access submits at <https://glama.ai/mcp/servers> and authenticates through
  **GitHub OAuth** — their API is read-only and has no submit endpoint, so this
  cannot be automated or done by an agent on your behalf.
- Submissions are **human-reviewed** before becoming publicly visible; the
  listing URL 404s until approval. Check your Glama account for the status.
- The listing slug has **no `@`**: `/mcp/servers/Jarroslav/agentic-os`.
- The score badge is live and is on `mcp/README.md`:
  `https://glama.ai/mcp/servers/Jarroslav/agentic-os/badges/score.svg`

### Being listed is not being scored

Getting approved does **not** produce a quality score. Glama's overall score is
**70% Tool Definition Quality + 30% Server Coherence**, and *both* are computed
by actually building the server and introspecting it over stdio. Until a **Glama
release** exists, both are unscored, the listing's Schema tab reads "No tools /
No prompts / No resources", and the badge shows a placeholder grade — even
though the same server publishes 7 tools, 6 prompts, and 31 resources to every
other host.

The earlier note here claimed no `Dockerfile` was needed. That was true only of
getting *listed*; it is false for getting *scored*, which is why one now exists.

**In-repo, done:**

- **`/Dockerfile`** — a two-stage build of the server. It must run with the
  **repository root** as build context, not `mcp/`: `build-content.mjs` needs
  `plugins/**`, the root `LICENSE` and `NOTICE`, and a real `.git` directory
  plus the `git` binary (it enumerates bundled content with `git ls-files`).
  Verified end-to-end from a clean clone: the image builds, and a container
  answers `initialize` / `tools/list` / `prompts/list` / `resources/list` with
  all 7 tools, 6 prompts, and 31 resources.
- **`/.dockerignore`** — note it deliberately does *not* exclude `.git`, per
  the point above; it does exclude `.claude/worktrees`, which would otherwise
  send a second full checkout as build context.
- **`/glama.json`** — `{"$schema": …, "maintainers": ["Jarroslav"]}`, the one
  required field of <https://glama.ai/mcp/schemas/server.json>. Glama detects
  it within minutes of the push.
- **Tool definitions hardened against the six TDQS dimensions** (purpose
  clarity, usage guidelines, behavioural transparency, parameter semantics,
  conciseness, contextual completeness). Every tool now states when to use it
  and what it does *not* do, carries `idempotentHint`/`destructiveHint`
  alongside `readOnlyHint`, and has a `description` on **every** input *and*
  output field. This matters disproportionately because the server-level score
  is *60% mean + 40% minimum* across tools — one thin description caps the
  whole grade, so the weakest tool is the one worth fixing first.

**Only you can do these** — they need your Glama login, and no API exists for
them:

1. **Claim the server**, if it is not already claimed.
2. **Dockerfile admin page** → point the build spec at `/Dockerfile` with the
   repo root as context → **Deploy**.
3. Once the build test passes → **Make Release**, enter a version (match the
   npm version, `0.1.1`), publish. This is what unlocks Tool Definition
   Quality and Server Coherence.
4. **Profile completion** — fill in the remaining profile fields.
5. **License** shows `F` even though the repo is Apache-2.0 and GitHub's API
   reports `apache-2.0` correctly, with `LICENSE` present at both the repo root
   and in `mcp/`. That is a stale scan, not a missing file: **trigger a rescan**
   from the server admin page.
6. **Related servers** — add a few from the admin page.
7. **Recent usage** — zero by design until people call it; their **Try in
   Browser** feature seeds the first data point.

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
