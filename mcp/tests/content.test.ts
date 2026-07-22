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

  it('refuses paths outside plugins/ even with traversal', () => {
    expect(content.readDoc('plugins/../../etc/passwd')).toBeUndefined();
    expect(content.readDoc('../LICENSE')).toBeUndefined();
  });

  it('exposes markdown docs only for search', () => {
    expect(content.markdownDocs().every(d => d.path.endsWith('.md'))).toBe(true);
  });
});
