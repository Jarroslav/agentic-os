#!/usr/bin/env node
// Fails when the committed content-index.json no longer matches plugins/**.
// This is what turns "someone edited a plugin and forgot to rebuild" red.
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { buildIndex, MCP_ROOT } from './build-content.mjs';

const live = await buildIndex();
const committed = JSON.parse(
  await readFile(join(MCP_ROOT, 'content-index.json'), 'utf8'),
);

const problems = [];
for (const [path, sha] of Object.entries(live)) {
  if (!(path in committed)) problems.push(`added, not indexed: ${path}`);
  else if (committed[path] !== sha) problems.push(`changed since index: ${path}`);
}
for (const path of Object.keys(committed)) {
  if (!(path in live)) problems.push(`indexed, but gone: ${path}`);
}

if (problems.length) {
  console.error('content drift detected:\n  ' + problems.join('\n  '));
  console.error('\nfix: cd mcp && npm run build:content, then commit content-index.json');
  process.exit(1);
}
console.log(`content index matches plugins/ (${Object.keys(live).length} files)`);
