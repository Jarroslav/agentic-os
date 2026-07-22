import { describe, expect, it } from 'vitest';
import { readdir, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const MCP_ROOT = fileURLToPath(new URL('..', import.meta.url));
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

// Minimal valid arguments for every tool this server advertises, keyed by
// tool name. This enumeration is deliberately NOT the source of truth for
// which tools get exercised — client.listTools() is (see the test below) —
// it only supplies arguments for tools whose required inputs can't be
// synthesized generically from the schema. A tool advertised by
// listTools() with no entry here fails that test loudly, rather than being
// silently skipped, which is what enrolls a future Phase 2b tool
// automatically instead of relying on someone remembering to add it here.
const TOOL_ARGS: Record<string, Record<string, unknown>> = {
  search_methodology: { query: 'escalation gate review' },
  get_document: { uri: 'agentic-os://skills/agentic-os/agentic-init' },
  list_presets: {},
  list_qe_blueprints: {},
  list_sdlc_phases: {},
};

describe('read-only guarantee', () => {
  it('no source file calls a write-capable fs API', async () => {
    // NOTE: link, open, chmod, chown are deliberately omitted — they're common English words
    // likely to appear in prose/comments and would make this scan unreliable.
    const banned = /\b(writeFile|writeFileSync|mkdir|mkdirSync|rm|rmSync|rmdir|rmdirSync|unlink|appendFile|createWriteStream|copyFile|copyFileSync|rename|renameSync|truncate|truncateSync|symlink|symlinkSync)\b/;
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

    try {
      // Drive the exercise loop off the server's own advertised tool list,
      // not a hand-written one — a tool added in a later phase is exercised
      // here automatically, and one with no argument mapping fails this test
      // instead of silently passing uncovered.
      const { tools } = await client.listTools();
      const exercised: string[] = [];
      for (const tool of tools) {
        const args = TOOL_ARGS[tool.name];
        if (args === undefined) {
          throw new Error(
            `Tool "${tool.name}" is advertised by listTools() but has no entry ` +
            `in TOOL_ARGS (mcp/tests/readonly.test.ts). Add minimal valid ` +
            `arguments for it so this read-only proof actually exercises it — ` +
            `see IMPORTANT 1 in the Phase 2a review.`,
          );
        }
        await client.callTool({ name: tool.name, arguments: args });
        exercised.push(tool.name);
      }
      // Sanity check on the loop itself: every one of the 5 tools shipped in
      // this phase must actually have been called, not merely present in
      // TOOL_ARGS unused.
      expect(exercised.sort()).toEqual([
        'get_document', 'list_presets', 'list_qe_blueprints',
        'list_sdlc_phases', 'search_methodology',
      ]);

      // Also exercise the resource and prompt surfaces alongside the tool
      // loop above, for the same byte-identical guarantee.
      await client.readResource({
        uri: 'agentic-os://file/agentic-os/presets/roles/qa.json',
      });
      await client.getPrompt({ name: 'sdlc-start', arguments: {} });
    } finally {
      await client.close();
    }

    expect(await fingerprint(join(REPO_ROOT, 'plugins'))).toBe(before);
  }, 30_000);
});
