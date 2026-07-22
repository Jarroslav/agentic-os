import { describe, expect, it, beforeAll, afterAll } from 'vitest';
import { mkdtemp, writeFile, mkdir, chmod, symlink, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { tmpdir } from 'node:os';
import { join, sep } from 'node:path';
import { Target } from '../src/target.js';

// This suite builds real, disposable temp trees with node:fs/promises
// directly (tests may write; only mcp/src/** may not — see the read-only
// scan in readonly.test.ts, which does not walk mcp/tests/).

let root: string;
let outside: string;
let canCreateSymlinks = true;

beforeAll(async () => {
  root = await mkdtemp(join(tmpdir(), 'target-repo-'));
  outside = await mkdtemp(join(tmpdir(), 'target-outside-'));

  await writeFile(join(root, 'README.md'), 'hello world\n', 'utf8');
  await mkdir(join(root, 'nested', 'dir'), { recursive: true });
  await writeFile(join(root, 'nested', 'dir', 'file.txt'), 'nested contents\n', 'utf8');

  await writeFile(join(root, 'script.sh'), '#!/bin/sh\necho hi\n', 'utf8');
  await chmod(join(root, 'script.sh'), 0o755);
  await writeFile(join(root, 'plain.sh'), '#!/bin/sh\necho hi\n', 'utf8');
  await chmod(join(root, 'plain.sh'), 0o644);

  await writeFile(join(outside, 'secret.txt'), 'top secret\n', 'utf8');

  try {
    await symlink(join(outside, 'secret.txt'), join(root, 'escape-link.txt'));
  } catch {
    canCreateSymlinks = false;
  }
});

afterAll(async () => {
  await rm(root, { recursive: true, force: true });
  await rm(outside, { recursive: true, force: true });
});

describe('Target.open', () => {
  it('resolves an existing directory root', async () => {
    const target = await Target.open(root);
    expect(target).toBeInstanceOf(Target);
  });

  it('rejects a non-existent root', async () => {
    const missing = join(root, 'does-not-exist');
    await expect(Target.open(missing)).rejects.toBeTruthy();
  });

  it('rejects a root that is a file, not a directory', async () => {
    const filePath = join(root, 'README.md');
    await expect(Target.open(filePath)).rejects.toBeTruthy();
  });
});

describe('Target read/sha256/exists/isExecutable', () => {
  let target: Target;
  beforeAll(async () => {
    target = await Target.open(root);
  });

  it('reads a file that exists', async () => {
    expect(await target.read('README.md')).toBe('hello world\n');
  });

  it('reads a nested file that exists', async () => {
    expect(await target.read('nested/dir/file.txt')).toBe('nested contents\n');
  });

  it('computes the correct sha256 against an independently computed value', async () => {
    const expected = createHash('sha256').update('hello world\n', 'utf8').digest('hex');
    expect(await target.sha256('README.md')).toBe(expected);
    expect(expected).toMatch(/^[0-9a-f]{64}$/);
  });

  it('returns undefined for a missing file', async () => {
    expect(await target.read('nope.md')).toBeUndefined();
    expect(await target.sha256('nope.md')).toBeUndefined();
    expect(await target.exists('nope.md')).toBe(false);
  });

  it('returns true/undefined appropriately for a file that exists', async () => {
    expect(await target.exists('README.md')).toBe(true);
  });

  it('returns undefined for a ../ escape out of the root', async () => {
    expect(await target.read('../etc/passwd')).toBeUndefined();
    expect(await target.read('../../etc/passwd')).toBeUndefined();
    expect(await target.exists('../etc/passwd')).toBe(false);
  });

  it('returns undefined for an absolute rel path', async () => {
    expect(await target.read('/etc/passwd')).toBeUndefined();
    expect(await target.read(join(outside, 'secret.txt'))).toBeUndefined();
    expect(await target.exists('/etc/passwd')).toBe(false);
  });

  it('still resolves a rel path with .. segments that stay inside the root', async () => {
    expect(await target.read('nested/dir/../../README.md')).toBe('hello world\n');
    expect(await target.read('nested/../nested/dir/file.txt')).toBe('nested contents\n');
  });

  it('returns undefined for an empty rel or "."', async () => {
    // Neither is a readable file (root itself is a directory), so both
    // must resolve to "not servable" rather than throwing.
    expect(await target.read('')).toBeUndefined();
    expect(await target.read('.')).toBeUndefined();
  });

  it('returns undefined for a directory passed as rel', async () => {
    expect(await target.read('nested')).toBeUndefined();
    expect(await target.read('nested/dir')).toBeUndefined();
  });

  it('does not leak the sibling-prefix case (/tmp/repo vs /tmp/repo-evil)', async () => {
    // root looks like <tmpdir>/target-repo-XXXXXX; construct a sibling
    // whose name has root's name as a literal prefix, and confirm that
    // reaching it via a rel path is rejected rather than accepted by a
    // naive startsWith(root) check.
    const evilSibling = `${root}-evil`;
    await mkdir(evilSibling, { recursive: true });
    await writeFile(join(evilSibling, 'leaked.txt'), 'should never be read\n', 'utf8');
    try {
      // The only way target.read ever sees this path is via a rel value;
      // there is no legitimate rel that maps outside root at all, but this
      // guards the comparison itself is not a bare startsWith(root).
      const relIntoSibling = `..${sep}${evilSibling.split(sep).pop()}${sep}leaked.txt`;
      expect(await target.read(relIntoSibling)).toBeUndefined();
    } finally {
      await rm(evilSibling, { recursive: true, force: true });
    }
  });

  it('isExecutable is true for a chmod +x file, false for a plain file', async () => {
    expect(await target.isExecutable('script.sh')).toBe(true);
    expect(await target.isExecutable('plain.sh')).toBe(false);
  });

  it('isExecutable is false for a missing file', async () => {
    expect(await target.isExecutable('nope.sh')).toBe(false);
  });

  it('returns undefined for a linked path inside the root pointing at a file outside it', async () => {
    if (!canCreateSymlinks) {
      console.warn('Skipping link-escape test: platform cannot create links');
      return;
    }
    // This is the case that proves realpath-based containment is actually
    // used: the unresolved path "escape-link.txt" is textually inside root,
    // so a containment check that compares the unresolved resolved-join
    // path against root (e.g. startsWith on the un-realpath'd path) would
    // wrongly accept it. Only resolving the final target and re-checking
    // containment catches this.
    expect(await target.read('escape-link.txt')).toBeUndefined();
    expect(await target.sha256('escape-link.txt')).toBeUndefined();
    expect(await target.exists('escape-link.txt')).toBe(false);
  });

  it('returns undefined for a broken link', async () => {
    if (!canCreateSymlinks) {
      console.warn('Skipping broken-link test: platform cannot create links');
      return;
    }
    const linkPath = join(root, 'broken-link.txt');
    await symlink(join(root, 'this-target-never-exists.txt'), linkPath);
    try {
      expect(await target.read('broken-link.txt')).toBeUndefined();
      expect(await target.exists('broken-link.txt')).toBe(false);
    } finally {
      await rm(linkPath, { force: true });
    }
  });
});
