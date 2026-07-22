import { describe, expect, it, beforeAll } from 'vitest';
import { loadContent, type Content } from '../src/content.js';

let content: Content;
beforeAll(async () => { content = await loadContent(); });

describe('content layer', () => {
  it('finds every skill across all three plugins', () => {
    const skills = content.listSkills();
    const plugins = new Set(skills.map(s => s.plugin));
    expect(plugins).toEqual(new Set(['agentic-os', 'agentic-sdlc', 'agentic-qe']));
    expect(skills.length).toBeGreaterThanOrEqual(31);
  });

  it('parses frontmatter name and description', () => {
    const init = content.listSkills().find(s => s.skill === 'agentic-init');
    expect(init?.plugin).toBe('agentic-os');
    expect(init?.description).toContain('Install the agentic-os process layer');
  });

  it('reads a document by repo-relative path', () => {
    const doc = content.readDoc('plugins/agentic-os/skills/agentic-doctor/SKILL.md');
    expect(doc?.text).toContain('install verifier');
  });

  it('returns undefined for an unknown path', () => {
    expect(content.readDoc('plugins/nope/NOPE.md')).toBeUndefined();
  });

  // readDoc is a Map.get() against keys populated solely from
  // Object.keys(index) at load time (see Content.load). There is no path
  // arithmetic here to defend against traversal — a string that was never
  // indexed simply isn't a key, whether or not it looks like a traversal
  // attempt. This test guards that only indexed paths are ever servable;
  // it says nothing about traversal-specific handling because none exists.
  it('serves only paths present in the build-time index', () => {
    expect(content.readDoc('plugins/../../etc/passwd')).toBeUndefined();
    expect(content.readDoc('../LICENSE')).toBeUndefined();
  });

  it('exposes markdown docs only for search', () => {
    expect(content.markdownDocs().every(d => d.path.endsWith('.md'))).toBe(true);
  });

  it('resolves a folded block scalar (">-") description to real text', () => {
    const qaGates = content.listSkills().find(
      s => s.plugin === 'agentic-sdlc' && s.skill === 'qa-gates',
    );
    expect(qaGates?.description).toContain(
      "Run the host project's quality gates",
    );
    expect(qaGates?.description.startsWith('>')).toBe(false);
  });

  it('resolves a literal block scalar ("|-") description to real text', () => {
    const testHeal = content.listSkills().find(
      s => s.plugin === 'agentic-sdlc' && s.skill === 'test-heal',
    );
    expect(testHeal?.description).toContain(
      "Repairs failing tests whose failure is the test's own fault",
    );
    expect(testHeal?.description.startsWith('|')).toBe(false);
  });

  it('never returns a raw block-scalar indicator or a too-short description', () => {
    const skills = content.listSkills();
    expect(skills.length).toBeGreaterThan(0);
    for (const s of skills) {
      expect(s.description.length).toBeGreaterThan(20);
      expect(s.description.startsWith('>')).toBe(false);
      expect(s.description.startsWith('|')).toBe(false);
    }
  });
});
