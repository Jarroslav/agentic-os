import { describe, expect, it, beforeAll, afterAll } from 'vitest';
import { execFileSync } from 'node:child_process';
import { mkdtemp, mkdir, readdir, readFile, writeFile, rm, cp } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { EXPECTED_WIRING } from '../src/doctor.js';

const MCP_ROOT = fileURLToPath(new URL('..', import.meta.url));
const REPO_ROOT = join(MCP_ROOT, '..');
const PLUGIN_ROOT = join(REPO_ROOT, 'plugins', 'agentic-os');
const MAKE_FRESH = join(REPO_ROOT, 'tests', 'fixtures', 'make-fresh.sh');
const REFINSTALL = join(REPO_ROOT, 'tests', 'lib', 'refinstall.py');
const SKILL_MD = join(REPO_ROOT, 'plugins', 'agentic-os', 'skills', 'agentic-doctor', 'SKILL.md');

type RunDoctorOutput = {
  installed: boolean;
  checks: Array<{ key: string; passed: boolean; detail: string }>;
  host_must_run: Array<{ key: string; why: string; commands: string[] }>;
  failures: string[];
  verdict: 'passed' | 'failed' | 'incomplete';
};

function findCheck(out: RunDoctorOutput, key: string): { key: string; passed: boolean; detail: string } {
  const found = out.checks.find((c) => c.key === key);
  if (found === undefined) throw new Error(`no check result with key "${key}" (have: ${out.checks.map((c) => c.key).join(', ')})`);
  return found;
}

// ---------------------------------------------------------------------------
// Part B — pin the shipped host_must_run command text to the live SKILL.md.
//
// This does not need a refinstall-built fixture or python3 at all:
// buildHostMustRun() in mcp/src/tools/run_doctor.ts is static, independent of
// target_path, so it's exercised the same way against any readable directory
// — REPO_ROOT itself, same as readonly.test.ts's TOOL_ARGS choice. This suite
// therefore always runs, even in an environment where Part A below has to
// skip for lacking python3.
// ---------------------------------------------------------------------------
describe('run_doctor host_must_run is pinned to the live SKILL.md', () => {
  let client: Client;
  let bareInstalledRoot: string;

  beforeAll(async () => {
    client = new Client({ name: 'skill-pin-test', version: '0.0.0' });
    await client.connect(new StdioClientTransport({
      command: 'node', args: ['dist/index.js'], cwd: MCP_ROOT,
    }));

    // buildHostMustRun() doesn't depend on target_path, but run_doctor only
    // returns it once the journal marks the target "installed" — a bare,
    // empty journal is enough for that (see contract.test.ts's identical
    // technique), with no need for python3 or a full refinstall build.
    bareInstalledRoot = await mkdtemp(join(tmpdir(), 'skill-pin-target-'));
    await mkdir(join(bareInstalledRoot, '.agentic', 'agentic-os'), { recursive: true });
    await writeFile(
      join(bareInstalledRoot, '.agentic', 'agentic-os', 'install.json'),
      JSON.stringify({ agentic_os_version: '0.1.0', files: {} }, null, 2),
      'utf8',
    );
  }, 30_000);

  afterAll(async () => {
    await client.close();
    await rm(bareInstalledRoot, { recursive: true, force: true });
  });

  it("Check 2's load-bearing fragments (spec_from_file_location, module_from_spec, except BaseException) appear verbatim in both the shipped py_compile commands and the current SKILL.md — a future edit that swaps except BaseException for except Exception, or otherwise drifts, must fail this loudly", async () => {
    const skillText = await readFile(SKILL_MD, 'utf8');

    const res = await client.callTool({ name: 'run_doctor', arguments: { target_path: bareInstalledRoot } });
    const out = res.structuredContent as RunDoctorOutput;
    const pyCompile = out.host_must_run.find((h) => h.key === 'py_compile');
    expect(pyCompile).toBeDefined();
    const shippedText = pyCompile?.commands.join('\n') ?? '';

    // The three fragments that make Check 2b meaningful: without them, a
    // hook that raises SystemExit at import time (sys.exit() at module
    // scope) would silently read as a pass instead of a failure.
    const loadBearingFragments = ['spec_from_file_location', 'module_from_spec', 'except BaseException'];
    for (const fragment of loadBearingFragments) {
      expect(shippedText).toContain(fragment);
      expect(skillText).toContain(fragment);
    }
  });
});

// ---------------------------------------------------------------------------
// Part C — pin doctor.ts's hand-maintained EXPECTED_WIRING to the live
// settings-fragment template, by set-equality of (event, hook-file) pairs.
//
// This is the fix for IMPORTANT 1: nothing previously failed if the fragment
// gained (or lost) an entry that EXPECTED_WIRING didn't track — exactly how
// prompt_scan_guard.py went missing from the SKILL.md Check 5 parenthetical
// earlier in this phase (see doctor.ts's comment atop EXPECTED_WIRING, and
// ROADMAP.md's "Known issue" entry). Like Part B above, this reads the
// fragment through the bundle reader (Content, via the file resource
// template) rather than building a refinstall fixture, so it always runs —
// no python3 dependency.
// ---------------------------------------------------------------------------
describe('doctor.ts EXPECTED_WIRING is pinned to the live settings fragment (set-equality)', () => {
  let client: Client;

  beforeAll(async () => {
    client = new Client({ name: 'wiring-pin-test', version: '0.0.0' });
    await client.connect(new StdioClientTransport({
      command: 'node', args: ['dist/index.js'], cwd: MCP_ROOT,
    }));
  }, 30_000);

  afterAll(async () => {
    await client.close();
  });

  /** Extracts every (event, hook-file) pair actually wired in a parsed
   *  settings-fragment.json.tmpl-shaped object, one entry per distinct pair
   *  — a hook wired under two matchers within the same event (e.g.
   *  guarded_write_paths.py under both the Write and Edit PreToolUse
   *  matchers) collapses to a single pair, matching EXPECTED_WIRING's own
   *  one-entry-per-(event,file) shape rather than one-per-matcher-group. */
  function extractWiringPairs(fragment: {
    hooks?: Record<string, Array<{ hooks?: Array<{ command?: string }> }>>;
  }): Set<string> {
    const pairs = new Set<string>();
    for (const [event, groups] of Object.entries(fragment.hooks ?? {})) {
      for (const group of groups) {
        for (const h of group.hooks ?? []) {
          const match = /\.claude\/hooks\/([A-Za-z0-9_.-]+\.py)/.exec(h.command ?? '');
          const file = match?.[1];
          if (file !== undefined) pairs.add(`${event}::${file}`);
        }
      }
    }
    return pairs;
  }

  it('EXPECTED_WIRING\'s (event, file) pairs exactly match the fragment\'s — no entry missing, none extra', async () => {
    const res = await client.readResource({
      uri: 'agentic-os://file/agentic-os/templates/hooks/settings-fragment.json.tmpl',
    });
    const fragmentText = String(res.contents[0]?.text ?? '');
    expect(fragmentText.length).toBeGreaterThan(0);
    const fragment = JSON.parse(fragmentText) as Parameters<typeof extractWiringPairs>[0];

    const fromFragment = extractWiringPairs(fragment);
    const fromExpected = new Set(EXPECTED_WIRING.map((w) => `${w.event}::${w.file}`));

    const missingFromExpected = [...fromFragment].filter((p) => !fromExpected.has(p)).sort();
    const extraInExpected = [...fromExpected].filter((p) => !fromFragment.has(p)).sort();

    expect(missingFromExpected, 'pairs the fragment wires that EXPECTED_WIRING does not track').toEqual([]);
    expect(extraInExpected, 'pairs EXPECTED_WIRING tracks that the fragment does not actually wire').toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Part A — fixture parity: run_doctor against a real, refinstall-built repo.
//
// Skip the whole suite (rather than fail it) when python3 is unavailable —
// tests/lib/refinstall.py needs it to build the fixture. CI's `mcp` job runs
// on ubuntu with python3 present, so this describe.skipIf should never
// actually trip there; it only protects a local run on a machine without
// python3 on PATH.
// ---------------------------------------------------------------------------
function hasPython3(): boolean {
  try {
    execFileSync('python3', ['--version'], { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

const PYTHON3_AVAILABLE = hasPython3();
if (!PYTHON3_AVAILABLE) {
  // eslint-disable-next-line no-console
  console.warn(
    '[fixture.test.ts] Skipping fixture-parity suite: python3 is not on PATH. ' +
    'tests/lib/refinstall.py needs it to build the fixture. Install python3 to run this suite.',
  );
}

describe.skipIf(!PYTHON3_AVAILABLE)('fixture parity: doctor vs. a refinstall-built fixture', () => {
  const tempRoots: string[] = [];

  async function makeTempDir(prefix: string): Promise<string> {
    const dir = await mkdtemp(join(tmpdir(), prefix));
    tempRoots.push(dir);
    return dir;
  }

  let client: Client;
  let fixtureDir: string;
  let baseline: RunDoctorOutput;

  beforeAll(async () => {
    // Build exactly the pair tests/run-matrix.sh does for its T1 case:
    //   make-fresh.sh <dir>         — bare Next.js-marker fixture repo
    //   refinstall.py <plugin> <dir> — deterministic Phase 4 scaffold install
    const work = await makeTempDir('fixture-parity-');
    fixtureDir = join(work, 'fresh');
    execFileSync('bash', [MAKE_FRESH, fixtureDir], { stdio: 'pipe' });
    execFileSync('python3', [REFINSTALL, PLUGIN_ROOT, fixtureDir], { stdio: 'pipe' });

    // git_hook baseline: PASS. refinstall.py deliberately never runs
    // install-git-hooks.sh (tests/run-matrix.sh runs it as its own explicit
    // T1 step, right after refinstall.py, for the same reason) — without
    // this, the installed pre-commit hook genuinely does not exist and
    // git_hook fails, which is the CORRECT native-check result for a bare
    // refinstall (see the ground truth in this task's brief). But git_hook
    // is not excluded from run_doctor's verdict decision the way
    // `dependencies` deliberately is (see checkDependencies()'s doc comment
    // in doctor.ts), so a failing git_hook forces verdict to 'failed'
    // instead of 'incomplete' — and this suite must assert 'incomplete'
    // (the three host-executed checks are still pending; never 'passed').
    // Running the installer here — identical to what run-matrix.sh does —
    // makes git_hook the one native check that is actually true on a fully
    // set-up repo, isolating `dependencies` as the sole reason verdict
    // stays 'incomplete' rather than becoming 'passed'.
    execFileSync('bash', ['scripts/install-git-hooks.sh'], { cwd: fixtureDir, stdio: 'pipe' });

    client = new Client({ name: 'fixture-parity-test', version: '0.0.0' });
    await client.connect(new StdioClientTransport({
      command: 'node', args: ['dist/index.js'], cwd: MCP_ROOT,
    }));

    const res = await client.callTool({ name: 'run_doctor', arguments: { target_path: fixtureDir } });
    baseline = res.structuredContent as RunDoctorOutput;
  }, 60_000);

  afterAll(async () => {
    await client?.close();
    while (tempRoots.length > 0) {
      const r = tempRoots.pop();
      if (r !== undefined) await rm(r, { recursive: true, force: true });
    }
  });

  it('reports installed: true', () => {
    expect(baseline.installed).toBe(true);
  });

  it('matches the six-check ground-truth baseline (git_hook PASS via the install-git-hooks.sh setup step above; dependencies is a permanent structural placeholder and always fails)', () => {
    expect(baseline.checks).toHaveLength(6);

    const manifest = findCheck(baseline, 'manifest');
    expect(manifest.passed).toBe(true);
    expect(manifest.detail).toContain('42 journaled file(s) checked; all present and matching');

    const settings = findCheck(baseline, 'settings');
    expect(settings.passed).toBe(true);
    expect(settings.detail).toContain('every managed gate hook is registered at its documented event');

    const gitHook = findCheck(baseline, 'git_hook');
    expect(gitHook.passed).toBe(true);

    const dependencies = findCheck(baseline, 'dependencies');
    expect(dependencies.passed).toBe(false);
    expect(dependencies.detail).toContain('not verifiable natively');

    const scorecard = findCheck(baseline, 'scorecard');
    expect(scorecard.passed).toBe(true);
    expect(scorecard.detail).toContain('9 fleet file(s) and 0 generated contract(s) scorecarded');

    const registry = findCheck(baseline, 'registry');
    expect(registry.passed).toBe(true);
    expect(registry.detail).toContain('routing table valid');
  });

  it('verdict is "incomplete" — never "passed" — because the three host-executed checks are still pending', () => {
    expect(baseline.verdict).toBe('incomplete');
  });

  it('host_must_run has exactly 3 entries', () => {
    expect(baseline.host_must_run).toHaveLength(3);
    expect(baseline.host_must_run.map((h) => h.key).sort()).toEqual(['dry_runs', 'hitl_smoke', 'py_compile']);
  });

  it('leaves the fixture tree byte-identical after run_doctor (mirrors readonly.test.ts\'s plugins/ fingerprint)', async () => {
    const before = await fingerprint(fixtureDir);
    await client.callTool({ name: 'run_doctor', arguments: { target_path: fixtureDir } });
    const after = await fingerprint(fixtureDir);
    expect(after).toBe(before);
  });

  // Both breakage tests below run against a fresh clone of the built
  // fixture, never the shared `fixtureDir` itself, so they stay
  // order-independent of every test above (and of each other).
  async function cloneFixture(prefix: string): Promise<string> {
    const dst = await makeTempDir(prefix);
    await cp(fixtureDir, dst, { recursive: true });
    return dst;
  }

  it('detects real breakage: deleting a journaled file fails the manifest check and names that file — the load-bearing assertion, without which this suite would only prove the doctor says yes', async () => {
    const brokenDir = await cloneFixture('fixture-parity-broken-');
    await rm(join(brokenDir, 'CLAUDE.md'));

    const res = await client.callTool({ name: 'run_doctor', arguments: { target_path: brokenDir } });
    const out = res.structuredContent as RunDoctorOutput;
    const manifest = findCheck(out, 'manifest');
    expect(manifest.passed).toBe(false);
    expect(manifest.detail).toContain('CLAUDE.md');
    expect(manifest.detail).toMatch(/missing:.*CLAUDE\.md/);
    expect(out.verdict).toBe('failed');
  });

  it('the modified-not-missing trap: editing a journaled file\'s contents still PASSES manifest, reported as modified, never as missing', async () => {
    const modifiedDir = await cloneFixture('fixture-parity-modified-');
    const original = await readFile(join(modifiedDir, 'AGENTS.md'), 'utf8');
    await writeFile(join(modifiedDir, 'AGENTS.md'), `${original}\n<!-- fixture-parity: locally edited -->\n`, 'utf8');

    const res = await client.callTool({ name: 'run_doctor', arguments: { target_path: modifiedDir } });
    const out = res.structuredContent as RunDoctorOutput;
    const manifest = findCheck(out, 'manifest');
    expect(manifest.passed).toBe(true);
    expect(manifest.detail).toContain('modified (not a failure): AGENTS.md');
    expect(manifest.detail).not.toContain('missing: AGENTS.md');
    expect(manifest.detail).not.toContain('missing:');
  });
});

/** Same recursive path+content sha256 fingerprint readonly.test.ts uses for
 *  `plugins/`, applied here to the whole fixture tree (including `.git/`,
 *  which run_doctor never touches either). Skips `__pycache__`/`node_modules`
 *  the same way — neither should exist in this fixture, but the exclusion is
 *  harmless if they ever do. */
async function fingerprint(dir: string): Promise<string> {
  const hash = createHash('sha256');
  const walk = async (d: string): Promise<void> => {
    for (const e of (await readdir(d, { withFileTypes: true })).sort(
      (a, b) => a.name.localeCompare(b.name),
    )) {
      if (e.name === '__pycache__' || e.name === 'node_modules') continue;
      const p = join(d, e.name);
      if (e.isDirectory()) await walk(p);
      else if (e.isFile()) hash.update(p).update(await readFile(p));
    }
  };
  await walk(dir);
  return hash.digest('hex');
}
