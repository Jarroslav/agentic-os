import { afterAll, describe, expect, it } from 'vitest';
import { mkdtempSync, rmSync, symlinkSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

// Regression test for the entrypoint guard in src/index.ts.
//
// npm installs a package's `bin` as a SYMLINK under node_modules/.bin. So
// `npx agentic-os-mcp`, a global install, and every MCP client that spawns
// the advertised command all launch the server through a symlink, where
// `process.argv[1]` is the symlink path but `import.meta.url` resolves the
// symlink to dist/index.js. A raw `import.meta.url === file://${argv[1]}`
// guard is false in that case, so main() never runs and the process exits 0
// without connecting — the server appears to "start" then immediately drop
// the transport (MCP clients report `-32000: Connection closed`).
//
// readonly.test.ts spawns `node dist/index.js` with the LITERAL path, which
// is the one launch mode where argv[1] already equals the real path — so it
// never exercised the symlink path and the bug shipped in 0.1.0. This test
// closes that gap by launching through a real symlink, exactly as npm's
// .bin does.

const MCP_ROOT = fileURLToPath(new URL('..', import.meta.url));
const tmp = mkdtempSync(join(tmpdir(), 'agentic-os-mcp-bin-'));

afterAll(() => {
  rmSync(tmp, { recursive: true, force: true });
});

describe('bin entrypoint via symlink (npx / global install / .bin)', () => {
  it('starts and serves tools when launched through a symlink to dist/index.js', async () => {
    // Mirror npm's node_modules/.bin/<name> -> ../<pkg>/dist/index.js symlink.
    const link = join(tmp, 'agentic-os-mcp');
    symlinkSync(join(MCP_ROOT, 'dist', 'index.js'), link);

    const client = new Client({ name: 'bin-test', version: '0.0.0' });
    await client.connect(
      new StdioClientTransport({ command: 'node', args: [link], stderr: 'ignore' }),
    );

    try {
      const { tools } = await client.listTools();
      // The full tool surface must be reachable, proving main() actually ran.
      expect(tools.map(t => t.name).sort()).toEqual([
        'get_document', 'list_presets', 'list_qe_blueprints',
        'list_sdlc_phases', 'plan_install', 'run_doctor', 'search_methodology',
      ]);
    } finally {
      await client.close();
    }
  }, 30_000);
});
