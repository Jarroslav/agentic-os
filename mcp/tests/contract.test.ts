import { describe, expect, it, beforeAll, afterAll } from 'vitest';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const MCP_ROOT = fileURLToPath(new URL('..', import.meta.url));

let client: Client;

beforeAll(async () => {
  client = new Client({ name: 'test', version: '0.0.0' });
  await client.connect(new StdioClientTransport({
    command: 'node',
    args: ['dist/index.js'],
    cwd: MCP_ROOT,
  }));
}, 30_000);

afterAll(async () => { await client.close(); });

describe('protocol contract', () => {
  // mcp/src/index.ts hardcodes `version` in the McpServer constructor,
  // duplicating package.json's version with nothing asserting they agree —
  // the existing repo-wide version-sync gate (tests/lib/check-manifests.py)
  // only walks plugins/, so it does not cover mcp/. This test is that
  // missing assertion: it connects like a real client and reads the
  // reported version back from the initialize handshake via the SDK's
  // getServerVersion(), rather than re-reading package.json from src/ at
  // runtime (which would give content.ts a second filesystem reader).
  it('reports a server version matching package.json', async () => {
    const pkg = JSON.parse(
      await readFile(join(MCP_ROOT, 'package.json'), 'utf8'),
    ) as { version: string };
    expect(client.getServerVersion()?.version).toBe(pkg.version);
  });

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

describe('search_methodology', () => {
  it('is advertised as read-only with an output schema', async () => {
    const { tools } = await client.listTools();
    const t = tools.find(x => x.name === 'search_methodology');
    expect(t?.annotations?.readOnlyHint).toBe(true);
    expect(t?.outputSchema).toBeDefined();
  });

  it('finds the escalation ladder', async () => {
    const res = await client.callTool({
      name: 'search_methodology',
      arguments: { query: 'HITL escalation ladder' },
    });
    const { results } = res.structuredContent as {
      results: Array<{ uri: string; snippet: string }>;
    };
    expect(results.length).toBeGreaterThan(0);
    expect(results[0]?.uri.startsWith('agentic-os://')).toBe(true);
    expect(results[0]?.snippet.length).toBeGreaterThan(0);
  });

  it('filters by plugin', async () => {
    const res = await client.callTool({
      name: 'search_methodology',
      arguments: { query: 'blueprint', plugin: 'agentic-qe' },
    });
    const { results } = res.structuredContent as { results: Array<{ plugin: string }> };
    expect(results.length).toBeGreaterThan(0);
    expect(results.every(r => r.plugin === 'agentic-qe')).toBe(true);
  });

  it('returns an empty list rather than erroring on no match', async () => {
    const res = await client.callTool({
      name: 'search_methodology',
      arguments: { query: 'zzzzqqqxxnomatch' },
    });
    expect((res.structuredContent as { results: unknown[] }).results).toEqual([]);
  });

  it('does not treat "ai" as a substring match inside unrelated words', async () => {
    // Before the word-start fix, "ai" matched inside "again", "maintain",
    // "domain", "explain", "available", etc. via raw indexOf. Measured
    // against this corpus that's 182 of 195 documents (global, unscoped) —
    // vastly more than the 51 that contain "ai" as (or at the start of) an
    // actual word.
    //
    // The tool's `limit` schema caps at 25, and both the buggy count (182)
    // and the fixed count (51) exceed that cap, so an unscoped query
    // returns exactly 25 results either way — asserting on that number
    // alone can't distinguish the two behaviors. Scoping to the
    // `agentic-sdlc` plugin (111 docs) avoids the cap: raw substring
    // matches 100 of them (still capped at 25), but word-start matching
    // only 9, so a fixed implementation returns well under 25 results here.
    const res = await client.callTool({
      name: 'search_methodology',
      arguments: { query: 'ai', plugin: 'agentic-sdlc', limit: 25 },
    });
    const { results } = res.structuredContent as { results: Array<{ uri: string }> };
    expect(results.length).toBeGreaterThan(0);
    expect(results.length).toBeLessThan(20);
  });

  it('still matches suffixed forms at a word start ("gate" finds "gates")', async () => {
    const res = await client.callTool({
      name: 'search_methodology',
      arguments: { query: 'gate', limit: 25 },
    });
    const { results } = res.structuredContent as {
      results: Array<{ snippet: string }>;
    };
    expect(results.length).toBeGreaterThan(0);
    expect(results.some(r => /gates/i.test(r.snippet))).toBe(true);
  });

  it('does not match a term that only ever occurs mid-word', async () => {
    // "tio" (as in "action", "section", "solution") never begins a word
    // anywhere in the corpus, so word-start matching must find nothing.
    const res = await client.callTool({
      name: 'search_methodology',
      arguments: { query: 'tio', limit: 25 },
    });
    const { results } = res.structuredContent as { results: unknown[] };
    expect(results).toEqual([]);
  });

  it('never emits an unpaired surrogate in a snippet whose window crosses an astral emoji', async () => {
    // plugins/agentic-sdlc/agents/guide-sync.md contains four astral-plane
    // emoji (📊 🔴 🟡 🔵) starting at UTF-16 code unit 8168. "findings" is
    // this document's first word-start match for that token — at index
    // 8009 — and snippet()'s window is [match.index - 80, match.index +
    // 160), so the end edge lands at 8169: exactly one code unit past 8168,
    // the high surrogate of 📊. A raw `text.slice(start, end)` there keeps
    // the high surrogate and drops its low-surrogate partner (verified by
    // temporarily reverting safeBoundary() and confirming this assertion
    // fails); safeBoundary() must nudge the edge back off that boundary.
    const UNPAIRED_SURROGATE =
      /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/;
    const res = await client.callTool({
      name: 'search_methodology',
      arguments: { query: 'findings', plugin: 'agentic-sdlc', limit: 25 },
    });
    const { results } = res.structuredContent as {
      results: Array<{ uri: string; snippet: string }>;
    };
    const hit = results.find(r => r.uri === 'agentic-os://file/agentic-sdlc/agents/guide-sync.md');
    expect(hit).toBeDefined();
    expect(UNPAIRED_SURROGATE.test(hit!.snippet)).toBe(false);
  });
});

describe('get_document', () => {
  it('returns a whole small document untruncated', async () => {
    const res = await client.callTool({
      name: 'get_document',
      arguments: { uri: 'agentic-os://skills/agentic-os/agentic-doctor' },
    });
    const out = res.structuredContent as
      { text: string; truncated: boolean; total_chars: number };
    expect(out.truncated).toBe(false);
    expect(Array.from(out.text).length).toBe(out.total_chars);
    expect(out.text).toContain('install verifier');
  });

  it('truncates and flags when over max_chars', async () => {
    const res = await client.callTool({
      name: 'get_document',
      arguments: {
        uri: 'agentic-os://skills/agentic-os/agentic-doctor',
        max_chars: 200,
      },
    });
    const out = res.structuredContent as
      { text: string; truncated: boolean; total_chars: number };
    expect(out.truncated).toBe(true);
    expect(out.text.length).toBe(200);
    expect(out.total_chars).toBeGreaterThan(200);
  });

  it('reports an unknown URI as a tool error, not a crash', async () => {
    const res = await client.callTool({
      name: 'get_document',
      arguments: { uri: 'agentic-os://file/agentic-os/does/not/exist.md' },
    });
    expect(res.isError).toBe(true);
    expect(String((res.content as Array<{ text: string }>)[0]?.text))
      .toContain('search_methodology');
  });
});

describe('get_document surrogate safety and max_chars ceiling', () => {
  // plugins/agentic-sdlc/agents/guide-sync.md contains four astral-plane
  // emoji (📊 U+1F4CA, 🔴 U+1F534, 🟡 U+1F7E1, 🔵 U+1F535). A scan of the
  // file (`Array.from(text)` vs raw UTF-16 index) found the first, 📊, at
  // UTF-16 code units 8168 (high surrogate) / 8169 (low surrogate) — no
  // astral character occurs earlier in the file, so the UTF-16 offset and
  // the code-point offset agree up to that point. max_chars: 8169 is
  // exactly the cut a naive `text.slice(0, max_chars)` would make: it keeps
  // code unit 8168 (the high surrogate) but drops unit 8169 (its low-half
  // partner), which is precisely the split this fix must prevent.
  const ASTRAL_URI = 'agentic-os://file/agentic-sdlc/agents/guide-sync.md';
  const SPLIT_OFFSET = 8169;
  const UNPAIRED_SURROGATE =
    /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/;

  it('is servable and truncation never emits an unpaired surrogate at the astral boundary', async () => {
    const res = await client.callTool({
      name: 'get_document',
      arguments: { uri: ASTRAL_URI, max_chars: SPLIT_OFFSET },
    });
    const out = res.structuredContent as
      { text: string; truncated: boolean; total_chars: number };
    expect(out.truncated).toBe(true);
    expect(UNPAIRED_SURROGATE.test(out.text)).toBe(false);
  });

  it('keeps total_chars greater than the returned text, measured in the same unit', async () => {
    const res = await client.callTool({
      name: 'get_document',
      arguments: { uri: ASTRAL_URI, max_chars: SPLIT_OFFSET },
    });
    const out = res.structuredContent as
      { text: string; truncated: boolean; total_chars: number };
    expect(out.truncated).toBe(true);
    // total_chars is counted in Unicode code points (see get_document.ts),
    // so compare against the returned text's code-point count rather than
    // its UTF-16 .length, to use the same unit total_chars is measured in.
    expect(out.total_chars).toBeGreaterThan(Array.from(out.text).length);
  });

  it('rejects max_chars above the new 50,000 ceiling', async () => {
    // The MCP SDK surfaces a zod schema failure as a resolved CallToolResult
    // with isError: true (same convention as the "unknown URI" test above),
    // not a rejected promise — so assert on isError, not on `.rejects`.
    const res = await client.callTool({
      name: 'get_document',
      arguments: {
        uri: 'agentic-os://skills/agentic-os/agentic-doctor',
        max_chars: 200_000,
      },
    });
    expect(res.isError).toBe(true);
    expect(String((res.content as Array<{ text: string }>)[0]?.text))
      .toContain('50000');
  });

  it('accepts max_chars at the new 50,000 ceiling', async () => {
    const res = await client.callTool({
      name: 'get_document',
      arguments: {
        uri: 'agentic-os://skills/agentic-os/agentic-doctor',
        max_chars: 50_000,
      },
    });
    expect(res.isError).toBeFalsy();
  });
});

describe('list_presets', () => {
  it('is advertised read-only with an output schema', async () => {
    const { tools } = await client.listTools();
    const t = tools.find(x => x.name === 'list_presets');
    expect(t?.annotations?.readOnlyHint).toBe(true);
    expect(t?.outputSchema).toBeDefined();
  });

  it('returns all seven role presets', async () => {
    const res = await client.callTool({ name: 'list_presets', arguments: {} });
    const { presets } = res.structuredContent as {
      presets: Array<{ name: string; uri: string; hitl_default: string }>;
    };
    expect(presets.map(p => p.name).sort()).toEqual([
      'architect', 'ba-po', 'developer', 'devops',
      'pm-delivery', 'portfolio', 'qa',
    ]);
  });

  it('carries the HITL default and a resolvable uri', async () => {
    const res = await client.callTool({ name: 'list_presets', arguments: {} });
    const { presets } = res.structuredContent as {
      presets: Array<{ name: string; uri: string; hitl_default: string; template_count: number }>;
    };
    const qa = presets.find(p => p.name === 'qa');
    expect(qa?.hitl_default).toBe('strict');
    expect(qa?.uri).toBe('agentic-os://presets/qa');
    expect(qa?.template_count).toBeGreaterThan(0);

    // the uri it advertises must actually resolve
    const doc = await client.readResource({ uri: qa!.uri });
    expect(String(doc.contents[0]?.text)).toContain('"name": "qa"');
  });

  it('does not dump full template arrays', async () => {
    const res = await client.callTool({ name: 'list_presets', arguments: {} });
    expect(JSON.stringify(res.structuredContent)).not.toContain('hooks/precommit-review-gate');
  });

  it('returns exactly as many presets as the content index has preset files', async () => {
    // Guards against list_presets.ts reverting to a hardcoded role list: the
    // index (mcp/content-index.json), built from the filesystem at build
    // time, is the authority on what preset files actually exist. A
    // hardcoded array that drifts from that set — a preset added or removed
    // under plugins/agentic-os/presets/roles/ without updating the constant —
    // must fail this test.
    const index: Record<string, string> = JSON.parse(
      await readFile(join(MCP_ROOT, 'content-index.json'), 'utf8'),
    );
    const PRESET_PATH = /^plugins\/agentic-os\/presets\/roles\/([^/]+)\.json$/;
    const presetFileCount = Object.keys(index).filter(k => PRESET_PATH.test(k)).length;

    const res = await client.callTool({ name: 'list_presets', arguments: {} });
    const { presets } = res.structuredContent as { presets: Array<{ name: string }> };

    expect(presetFileCount).toBeGreaterThan(0);
    expect(presets.length).toBe(presetFileCount);
  });
});

describe('preset and blueprint URI aliases', () => {
  it('reads a preset by its alias', async () => {
    const res = await client.readResource({ uri: 'agentic-os://presets/qa' });
    expect(res.contents[0]?.mimeType).toBe('application/json');
    expect(String(res.contents[0]?.text)).toContain('"name": "qa"');
  });

  it('reads a blueprint by its alias', async () => {
    const res = await client.readResource({
      uri: 'agentic-os://qe/blueprints/design/test-cases',
    });
    expect(String(res.contents[0]?.text)).toContain('# Generate test cases');
  });

  it('still accepts the file/ form for the same documents', async () => {
    const res = await client.readResource({
      uri: 'agentic-os://file/agentic-os/presets/roles/qa.json',
    });
    expect(String(res.contents[0]?.text)).toContain('"name": "qa"');
  });

  it('get_document accepts an alias without change', async () => {
    const res = await client.callTool({
      name: 'get_document',
      arguments: { uri: 'agentic-os://presets/developer' },
    });
    expect((res.structuredContent as { text: string }).text)
      .toContain('"name": "developer"');
  });

  it('rejects an alias for a role that does not exist', async () => {
    const res = await client.callTool({
      name: 'get_document',
      arguments: { uri: 'agentic-os://presets/not-a-role' },
    });
    expect(res.isError).toBe(true);
  });
});
