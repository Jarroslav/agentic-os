#!/usr/bin/env node
// Copies plugins/** into dist/content/ and emits content-index.json.
// This is the ONLY path from plugins/ into the published package.
import { createHash } from 'node:crypto';
import { readdir, readFile, mkdir, writeFile, rm } from 'node:fs/promises';
import { dirname, join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
export const MCP_ROOT = join(HERE, '..');
export const REPO_ROOT = join(MCP_ROOT, '..');
export const PLUGINS_DIR = join(REPO_ROOT, 'plugins');

// Directories never shipped: caches and per-skill eval fixtures the server
// has no way to run. Excluding them keeps the package lean and the index stable.
const SKIP_DIRS = new Set(['__pycache__', 'node_modules', '.git']);

async function walk(dir, out = []) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      if (SKIP_DIRS.has(entry.name)) continue;
      await walk(join(dir, entry.name), out);
    } else if (entry.isFile()) {
      out.push(join(dir, entry.name));
    }
  }
  return out;
}

/** @returns {Promise<Record<string,string>>} repo-relative POSIX path -> sha256 */
export async function buildIndex() {
  const files = (await walk(PLUGINS_DIR)).sort();
  const index = {};
  for (const abs of files) {
    const rel = relative(REPO_ROOT, abs).split(sep).join('/');
    const buf = await readFile(abs);
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
