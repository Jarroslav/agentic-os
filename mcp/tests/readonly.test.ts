import { describe, expect, it } from 'vitest';
import { readdir, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const MCP_ROOT = new URL('..', import.meta.url).pathname;
const REPO_ROOT = join(MCP_ROOT, '..');

async function fingerprint(dir: string): Promise<string> {
  const hash = createHash('sha256');
  const walk = async (d: string): Promise<void> => {
    for (const e of (await readdir(d, { withFileTypes: true })).sort(
      (a, b) => a.name.localeCompare(b.name),
    )) {
      if (e.name === '__pycache__' || e.name === 'node_modules') continue;
      const p = join(d, e.name);
      if (e.isDirectory()) await walk(p);
      else if (e.isFile()) hash.update(p).update(await readFile(p));
    }
  };
  await walk(dir);
  return hash.digest('hex');
}

describe('read-only guarantee', () => {
  it('no source file calls a write-capable fs API', async () => {
    const banned = /\b(writeFile|writeFileSync|mkdir|mkdirSync|rm|rmSync|unlink|appendFile|createWriteStream)\b/;
    const offenders: string[] = [];
    const walk = async (d: string): Promise<void> => {
      for (const e of await readdir(d, { withFileTypes: true })) {
        const p = join(d, e.name);
        if (e.isDirectory()) await walk(p);
        else if (p.endsWith('.ts') && banned.test(await readFile(p, 'utf8'))) {
          offenders.push(p);
        }
      }
    };
    await walk(join(MCP_ROOT, 'src'));
    expect(offenders).toEqual([]);
  });

  it('leaves plugins/ byte-identical after exercising every tool', async () => {
    const before = await fingerprint(join(REPO_ROOT, 'plugins'));

    const client = new Client({ name: 'ro-test', version: '0.0.0' });
    await client.connect(new StdioClientTransport({
      command: 'node', args: ['dist/index.js'], cwd: MCP_ROOT,
    }));

    await client.callTool({
      name: 'search_methodology', arguments: { query: 'escalation gate review' },
    });
    await client.callTool({
      name: 'get_document',
      arguments: { uri: 'agentic-os://skills/agentic-os/agentic-init' },
    });
    await client.readResource({
      uri: 'agentic-os://file/agentic-os/presets/roles/qa.json',
    });
    await client.getPrompt({ name: 'sdlc-start', arguments: {} });
    await client.close();

    expect(await fingerprint(join(REPO_ROOT, 'plugins'))).toBe(before);
  }, 30_000);
});
