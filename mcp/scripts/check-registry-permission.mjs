#!/usr/bin/env node
// Preflight for the release workflow: proves the just-obtained MCP Registry
// JWT actually grants publish permission on server.json's declared `name`
// *before* `npm publish` runs — the whole point of moving `mcp-publisher
// login` ahead of the npm step (see .github/workflows/release.yml).
//
// Why this exists at all: the Registry grants permission by fetching the
// OIDC `repository_owner` claim verbatim (no case-folding) and matching it
// against `server.json`'s `name` with a case-sensitive prefix check.
// Confirmed directly against upstream (modelcontextprotocol/registry):
//   - internal/api/handlers/v0/auth/github_oidc.go's buildPermissions grants
//     `io.github.<repository_owner>/*` using the raw OIDC claim, unmodified.
//   - internal/auth/jwt.go's isResourceMatch is `strings.HasPrefix` with no
//     ToLower anywhere in that file, publish.go, or github_oidc.go.
// So a case mismatch between our declared name and the real GitHub owner
// login is invisible until the Registry actually 403s — which, without this
// preflight, would happen *after* npm publish has already burned a version
// number (npm never lets you republish or reuse one, even after unpublishing
// within the 72-hour window).
//
// This script requires nothing beyond what `mcp-publisher login` already
// wrote to disk, so it costs no extra network round-trip and no extra
// secret.
import { readFile } from 'node:fs/promises';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

// Matches upstream cmd/publisher/commands/login.go's tokenFilePath(): always
// ~/.config/mcp-publisher/token.json, never overridable by flag or env.
const TOKEN_PATH = join(homedir(), '.config', 'mcp-publisher', 'token.json');

export function decodeBase64Url(segment) {
  const padded = segment.replace(/-/g, '+').replace(/_/g, '/').padEnd(
    segment.length + ((4 - (segment.length % 4)) % 4),
    '=',
  );
  return Buffer.from(padded, 'base64').toString('utf8');
}

// Reimplements upstream internal/auth/jwt.go's isResourceMatch exactly:
// a pattern ending in "*" is a prefix match (case-sensitive, no
// normalization anywhere in that call chain); otherwise it's an exact
// match. Deliberately does not lowercase either side — doing so would hide
// the exact class of bug this script exists to catch.
export function isResourceMatch(resource, pattern) {
  if (pattern.endsWith('*')) {
    return resource.startsWith(pattern.slice(0, -1));
  }
  return resource === pattern;
}

// Pure decision function, split out from main() so tests can drive it
// directly without touching the filesystem or process.exit.
export function checkPermission(declaredName, permissions) {
  return permissions.filter(
    (p) => p && p.action === 'publish' && typeof p.resource === 'string' && isResourceMatch(declaredName, p.resource),
  );
}

export async function main() {
  const serverJsonPath = process.argv[2] ?? join(process.cwd(), 'server.json');

  let tokenRaw;
  try {
    tokenRaw = await readFile(TOKEN_PATH, 'utf8');
  } catch (err) {
    throw new Error(
      `check-registry-permission: could not read ${TOKEN_PATH} (${err.code ?? err.message}). ` +
      'Run `mcp-publisher login github-oidc` (CI) or `mcp-publisher login github` (local) first.',
    );
  }

  let tokenInfo;
  try {
    tokenInfo = JSON.parse(tokenRaw);
  } catch {
    throw new Error(`check-registry-permission: ${TOKEN_PATH} is not valid JSON.`);
  }

  const jwt = tokenInfo.token;
  if (typeof jwt !== 'string' || jwt.length === 0) {
    throw new Error(`check-registry-permission: ${TOKEN_PATH} has no "token" field.`);
  }

  const parts = jwt.split('.');
  if (parts.length !== 3) {
    throw new Error(
      `check-registry-permission: token in ${TOKEN_PATH} is not a 3-part JWT (got ${parts.length} part(s)).`,
    );
  }

  let claims;
  try {
    claims = JSON.parse(decodeBase64Url(parts[1]));
  } catch (err) {
    throw new Error(`check-registry-permission: could not decode/parse the JWT payload: ${err.message}`);
  }

  const permissions = Array.isArray(claims.permissions) ? claims.permissions : [];

  const serverJson = JSON.parse(await readFile(serverJsonPath, 'utf8'));
  const declaredName = serverJson.name;
  if (typeof declaredName !== 'string' || declaredName.length === 0) {
    throw new Error(`check-registry-permission: ${serverJsonPath} has no "name" field.`);
  }

  // Field name is `resource` in the JWT (Go struct tag `json:"resource"` on
  // auth.Permission.ResourcePattern) -- NOT `resource_pattern`. Checked
  // directly against internal/auth/jwt.go; documenting here so nobody
  // "fixes" this to match a plausible-looking but wrong field name.
  const matches = checkPermission(declaredName, permissions);

  if (matches.length === 0) {
    const granted = permissions
      .map((p) => `${p.action ?? '<no action>'}:${p.resource ?? '<no resource>'}`)
      .join(', ') || '(none)';
    console.error('::error::MCP Registry token does not grant publish permission for this server.');
    console.error(`::error::Declared name (server.json): ${declaredName}`);
    console.error(`::error::Granted permissions: ${granted}`);
    console.error(
      '::error::This would 403 at the Registry publish step -- after npm publish, which cannot be undone. ' +
      'Aborting before npm publish runs. Most likely cause: server.json/package.json\'s declared ' +
      'namespace case does not match the real GitHub owner login (Registry grants are case-sensitive, ' +
      'derived from the raw OIDC repository_owner claim -- see mcp/RELEASE.md).',
    );
    process.exit(1);
  }

  console.log(
    `check-registry-permission: OK -- "${declaredName}" is covered by granted permission ` +
    `"${matches[0].resource}".`,
  );
}

// Only run when executed directly (`node check-registry-permission.mjs`),
// not when imported by tests.
const isDirectRun = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];
if (isDirectRun) {
  await main();
}
