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

describe('server.json / manifest.json / package.json agreement', () => {
  // The MCP Registry's npm ownership check fetches the *published* npm
  // package and requires its `mcpName` to equal server.json's `name`. The
  // .mcpb bundle's manifest ships alongside the same build. All three files
  // describe one release and must not drift relative to each other — a
  // human will not notice a version mismatch until publish fails.

  async function readJson(relPath: string): Promise<Record<string, unknown>> {
    return JSON.parse(await readFile(join(MCP_ROOT, relPath), 'utf8')) as Record<
      string,
      unknown
    >;
  }

  it('server.json name matches package.json mcpName', async () => {
    const pkg = await readJson('package.json');
    const server = await readJson('server.json');
    expect(server.name).toBe(pkg.mcpName);
  });

  it('server.json version matches package.json version', async () => {
    const pkg = await readJson('package.json');
    const server = await readJson('server.json');
    expect(server.version).toBe(pkg.version);
  });

  it('server.json packages[0] identifier and version match package.json', async () => {
    const pkg = await readJson('package.json');
    const server = await readJson('server.json');
    const packages = server.packages as Array<Record<string, unknown>>;
    const firstPackage = packages[0];
    if (firstPackage === undefined) {
      throw new Error('server.json packages[] is empty');
    }
    expect(firstPackage.identifier).toBe(pkg.name);
    expect(firstPackage.version).toBe(pkg.version);
  });

  it('manifest.json version matches package.json version', async () => {
    const pkg = await readJson('package.json');
    const manifest = await readJson('manifest.json');
    expect(manifest.version).toBe(pkg.version);
  });

  it('manifest.json server paths point at a file the build actually produces', async () => {
    const manifest = await readJson('manifest.json');
    const server = manifest.server as Record<string, unknown>;
    const mcpConfig = server.mcp_config as Record<string, unknown>;
    const args = mcpConfig.args as string[];
    const firstArg = args[0];
    if (firstArg === undefined) {
      throw new Error('manifest.json server.mcp_config.args is empty');
    }

    // entry_point is relative to the bundle root; the mcp_config arg is
    // `${__dirname}/<path>` which resolves to the same bundle-relative path
    // at run time. Both must resolve to a file the build emits.
    const entryPoint = server.entry_point as string;
    const argPath = firstArg.replace('${__dirname}/', '');
    expect(argPath).toBe(entryPoint);

    const { existsSync } = await import('node:fs');
    expect(existsSync(join(MCP_ROOT, entryPoint))).toBe(true);
  });
});
