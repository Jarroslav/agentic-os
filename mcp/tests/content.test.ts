import { describe, expect, it, beforeAll } from 'vitest';
import { execFileSync } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadContent, type Content } from '../src/content.js';
import { pathToUri, uriToPath } from '../src/resources.js';

const MCP_ROOT = fileURLToPath(new URL('..', import.meta.url));
const REPO_ROOT = join(MCP_ROOT, '..');

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

  // Pins the widened invariant this class's docstring claims: every indexed
  // path is servable. A future re-narrowing of the loader (e.g. a
  // reintroduced extension filter) would shrink docs below the index's key
  // count, and this test catches that directly at the module that owns the
  // guarantee — rather than incidentally, via a different file's
  // plan_install file-count assertion.
  it('serves every indexed path — paths().length matches the index size', async () => {
    const indexPath = join(MCP_ROOT, 'content-index.json');
    const index: Record<string, string> = JSON.parse(await readFile(indexPath, 'utf8'));
    expect(content.paths().length).toBe(Object.keys(index).length);
  });

  // With the extension filter gone, Content.load() reads every indexed file
  // as utf8 with nothing checking that it actually is text. If a binary
  // (PNG, font, archive, ...) were ever committed under plugins/, it would
  // be read at startup and served as mojibake with U+FFFD replacement
  // characters — silently, no crash, no warning. A NUL byte is the
  // reliable positive signal for binary content, regardless of extension;
  // an extension denylist is only a cheap secondary check. This is a
  // test-only guard by design (see content.ts's comment): a failure here
  // means a human must look, not that the loader should start skipping
  // files — that would quietly reintroduce the second access-control
  // mechanism this task removed.
  it('no loaded document contains a NUL byte', () => {
    const withNul = content.paths()
      .filter(p => content.readDoc(p)?.text.includes('\0'));
    expect(withNul).toEqual([]);
  });

  it('no index key uses a common binary file extension', async () => {
    const indexPath = join(MCP_ROOT, 'content-index.json');
    const index: Record<string, string> = JSON.parse(await readFile(indexPath, 'utf8'));
    const BINARY_EXT = /\.(png|jpe?g|gif|webp|bmp|ico|pdf|zip|gz|tar|woff2?|ttf|otf|eot|mp3|mp4|mov|wasm|exe|dll|so|class|jar)$/i;
    const suspicious = Object.keys(index).filter(p => BINARY_EXT.test(p));
    expect(suspicious).toEqual([]);
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

  // Regression guard for the class of bug where build-content.mjs's walk()
  // read the working tree instead of git's index: an untracked local file
  // (a .pytest_cache, .DS_Store, .venv, …) could get baked into the
  // committed content-index.json, shipping local debris and failing
  // check:drift on every fresh clone. Every indexed key must be a
  // git-tracked path under plugins/ — this is what makes that class of bug
  // impossible to reintroduce, independent of how the index was built.
  it('indexes only git-tracked paths', async () => {
    const indexPath = join(MCP_ROOT, 'content-index.json');
    const index: Record<string, string> = JSON.parse(await readFile(indexPath, 'utf8'));

    const out = execFileSync('git', ['ls-files', '-z', 'plugins'], {
      cwd: REPO_ROOT,
      encoding: 'utf8',
    });
    const tracked = new Set(out.split('\0').filter(rel => rel.length > 0));

    const untracked = Object.keys(index).filter(path => !tracked.has(path));
    expect(untracked).toEqual([]);
  });

  // The resource template (`agentic-os://file/{+path}`) round-trips a path
  // through `URL`, while get_document's URI parsing does not — they only
  // agree because no plugin file currently has a space, '#', or '%' in its
  // name. Pinning the character set cheaply guards that unstated invariant.
  it('every index key matches the safe path character set', async () => {
    const indexPath = join(MCP_ROOT, 'content-index.json');
    const index: Record<string, string> = JSON.parse(await readFile(indexPath, 'utf8'));
    const SAFE_PATH = /^[A-Za-z0-9._/-]+$/;

    const unsafe = Object.keys(index).filter(path => !SAFE_PATH.test(path));
    expect(unsafe).toEqual([]);
  });

  it('every index key round-trips through pathToUri and uriToPath', async () => {
    const indexPath = join(MCP_ROOT, 'content-index.json');
    const index: Record<string, string> = JSON.parse(await readFile(indexPath, 'utf8'));

    const mismatches: string[] = [];
    for (const path of Object.keys(index)) {
      const uri = pathToUri(path);
      const reconstructed = uriToPath(uri);
      if (reconstructed !== path) {
        mismatches.push(`Path: ${path} → URI: ${uri} → Reconstructed: ${reconstructed}`);
      }
    }
    expect(mismatches).toEqual([]);
  });

  it('emits canonical forms for presets and blueprints, not file/ form', async () => {
    // Test preset canonical form
    const presetPath = 'plugins/agentic-os/presets/roles/qa.json';
    const presetUri = pathToUri(presetPath);
    expect(presetUri).toBe('agentic-os://presets/qa');

    // Test blueprint canonical form
    const blueprintPath = 'plugins/agentic-qe/skills/qe-blueprints/references/catalog/analyze/change-impact-scoping.md';
    const blueprintUri = pathToUri(blueprintPath);
    expect(blueprintUri).toBe('agentic-os://qe/blueprints/analyze/change-impact-scoping');

    // Test that pathToUri does not emit file/ form for presets or blueprints
    expect(presetUri).not.toContain('file/');
    expect(blueprintUri).not.toContain('file/');
  });
});
