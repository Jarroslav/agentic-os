import { describe, expect, it, beforeAll } from 'vitest';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { resolveTemplateId } from '../src/templates.js';

const MCP_ROOT = fileURLToPath(new URL('..', import.meta.url));
let indexPaths: string[];
let templateIds: string[];

beforeAll(async () => {
  const index = JSON.parse(
    await readFile(join(MCP_ROOT, 'content-index.json'), 'utf8'),
  ) as Record<string, string>;
  indexPaths = Object.keys(index);

  const ids = new Set<string>();
  for (const p of indexPaths.filter(p => /presets\/roles\/[^/]+\.json$/.test(p))) {
    const preset = JSON.parse(
      await readFile(join(MCP_ROOT, 'dist', 'content', p), 'utf8'),
    ) as { templates?: string[] };
    for (const t of preset.templates ?? []) ids.add(t);
  }
  templateIds = [...ids].sort();
});

describe('resolveTemplateId', () => {
  it('resolves EVERY template id referenced by EVERY preset', () => {
    const unresolved = templateIds.filter(id => !resolveTemplateId(id, indexPaths));
    expect(unresolved).toEqual([]);
    expect(templateIds.length).toBeGreaterThanOrEqual(46);
  });

  it('resolves to paths that actually exist in the index', () => {
    const bad = templateIds
      .map(id => [id, resolveTemplateId(id, indexPaths)] as const)
      .filter(([, p]) => p && !indexPaths.includes(p));
    expect(bad).toEqual([]);
  });

  it('handles the two documented exceptions', () => {
    expect(resolveTemplateId('governance/claude-section', indexPaths))
      .toBe('plugins/agentic-os/templates/governance/CLAUDE.section.md.tmpl');
    expect(resolveTemplateId('hooks/session-bootstrap', indexPaths))
      .toBe('plugins/agentic-os/templates/hooks/claude/session_start_bootstrap.py.tmpl');
  });

  it('resolves case-differing ids — these fail exact-case matching', () => {
    // governance/agents -> AGENTS.md.tmpl, governance/patterns -> PATTERNS.md.tmpl.
    // A macOS filesystem probe hides this; the index is exact-case, as Linux CI is.
    expect(resolveTemplateId('governance/agents', indexPaths))
      .toBe('plugins/agentic-os/templates/governance/AGENTS.md.tmpl');
    expect(resolveTemplateId('governance/patterns', indexPaths))
      .toBe('plugins/agentic-os/templates/governance/PATTERNS.md.tmpl');
  });

  it('returns undefined for an unknown id rather than guessing', () => {
    expect(resolveTemplateId('hooks/not-a-real-hook', indexPaths)).toBeUndefined();
    expect(resolveTemplateId('nonsense', indexPaths)).toBeUndefined();
  });
});
