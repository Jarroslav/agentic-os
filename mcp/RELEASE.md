# Release runbook

This is the maintainer's checklist for cutting a release of `agentic-os-mcp`.
It is a human-run procedure — `.github/workflows/release.yml` automates the
publish itself once you push the tag, but every step before that (bumping
versions, updating the changelog, merging) is done by hand through the normal
PR flow.

**The most important sentence in this document: npm publishes are
permanent.** npm refuses to republish a version number once it has been
published — even if you unpublish it first, that exact version can never be
reused. Unpublishing itself is also heavily restricted (npm only allows it
within 72 hours of publish, and only if no other package depends on it).
Treat every push of an `agentic-os-mcp-v*` tag as a one-way door: if the
package is broken, the fix is a **new** version, not a redo of the old one.

## One-time setup (before the first release)

1. **Create an npm automation token.**
   - Log in to npmjs.com as the account that will own the `agentic-os-mcp`
     package.
   - Account Settings → Access Tokens → Generate New Token → **Automation**
     (automation tokens work in CI without 2FA prompts and are scoped for
     exactly this use — publishing from a script, not a human session).
   - Copy the token immediately; npm shows it only once.
2. **Add it as the `NPM_TOKEN` repository secret** (Settings → Secrets and
   variables → Actions → New repository secret, name `NPM_TOKEN`). This is
   the secret `.github/workflows/release.yml`'s "Publish to npm" step reads
   as `NODE_AUTH_TOKEN`.
3. **Confirm the MCP Registry namespace case.** `mcp/package.json` declares
   `mcpName: "io.github.jarroslav/agentic-os"` (lowercase), and
   `mcp/server.json`'s `name` matches it — but the GitHub account is
   `Jarroslav` (capital J). GitHub Registry namespaces are derived from your
   GitHub login, and **only an actual `mcp-publisher login github` (or
   `github-oidc`) run against the real registry proves which case it
   normalizes to.** Do not assume lowercase is correct just because it's
   the npm/URL convention elsewhere.
   - Before the first release, run `mcp-publisher login github` locally (or
     watch the first `release.yml` run's "Authenticate to MCP Registry"
     step) and check what namespace it grants.
   - If the Registry expects `io.github.Jarroslav/agentic-os` instead, update
     `mcpName` in `package.json` and `name` in `server.json` together (both
     must still agree, per `mcp/tests/package.test.ts`) **before** cutting
     the first release — a namespace mismatch after publish means a wasted,
     unreusable npm version (see the note above).
   - This step needs doing exactly once; after the first successful Registry
     publish, the correct case is confirmed and this note can be deleted.

No setup is needed for the Registry side beyond the above: the release
workflow authenticates with `mcp-publisher login github-oidc`, which uses the
workflow's own GitHub Actions OIDC token — no PAT, no additional secret.

## Each release

1. **Bump the version in all three files, together:**
   - `mcp/package.json` → `version`
   - `mcp/server.json` → `version` (and `packages[0].version`)
   - `mcp/manifest.json` → `version`

   `mcp/tests/package.test.ts` asserts all three agree with each other (and
   with `server.json`'s `name` / `packages[0].identifier` against
   `package.json`'s `mcpName` / `name`) — a mismatch fails `npm test` before
   you ever reach the tag.
2. **Move `mcp/CHANGELOG.md`'s `[Unreleased]` entries under the new version
   heading**, dated, following Keep a Changelog.
3. **Open a PR, get it through the `gate` and `mcp` CI checks and review, and
   merge to `main`** — the normal workflow described in `CONTRIBUTING.md`.
   Do this *before* tagging: the tag must point at a commit that has already
   passed CI once as a PR, not at unreviewed work.
4. **Tag the merge commit and push the tag:**

   ```bash
   git checkout main && git pull
   git tag -a agentic-os-mcp-v0.2.0 -m "agentic-os-mcp 0.2.0"
   git push origin agentic-os-mcp-v0.2.0
   ```

   Pushing the tag triggers `.github/workflows/release.yml`, which re-runs
   the full repo gate, asserts the tag matches `package.json`'s version,
   publishes to npm (`npm publish --provenance --access public`), then — only
   if that succeeded — publishes `server.json` to the MCP Registry, then
   builds the `.mcpb` bundle and attaches it to a GitHub release for the tag.
5. **Watch the `release` workflow run to completion** in the Actions tab.
   A failure partway through (e.g. the Registry publish, after npm already
   succeeded) does not roll npm back — see "What is irreversible" above.
   If the Registry step fails after a successful npm publish, you can re-run
   just that step manually (`mcp-publisher login github-oidc && mcp-publisher
   publish mcp/server.json` from a checkout at the tag) without touching npm
   again.

## Verifying a release afterwards

Run all three:

```bash
# 1. The package metadata npm actually has
npm view agentic-os-mcp

# 2. A fresh-machine install path — no local cache, no dist/ already built
npx -y agentic-os-mcp

# 3. The Registry listing (replace the namespace if step 3 of one-time
#    setup above found it differs from io.github.jarroslav)
curl -s https://registry.modelcontextprotocol.io/v0/servers?search=agentic-os
```

`npm view` confirms the version, tarball contents summary, and provenance
attestation are what you expect. `npx -y agentic-os-mcp` is the same command
end users run — it should download, build nothing (the tarball ships
pre-built `dist/`), and start the stdio server (Ctrl-C to exit; there is no
output on a bare stdio connection with nothing talking to it, which is
expected). The Registry query confirms the listing is live and its version
matches.

Once verified, remove the "Not yet published" caveat from `mcp/README.md`'s
Install section in a follow-up commit (see the note left there).
