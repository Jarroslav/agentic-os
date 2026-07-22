import { describe, expect, it } from 'vitest';
import { readFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const MCP_ROOT = fileURLToPath(new URL('..', import.meta.url));

interface PackedFile {
  path: string;
  size: number;
  mode: number;
}

interface PackResult {
  files: PackedFile[];
}

// `npm pack --dry-run --json` shells out to `prepack` (which runs the build)
// before printing its JSON report to stdout. The build's own console output
// lands on the same stream and corrupts the JSON — so this always builds
// first (see `npm run build` in the Verify step / CI) and passes
// `--ignore-scripts` here so pack itself doesn't re-run prepack and re-emit
// build noise into the very stdout this parses.
function npmPackDryRun(): PackResult {
  const stdout = execFileSync(
    'npm',
    ['pack', '--dry-run', '--json', '--ignore-scripts'],
    { cwd: MCP_ROOT, encoding: 'utf8' },
  );
  const parsed = JSON.parse(stdout) as PackResult[];
  const result = parsed[0];
  if (result === undefined) {
    throw new Error('npm pack --dry-run --json returned an empty array');
  }
  return result;
}

describe('npm package contents', () => {
  const pack = npmPackDryRun();
  const paths = pack.files.map(f => f.path);

  it('contains a LICENSE and a NOTICE', () => {
    // Apache-2.0 requires both to travel with the distribution. They're
    // copied from the repo root into mcp/ at build time (see
    // scripts/build-content.mjs) rather than duplicated in git.
    expect(paths).toContain('LICENSE');
    expect(paths).toContain('NOTICE');
  });

  it('contains no .map files', () => {
    // Source maps point at src/, which is never part of the tarball, so a
    // shipped .map resolves to nothing for a consumer — dead weight at best,
    // a broken debugging experience at worst. tsconfig.json sets
    // sourceMap: false so tsc never emits them in the first place.
    const maps = paths.filter(p => p.endsWith('.map'));
    expect(maps).toEqual([]);
  });

  it('contains no test files and nothing under tests/', () => {
    // dist/content/** legitimately contains files that are *about* testing
    // (eval-harness fixtures, testing-pattern docs, a plugin's own
    // test-automation templates) — those are shipped product content, not
    // this package's own tests, so this check is scoped to everything
    // *outside* dist/content/. Nothing under mcp/tests/ (or any file
    // matching *.test.ts / *.test.js) should ever leak in from there.
    const nonContent = paths.filter(p => !p.startsWith('dist/content/'));
    const offenders = nonContent.filter(
      p => p.startsWith('tests/') || p.includes('/tests/') || /\.test\.(ts|js)$/.test(p),
    );
    expect(offenders).toEqual([]);
  });

  it('contains every content-index.json entry, and only those', async () => {
    // Compares against content-index.json's own key count rather than a
    // hardcoded number, so this assertion tracks reality as plugins/ grows
    // or shrinks instead of needing a manual bump every time.
    const index = JSON.parse(
      await readFile(join(MCP_ROOT, 'content-index.json'), 'utf8'),
    ) as Record<string, string>;
    const expectedRelPaths = Object.keys(index).sort();

    const prefix = 'dist/content/';
    const packedContentRelPaths = paths
      .filter(p => p.startsWith(prefix))
      .map(p => p.slice(prefix.length))
      .sort();

    expect(packedContentRelPaths).toEqual(expectedRelPaths);
  });
});
