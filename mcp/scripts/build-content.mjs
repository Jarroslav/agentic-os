#!/usr/bin/env node
// Copies plugins/** into dist/content/ and emits content-index.json.
// This is the ONLY path from plugins/ into the published package.
import { createHash } from 'node:crypto';
import { readFile, mkdir, writeFile, rm } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
export const MCP_ROOT = join(HERE, '..');
export const REPO_ROOT = join(MCP_ROOT, '..');
export const PLUGINS_DIR = join(REPO_ROOT, 'plugins');

// The index's source of truth is git-tracked files under plugins/, not the
// working tree. Anything untracked (a local .pytest_cache, .DS_Store, .venv,
// .idea, editor swap file, …) is invisible to `git ls-files` and therefore
// can never be baked into the committed index — no per-name skip list to
// keep up to date, and no way for one contributor's local debris to end up
// shipped in another contributor's tarball.
function gitTrackedPluginFiles() {
  const out = execFileSync('git', ['ls-files', '-z', 'plugins'], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
  });
  // `-z` NUL-terminates every entry, including the last, so splitting on '\0'
  // always yields one trailing empty string — drop it.
  return out.split('\0').filter(rel => rel.length > 0);
}

/** @returns {Promise<Record<string,string>>} repo-relative POSIX path -> sha256 */
export async function buildIndex() {
  const files = gitTrackedPluginFiles().sort();
  const index = {};
  for (const rel of files) {
    const buf = await readFile(join(REPO_ROOT, rel));
    index[rel] = createHash('sha256').update(buf).digest('hex');
  }
  return index;
}

async function main() {
  const index = await buildIndex();
  const contentDir = join(MCP_ROOT, 'dist', 'content');
  await rm(contentDir, { recursive: true, force: true });
  for (const rel of Object.keys(index)) {
    const dest = join(contentDir, rel);
    await mkdir(dirname(dest), { recursive: true });
    await writeFile(dest, await readFile(join(REPO_ROOT, rel)));
  }
  await writeFile(
    join(MCP_ROOT, 'content-index.json'),
    JSON.stringify(index, null, 2) + '\n',
  );
  console.log(`bundled ${Object.keys(index).length} files`);
}

if (import.meta.url === `file://${process.argv[1]}`) await main();
