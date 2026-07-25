#!/usr/bin/env node
// Packs mcp/ into a .mcpb bundle containing only what the server needs at
// run time: the compiled dist/, the runtime-loaded content-index.json,
// legal files, the manifest/server descriptors, and a *production-only*
// node_modules.
//
// `mcpb pack` bundles whatever node_modules it finds next to manifest.json.
// A developer's checkout has devDependencies installed (typescript, vite,
// esbuild, rollup, vitest) — none of which the running server imports — so
// packing the working tree in place ships ~55MB of dead weight and needless
// supply-chain surface to every user who installs the bundle.
//
// This packs from an isolated staging copy instead of doing
// `npm ci --omit=dev` in the working tree and reinstalling afterwards.
// Reinstalling-after is a two-step, non-atomic sequence: an interrupted
// build (crash, Ctrl-C, a failed `npm ci --omit=dev`, a failed pack) can
// leave the developer's own node_modules stripped of devDependencies with
// no automatic recovery, right when they need vitest to figure out why the
// build failed. A staging copy never touches the working tree's
// node_modules at all, so there is nothing to restore and no failure mode
// that surprises the developer.
import { cp, mkdtemp, rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const HERE = dirname(fileURLToPath(import.meta.url));
const MCP_ROOT = join(HERE, '..');

// Everything the running server (or `npm ci` staging it) needs. Deliberately
// excludes tests/, src/, and scripts/ — dev-only, and also belt-and-braces
// covered by .mcpbignore in case this script is ever bypassed in favour of
// a plain `mcpb pack`.
// Version pinned deliberately (same rationale as ci.yml's Inspector CLI
// pin): this runs after `npm publish` in the release workflow, so an
// unrelated upstream @anthropic-ai/mcpb release cannot turn a release run
// red at the one point where a failure is most disruptive to recover from.
// Should be bumped intentionally, verifying with `npm run build:mcpb`
// locally first.
const MCPB_VERSION = '2.1.2';

const RUNTIME_ENTRIES = [
  'dist',
  'content-index.json',
  'LICENSE',
  'NOTICE',
  'README.md',
  'CHANGELOG.md',
  'manifest.json',
  'server.json',
  'package.json',
  // Not needed by the running server, but required *in the staging copy*
  // so `npm ci` there resolves the exact locked graph. `mcpb pack` drops
  // package-lock.json via its own built-in EXCLUDE_PATTERNS regardless, so
  // it never reaches the final bundle.
  'package-lock.json',
  // Governs the staging pack the same way it governs an in-place one —
  // copied so the tsconfig.json un-exclude (and the /tests//src//scripts/
  // excludes) still apply to the staged dist/content/.
  '.mcpbignore',
];

async function main() {
  const entryPoint = join(MCP_ROOT, 'dist', 'index.js');
  if (!existsSync(entryPoint)) {
    throw new Error(
      'mcp/dist/index.js not found — run `npm run build` before `npm run build:mcpb`.',
    );
  }

  const stageDir = await mkdtemp(join(tmpdir(), 'agentic-os-mcpb-'));
  try {
    for (const entry of RUNTIME_ENTRIES) {
      const src = join(MCP_ROOT, entry);
      if (!existsSync(src)) {
        throw new Error(`build-mcpb: required ${src} is missing — cannot stage a bundle without it.`);
      }
      await cp(src, join(stageDir, entry), { recursive: true });
    }

    console.log('[build-mcpb] installing production-only dependencies into staging copy...');
    execFileSync('npm', ['ci', '--omit=dev', '--ignore-scripts'], {
      cwd: stageDir,
      stdio: 'inherit',
    });

    const outputPath = join(MCP_ROOT, 'mcp.mcpb');
    console.log('[build-mcpb] packing...');
    execFileSync(
      'npx',
      ['--yes', `@anthropic-ai/mcpb@${MCPB_VERSION}`, 'pack', stageDir, outputPath],
      { cwd: MCP_ROOT, stdio: 'inherit' },
    );
    console.log(`[build-mcpb] wrote ${outputPath}`);
  } finally {
    await rm(stageDir, { recursive: true, force: true });
  }
}

await main();
