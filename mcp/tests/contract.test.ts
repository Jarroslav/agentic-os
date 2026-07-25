import { describe, expect, it, beforeAll, afterAll } from 'vitest';
import { readFile, mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
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

describe('every advertised tool', () => {
  // The stated global constraint is that *every* tool — not just the ones
  // someone remembered to assert on individually — is read-only, carries an
  // output schema, and follows the naming conventions the namespace prefix
  // and MCP host UIs depend on. Replaces the two ad hoc per-tool
  // readOnlyHint/outputSchema assertions that used to live in the
  // search_methodology and list_presets describe blocks below: a new tool
  // registered without the annotation now fails here regardless of whether
  // anyone thought to write a tool-specific assertion for it.
  it('stays within the documented tool cap', async () => {
    const { tools } = await client.listTools();
    expect(tools.length).toBeGreaterThan(0);
    expect(tools.length).toBeLessThanOrEqual(8); // see mcp/README.md Tools section for cap rationale
  });

  it('is advertised read-only with an output schema', async () => {
    const { tools } = await client.listTools();
    for (const t of tools) {
      expect(t.annotations?.readOnlyHint).toBe(true);
      expect(t.outputSchema).toBeDefined();
    }
  });

  it('has a valid, host-safe name', async () => {
    const { tools } = await client.listTools();
    for (const t of tools) {
      expect(t.name).toMatch(/^[a-z][a-z0-9_]*$/);
      expect(('agentic-os:' + t.name).length).toBeLessThan(60);
    }
  });
});

describe('search_methodology', () => {
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

describe('list_qe_blueprints', () => {
  it('returns all 28 blueprints across 6 stages', async () => {
    const res = await client.callTool({ name: 'list_qe_blueprints', arguments: {} });
    const { blueprints } = res.structuredContent as {
      blueprints: Array<{ id: string; stage: string; title: string; summary: string; uri: string }>;
    };
    expect(blueprints).toHaveLength(28);
    expect(new Set(blueprints.map(b => b.stage))).toEqual(
      new Set(['analyze', 'build', 'design', 'execute', 'operate', 'report']),
    );
  });

  it('filters by stage', async () => {
    const res = await client.callTool({
      name: 'list_qe_blueprints', arguments: { stage: 'design' },
    });
    const { blueprints } = res.structuredContent as { blueprints: Array<{ stage: string }> };
    expect(blueprints).toHaveLength(4);
    expect(blueprints.every(b => b.stage === 'design')).toBe(true);
  });

  it('gives every blueprint a real title, a summary, and a resolvable uri', async () => {
    const res = await client.callTool({ name: 'list_qe_blueprints', arguments: {} });
    const { blueprints } = res.structuredContent as {
      blueprints: Array<{ title: string; summary: string; uri: string }>;
    };
    for (const b of blueprints) {
      expect(b.title.startsWith('#')).toBe(false);   // heading marker stripped
      expect(b.title.length).toBeGreaterThan(3);
      expect(b.summary.length).toBeGreaterThan(20);
    }
    const doc = await client.readResource({ uri: blueprints[0]!.uri });
    expect(String(doc.contents[0]?.text).length).toBeGreaterThan(100);
  });

  it('rejects an unknown stage at the schema', async () => {
    const res = await client.callTool({
      name: 'list_qe_blueprints', arguments: { stage: 'nonsense' },
    });
    expect(res.isError).toBe(true);
  });

  it('derives its stage enum from the content index, not a hardcoded tuple', async () => {
    // Mirrors list_presets's analogous index-derived guard above: computes
    // the expected stage set directly from content-index.json (the same
    // authority list_qe_blueprints.ts itself reads at registration time) and
    // checks both that the tool's unfiltered output matches it exactly and
    // that every one of those stages is schema-valid to filter by. A stage
    // directory added under
    // plugins/agentic-qe/skills/qe-blueprints/references/catalog/ without
    // regenerating the schema from the index would fail the second half of
    // this test even if it passed the first (the tool would emit blueprints
    // for the new stage but reject it as a filter).
    const index: Record<string, string> = JSON.parse(
      await readFile(join(MCP_ROOT, 'content-index.json'), 'utf8'),
    );
    const CATALOG_PATH =
      /^plugins\/agentic-qe\/skills\/qe-blueprints\/references\/catalog\/([^/]+)\/[^/]+\.md$/;
    const expectedStages = new Set(
      Object.keys(index)
        .map(k => CATALOG_PATH.exec(k)?.[1])
        .filter((s): s is string => s !== undefined),
    );
    expect(expectedStages.size).toBeGreaterThan(0);

    const res = await client.callTool({ name: 'list_qe_blueprints', arguments: {} });
    const { blueprints } = res.structuredContent as { blueprints: Array<{ stage: string }> };
    expect(new Set(blueprints.map(b => b.stage))).toEqual(expectedStages);

    for (const stage of expectedStages) {
      const filtered = await client.callTool({
        name: 'list_qe_blueprints', arguments: { stage },
      });
      expect(filtered.isError).toBeFalsy();
    }
  });

  it('never emits an unpaired surrogate in any summary', async () => {
    // This currently passes trivially — no blueprint in the corpus contains
    // an astral character today — but summarize() caps by code point via
    // truncateCodePoints() (mcp/src/text.ts), the same helper get_document.ts
    // uses, precisely so this stays true if a future blueprint's first
    // paragraph both contains an astral character and crosses the 300-cap
    // boundary.
    const UNPAIRED_SURROGATE =
      /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/;
    const res = await client.callTool({ name: 'list_qe_blueprints', arguments: {} });
    const { blueprints } = res.structuredContent as { blueprints: Array<{ summary: string }> };
    expect(blueprints.length).toBeGreaterThan(0);
    expect(blueprints.every(b => !UNPAIRED_SURROGATE.test(b.summary))).toBe(true);
  });
});

describe('list_sdlc_phases', () => {
  it('returns all 13 phases in order', async () => {
    const res = await client.callTool({ name: 'list_sdlc_phases', arguments: {} });
    const { phases } = res.structuredContent as {
      phases: Array<{ number: number; name: string; skippable: string; gates: string[] }>;
    };
    expect(phases).toHaveLength(13);
    expect(phases[0]?.number).toBe(0);
    expect(phases[12]?.number).toBe(12);
    expect(phases.map(p => p.number)).toEqual([...Array(13).keys()]);
  });

  it('extracts gate names from the table', async () => {
    const res = await client.callTool({ name: 'list_sdlc_phases', arguments: {} });
    const { phases } = res.structuredContent as {
      phases: Array<{ number: number; gates: string[] }>;
    };
    expect(phases.find(p => p.number === 1)?.gates)
      .toEqual(expect.arrayContaining(['requirements.ambiguous']));
    expect(phases.find(p => p.number === 5)?.gates).toEqual(['plan.approved']);
    expect(phases.find(p => p.number === 0)?.gates).toEqual([]);  // em dash -> none
  });

  it('names the phases', async () => {
    const res = await client.callTool({ name: 'list_sdlc_phases', arguments: {} });
    const { phases } = res.structuredContent as {
      phases: Array<{ number: number; name: string }>;
    };
    expect(phases.find(p => p.number === 1)?.name).toContain('Requirements');
    expect(phases.every(p => p.name.length > 2)).toBe(true);
  });

  it('points at the document it parsed', async () => {
    const res = await client.callTool({ name: 'list_sdlc_phases', arguments: {} });
    const { source_uri } = res.structuredContent as { source_uri: string };
    expect(source_uri).toBe('agentic-os://skills/agentic-sdlc/sdlc-pipeline');
    const doc = await client.readResource({ uri: source_uri });
    expect(String(doc.contents[0]?.text)).toContain('## Phase map');
  });
});

describe('plan_install', () => {
  it('plans a single role', async () => {
    const res = await client.callTool({
      name: 'plan_install', arguments: { roles: ['developer'] },
    });
    const out = res.structuredContent as {
      files: Array<{ template_id: string; source_uri: string; owner: string }>;
      hitl_default: string;
    };
    expect(out.files.length).toBeGreaterThan(20);
    expect(out.hitl_default).toBe('gated-autonomous');
    expect(out.files.every(f => f.source_uri.startsWith('agentic-os://'))).toBe(true);
    expect(out.files.every(f => f.owner === 'managed')).toBe(true);
  });

  it('composes roles additively', async () => {
    const dev = await client.callTool({ name: 'plan_install', arguments: { roles: ['developer'] } });
    const qa = await client.callTool({ name: 'plan_install', arguments: { roles: ['qa'] } });
    const both = await client.callTool({ name: 'plan_install', arguments: { roles: ['developer', 'qa'] } });
    const ids = (r: unknown) => new Set(
      (r as { files: Array<{ template_id: string }> }).files.map(f => f.template_id));
    const union = new Set([...ids(dev.structuredContent), ...ids(qa.structuredContent)]);
    expect(ids(both.structuredContent)).toEqual(union);
  });

  it('applies strictest-HITL-wins', async () => {
    const res = await client.callTool({
      name: 'plan_install', arguments: { roles: ['developer', 'qa'] },
    });
    // qa is strict, developer is gated-autonomous -> strict wins
    expect((res.structuredContent as { hitl_default: string }).hitl_default).toBe('strict');
  });

  it('unions orchestration styles rather than picking a winner', async () => {
    const res = await client.callTool({
      name: 'plan_install', arguments: { roles: ['developer', 'qa'] },
    });
    const out = res.structuredContent as
      { orchestration_installed: string[]; orchestration_default: string };
    // developer is pipeline, qa is dispatcher — a dev+qa team installs BOTH
    expect(new Set(out.orchestration_installed)).toEqual(new Set(['pipeline', 'dispatcher']));
    // and strict HITL (from qa) forces the dispatcher default
    expect(out.orchestration_default).toBe('dispatcher');
  });

  it('takes the default orchestration from the first listed role when HITL is not strict', async () => {
    const res = await client.callTool({
      name: 'plan_install', arguments: { roles: ['developer', 'devops'] },
    });
    const out = res.structuredContent as
      { orchestration_default: string; hitl_default: string };
    expect(out.hitl_default).toBe('gated-autonomous');   // neither is strict
    expect(out.orchestration_default).toBe('pipeline');  // developer listed first
  });

  it('every planned file resolves to a readable document', async () => {
    const res = await client.callTool({ name: 'plan_install', arguments: { roles: ['qa'] } });
    const { files } = res.structuredContent as { files: Array<{ source_uri: string }> };
    for (const f of files.slice(0, 5)) {
      const doc = await client.readResource({ uri: f.source_uri });
      expect(String(doc.contents[0]?.text).length).toBeGreaterThan(0);
    }
  });

  it('rejects an unknown role as a recoverable error', async () => {
    const res = await client.callTool({
      name: 'plan_install', arguments: { roles: ['not-a-role'] },
    });
    expect(res.isError).toBe(true);
    expect(String((res.content as Array<{ text: string }>)[0]?.text)).toContain('list_presets');
  });
});

describe('run_doctor', () => {
  // Temp dirs created directly with node:fs/promises are fine here — only
  // mcp/src/** is banned from touching the filesystem (see
  // readonly.test.ts); this test file is exempt, same as target.test.ts and
  // doctor.test.ts.
  const roots: string[] = [];
  afterAll(async () => {
    while (roots.length > 0) {
      const r = roots.pop();
      if (r !== undefined) await rm(r, { recursive: true, force: true });
    }
  });
  async function makeRoot(): Promise<string> {
    const root = await mkdtemp(join(tmpdir(), 'run-doctor-target-'));
    roots.push(root);
    return root;
  }

  it('reports a non-existent target_path as a recoverable error, not a thrown/rejected call', async () => {
    const res = await client.callTool({
      name: 'run_doctor',
      arguments: { target_path: join(tmpdir(), 'run-doctor-does-not-exist-xyz') },
    });
    expect(res.isError).toBe(true);
    expect(String((res.content as Array<{ text: string }>)[0]?.text).length).toBeGreaterThan(0);
  });

  it('reports installed: false with a single not-installed check when the journal is missing', async () => {
    const root = await makeRoot();
    const res = await client.callTool({
      name: 'run_doctor',
      arguments: { target_path: root },
    });
    const out = res.structuredContent as {
      installed: boolean;
      checks: Array<{ key: string; passed: boolean }>;
      verdict: string;
    };
    expect(out.installed).toBe(false);
    expect(out.checks).toHaveLength(1);
    expect(out.checks[0]?.key).toBe('not-installed');
    expect(out.checks[0]?.passed).toBe(false);
    expect(out.verdict).toBe('failed');
  });

  it('host_must_run has exactly 3 entries, each with a non-empty commands array and a non-empty why, on an installed repo — and verdict is never "passed" while it is non-empty (the integrity rule)', async () => {
    // "Installed" only requires .agentic/agentic-os/install.json to exist
    // and parse as JSON — runNativeChecks() doesn't require any journaled
    // files to be present on disk for the not-installed sentinel to be
    // skipped (see doctor.ts / doctor.test.ts). A bare, empty journal is
    // therefore enough to exercise the installed path without needing a
    // full fixture install.
    const root = await makeRoot();
    await mkdir(join(root, '.agentic', 'agentic-os'), { recursive: true });
    await writeFile(
      join(root, '.agentic', 'agentic-os', 'install.json'),
      JSON.stringify({ agentic_os_version: '0.1.0', files: {} }, null, 2),
      'utf8',
    );

    const res = await client.callTool({
      name: 'run_doctor',
      arguments: { target_path: root },
    });
    const out = res.structuredContent as {
      installed: boolean;
      verdict: string;
      host_must_run: Array<{ key: string; why: string; commands: string[] }>;
    };
    expect(out.installed).toBe(true);
    expect(out.host_must_run).toHaveLength(3);
    expect(out.host_must_run.map((h) => h.key).sort()).toEqual(
      ['dry_runs', 'hitl_smoke', 'py_compile'],
    );
    for (const entry of out.host_must_run) {
      expect(entry.commands.length).toBeGreaterThan(0);
      expect(entry.commands.every((c) => c.length > 0)).toBe(true);
      expect(entry.why.length).toBeGreaterThan(0);
    }

    // The integrity rule itself: host_must_run is non-empty here, so
    // verdict must never be 'passed' — regardless of what the native
    // checks reported.
    expect(out.host_must_run.length).toBeGreaterThan(0);
    expect(out.verdict).not.toBe('passed');
  });

  it('is advertised read-only (covered generically above; confirms the suite stays green with a 7th tool)', async () => {
    const { tools } = await client.listTools();
    const tool = tools.find((t) => t.name === 'run_doctor');
    expect(tool).toBeDefined();
    expect(tool?.annotations?.readOnlyHint).toBe(true);
  });
});
