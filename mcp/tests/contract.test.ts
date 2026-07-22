import { describe, expect, it, beforeAll, afterAll } from 'vitest';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

let client: Client;

beforeAll(async () => {
  client = new Client({ name: 'test', version: '0.0.0' });
  await client.connect(new StdioClientTransport({
    command: 'node',
    args: ['dist/index.js'],
    cwd: new URL('..', import.meta.url).pathname,
  }));
}, 30_000);

afterAll(async () => { await client.close(); });

describe('protocol contract', () => {
  it('lists one resource per skill', async () => {
    const { resources } = await client.listResources();
    expect(resources.length).toBeGreaterThanOrEqual(31);
    expect(resources.map(r => r.uri)).toContain(
      'agentic-os://skills/agentic-os/agentic-init',
    );
  });

  it('reads a skill resource', async () => {
    const res = await client.readResource({
      uri: 'agentic-os://skills/agentic-qe/qe-blueprints',
    });
    expect(res.contents[0]?.mimeType).toBe('text/markdown');
    expect(String(res.contents[0]?.text)).toContain('blueprint');
  });

  it('reads an arbitrary plugin file through the file template', async () => {
    const res = await client.readResource({
      uri: 'agentic-os://file/agentic-os/presets/roles/developer.json',
    });
    expect(String(res.contents[0]?.text)).toContain('"name": "developer"');
  });

  it('rejects an unknown resource URI', async () => {
    await expect(client.readResource({
      uri: 'agentic-os://file/agentic-os/../../LICENSE',
    })).rejects.toThrow();
  });

  it('exposes the six workflow prompts', async () => {
    const { prompts } = await client.listPrompts();
    expect(prompts.map(p => p.name).sort()).toEqual([
      'agentic-doctor', 'agentic-init', 'agentic-upgrade',
      'qe-blueprint-scaffold', 'sdlc-start', 'sdlc-task',
    ]);
  });

  it('a prompt returns the skill body plus the read-only preamble', async () => {
    const res = await client.getPrompt({ name: 'agentic-init', arguments: {} });
    const text = String(res.messages[0]?.content.text);
    expect(text).toContain('you must perform every file write yourself');
    expect(text).toContain('agentic-init — the installer');
  });
});
