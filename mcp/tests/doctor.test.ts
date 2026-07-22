import { describe, expect, it, afterEach } from 'vitest';
import { mkdtemp, mkdir, writeFile, chmod, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { Target } from '../src/target.js';
import { runNativeChecks, type CheckResult } from '../src/doctor.js';

// Synthetic target trees only — this suite never touches the real
// tests/fixtures/make-fresh.sh fixture (that's Task 7's integration test).
// Tests may write with node:fs/promises directly (only mcp/src/** is
// banned from doing so; see readonly.test.ts).

const roots: string[] = [];

async function makeRoot(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), 'doctor-target-'));
  roots.push(root);
  return root;
}

afterEach(async () => {
  while (roots.length > 0) {
    const r = roots.pop();
    if (r !== undefined) await rm(r, { recursive: true, force: true });
  }
});

function sha256(content: string): string {
  return createHash('sha256').update(content, 'utf8').digest('hex');
}

async function put(root: string, rel: string, content: string): Promise<void> {
  const full = join(root, rel);
  await mkdir(dirname(full), { recursive: true });
  await writeFile(full, content, 'utf8');
}

async function putExecutable(root: string, rel: string, content: string): Promise<void> {
  await put(root, rel, content);
  await chmod(join(root, rel), 0o755);
}

function getCheck(results: CheckResult[], key: string): CheckResult {
  const found = results.find((r) => r.key === key);
  if (found === undefined) throw new Error(`no check result with key "${key}"`);
  return found;
}

async function writeJournal(
  root: string,
  files: Record<string, { sha256: string; owner: string; template?: string }>,
): Promise<void> {
  await put(
    root,
    '.agentic/agentic-os/install.json',
    JSON.stringify({ agentic_os_version: '0.1.0', answers: {}, phase: 'scaffold', files, follow_ups: [] }, null, 2),
  );
}

const MINIMAL_SETTINGS = {
  permissions: { deny: ['Read(.env*)', 'Read(.auth/**)', 'Read(*token*.env)'] },
  hooks: {},
};

describe('runNativeChecks: not-installed precondition', () => {
  it('returns exactly one failed check with key not-installed, and no others, when the journal is missing', async () => {
    const root = await makeRoot();
    const target = await Target.open(root);
    const results = await runNativeChecks(target);
    expect(results).toHaveLength(1);
    expect(results[0]).toMatchObject({ key: 'not-installed', passed: false });
    for (const key of ['manifest', 'settings', 'githook', 'scorecard', 'registry']) {
      expect(results.find((r) => r.key === key)).toBeUndefined();
    }
  });
});

describe('manifest check', () => {
  it('passes when every journaled file is present with a matching hash', async () => {
    const root = await makeRoot();
    const body = 'print("hi")\n';
    await put(root, 'CLAUDE.md', body);
    await writeJournal(root, { 'CLAUDE.md': { sha256: sha256(body), owner: 'managed' } });
    const results = await runNativeChecks(await Target.open(root));
    expect(getCheck(results, 'manifest').passed).toBe(true);
  });

  it('fails when a journaled managed file is missing from disk', async () => {
    const root = await makeRoot();
    await writeJournal(root, {
      '.claude/hooks/some_hook.py': { sha256: sha256('anything'), owner: 'managed' },
    });
    const results = await runNativeChecks(await Target.open(root));
    const manifest = getCheck(results, 'manifest');
    expect(manifest.passed).toBe(false);
    expect(manifest.detail).toContain('.claude/hooks/some_hook.py');
  });

  it('THE TRAP: a modified file (hash differs) is reported as modified, not a failure', async () => {
    const root = await makeRoot();
    const original = 'original content\n';
    await put(root, 'CLAUDE.md', 'edited by the user, differs from journal\n');
    await writeJournal(root, { 'CLAUDE.md': { sha256: sha256(original), owner: 'managed' } });
    const results = await runNativeChecks(await Target.open(root));
    const manifest = getCheck(results, 'manifest');
    expect(manifest.passed).toBe(true);
    expect(manifest.detail.toLowerCase()).toContain('modified');
    expect(manifest.detail).toContain('CLAUDE.md');
  });

  it('a missing file with owner "user" is not a failure', async () => {
    const root = await makeRoot();
    await writeJournal(root, {
      '.claude/hooks/team_owned.py': { sha256: sha256('whatever'), owner: 'user' },
    });
    const results = await runNativeChecks(await Target.open(root));
    const manifest = getCheck(results, 'manifest');
    expect(manifest.passed).toBe(true);
  });

  it('a missing owner:user file does not mask a real missing managed-file failure', async () => {
    const root = await makeRoot();
    await writeJournal(root, {
      '.claude/hooks/team_owned.py': { sha256: sha256('whatever'), owner: 'user' },
      '.claude/hooks/really_missing.py': { sha256: sha256('whatever2'), owner: 'managed' },
    });
    const results = await runNativeChecks(await Target.open(root));
    const manifest = getCheck(results, 'manifest');
    expect(manifest.passed).toBe(false);
    expect(manifest.detail).toContain('.claude/hooks/really_missing.py');
  });
});

describe('settings check', () => {
  it('passes when a managed hook is registered at its documented event', async () => {
    const root = await makeRoot();
    const hookBody = '# hook\n';
    await put(root, '.claude/hooks/human_gated_commands.py', hookBody);
    await put(
      root,
      '.claude/settings.json',
      JSON.stringify({
        permissions: { deny: ['Read(.env*)', 'Read(.auth/**)', 'Read(*token*.env)'] },
        hooks: {
          PreToolUse: [
            {
              matcher: 'Bash',
              hooks: [{ type: 'command', command: 'python3 .claude/hooks/human_gated_commands.py' }],
            },
          ],
        },
      }),
    );
    await writeJournal(root, {
      '.claude/hooks/human_gated_commands.py': { sha256: sha256(hookBody), owner: 'managed' },
    });
    const results = await runNativeChecks(await Target.open(root));
    expect(getCheck(results, 'settings').passed).toBe(true);
  });

  it('fails, naming the hook, when a managed hook is absent from settings.json', async () => {
    const root = await makeRoot();
    const hookBody = '# hook\n';
    await put(root, '.claude/hooks/human_gated_commands.py', hookBody);
    await put(root, '.claude/settings.json', JSON.stringify(MINIMAL_SETTINGS));
    await writeJournal(root, {
      '.claude/hooks/human_gated_commands.py': { sha256: sha256(hookBody), owner: 'managed' },
    });
    const results = await runNativeChecks(await Target.open(root));
    const settings = getCheck(results, 'settings');
    expect(settings.passed).toBe(false);
    expect(settings.detail).toContain('human_gated_commands.py');
  });

  it('fails when a wired hook command points at a script that does not exist', async () => {
    const root = await makeRoot();
    await put(
      root,
      '.claude/settings.json',
      JSON.stringify({
        permissions: { deny: ['Read(.env*)', 'Read(.auth/**)', 'Read(*token*.env)'] },
        hooks: {
          PreToolUse: [
            {
              matcher: 'Bash',
              hooks: [{ type: 'command', command: 'python3 .claude/hooks/ghost_hook.py' }],
            },
          ],
        },
      }),
    );
    await writeJournal(root, {});
    const results = await runNativeChecks(await Target.open(root));
    const settings = getCheck(results, 'settings');
    expect(settings.passed).toBe(false);
    expect(settings.detail).toContain('ghost_hook.py');
  });

  it('fails when permissions.deny is missing a required entry', async () => {
    const root = await makeRoot();
    await put(root, '.claude/settings.json', JSON.stringify({ permissions: { deny: [] }, hooks: {} }));
    await writeJournal(root, {});
    const results = await runNativeChecks(await Target.open(root));
    const settings = getCheck(results, 'settings');
    expect(settings.passed).toBe(false);
    expect(settings.detail).toContain('Read(.env*)');
  });
});

describe('githook check', () => {
  it('passes when the installed hook exists, is executable, carries the marker, and the tracked twin exists', async () => {
    const root = await makeRoot();
    const body = '#!/usr/bin/env bash\n# agentic-os: pre-commit gate\necho ok\n';
    await putExecutable(root, '.git/hooks/pre-commit', body);
    await put(root, '.githooks/pre-commit', body);
    await writeJournal(root, {});
    const results = await runNativeChecks(await Target.open(root));
    expect(getCheck(results, 'githook').passed).toBe(true);
  });

  it('fails when the installed hook is missing', async () => {
    const root = await makeRoot();
    await put(root, '.githooks/pre-commit', '#!/usr/bin/env bash\n# agentic-os: pre-commit gate\necho ok\n');
    await writeJournal(root, {});
    const results = await runNativeChecks(await Target.open(root));
    const githook = getCheck(results, 'githook');
    expect(githook.passed).toBe(false);
    expect(githook.detail).toContain('install-git-hooks.sh');
  });
});

describe('scorecard check', () => {
  it('is skipped (pass) when instruction_gate.py is not installed', async () => {
    const root = await makeRoot();
    await writeJournal(root, {});
    const results = await runNativeChecks(await Target.open(root));
    const scorecard = getCheck(results, 'scorecard');
    expect(scorecard.passed).toBe(true);
    expect(scorecard.detail.toLowerCase()).toContain('skip');
  });

  it('fails when instruction_gate.py is installed but the scorecard file is missing', async () => {
    const root = await makeRoot();
    const gateBody = '# gate\n';
    await put(root, '.claude/hooks/instruction_gate.py', gateBody);
    await writeJournal(root, {
      '.claude/hooks/instruction_gate.py': { sha256: sha256(gateBody), owner: 'managed' },
    });
    const results = await runNativeChecks(await Target.open(root));
    const scorecard = getCheck(results, 'scorecard');
    expect(scorecard.passed).toBe(false);
    expect(scorecard.detail).toContain('instruction-scorecard.json');
  });

  it('passes when the gate is installed and every governed file is scorecarded above threshold', async () => {
    const root = await makeRoot();
    const gateBody = '# gate\n';
    const claudeMd = '# CLAUDE\n';
    await put(root, '.claude/hooks/instruction_gate.py', gateBody);
    await put(root, 'CLAUDE.md', claudeMd);
    await put(
      root,
      'docs/audits/instruction-scorecard.json',
      JSON.stringify({
        schema: 1,
        threshold: 95,
        files: { 'CLAUDE.md': { content_sha256: sha256(claudeMd), composite_score: 100, source: 'template-inherited' } },
      }),
    );
    await writeJournal(root, {
      '.claude/hooks/instruction_gate.py': { sha256: sha256(gateBody), owner: 'managed' },
      'CLAUDE.md': { sha256: sha256(claudeMd), owner: 'managed' },
    });
    const results = await runNativeChecks(await Target.open(root));
    expect(getCheck(results, 'scorecard').passed).toBe(true);
  });

  it('fails when a generated agent contract has no scorecard entry', async () => {
    const root = await makeRoot();
    const gateBody = '# gate\n';
    const agentBody = '# generated agent contract\n';
    await put(root, '.claude/hooks/instruction_gate.py', gateBody);
    await put(root, '.agentic/agents/schema-writer.md', agentBody);
    await put(root, '.claude/agents/schema-writer.md', 'pointer\n');
    await put(
      root,
      'docs/audits/instruction-scorecard.json',
      JSON.stringify({ schema: 1, threshold: 95, files: {} }),
    );
    await writeJournal(root, {
      '.claude/hooks/instruction_gate.py': { sha256: sha256(gateBody), owner: 'managed' },
      '.agentic/agents/schema-writer.md': { sha256: sha256(agentBody), owner: 'generated' },
    });
    const results = await runNativeChecks(await Target.open(root));
    const scorecard = getCheck(results, 'scorecard');
    expect(scorecard.passed).toBe(false);
    expect(scorecard.detail).toContain('.agentic/agents/schema-writer.md');
  });

  it('fails when a generated agent contract scores below its effective threshold', async () => {
    const root = await makeRoot();
    const gateBody = '# gate\n';
    const agentBody = '# generated agent contract\n';
    await put(root, '.claude/hooks/instruction_gate.py', gateBody);
    await put(root, '.agentic/agents/schema-writer.md', agentBody);
    await put(
      root,
      'docs/audits/instruction-scorecard.json',
      JSON.stringify({
        schema: 1,
        threshold: 95,
        files: {
          '.agentic/agents/schema-writer.md': { content_sha256: sha256(agentBody), composite_score: 80 },
        },
      }),
    );
    await writeJournal(root, {
      '.claude/hooks/instruction_gate.py': { sha256: sha256(gateBody), owner: 'managed' },
      '.agentic/agents/schema-writer.md': { sha256: sha256(agentBody), owner: 'generated' },
    });
    const results = await runNativeChecks(await Target.open(root));
    const scorecard = getCheck(results, 'scorecard');
    expect(scorecard.passed).toBe(false);
    expect(scorecard.detail).toContain('80');
  });
});

describe('registry check', () => {
  const HEALTHY_REGISTRY = `# Agent Registry

| Trigger / intent | Owning asset | Human gate / escalation notes |
| --- | --- | --- |
| Route ambiguous requests | \`.agentic/agents/dispatcher.md\` | read-only |
| <!-- generated-agent-rows --> | | |
| Write the schema | \`.agentic/agents/schema-writer.md\` | writer |

Closing paragraph text.

## Orchestration rules

- one owner per intent
`;

  it('is skipped (pass) when agent-registry.md is not part of this install', async () => {
    const root = await makeRoot();
    await writeJournal(root, {});
    const results = await runNativeChecks(await Target.open(root));
    const registry = getCheck(results, 'registry');
    expect(registry.passed).toBe(true);
    expect(registry.detail.toLowerCase()).toContain('skip');
  });

  it('reports N/A (pass) when journaled but missing from disk — that is the manifest check\'s failure', async () => {
    const root = await makeRoot();
    await writeJournal(root, {
      '.agentic/guides/agent-registry.md': { sha256: sha256('anything'), owner: 'generated' },
    });
    const results = await runNativeChecks(await Target.open(root));
    const registry = getCheck(results, 'registry');
    expect(registry.passed).toBe(true);
    expect(registry.detail).toContain('N/A');
  });

  it('passes on a healthy registry: valid table, one marker row, one row per generated contract, intact tail', async () => {
    const root = await makeRoot();
    await put(root, '.agentic/guides/agent-registry.md', HEALTHY_REGISTRY);
    await put(root, '.agentic/agents/schema-writer.md', 'contract\n');
    await writeJournal(root, {
      '.agentic/guides/agent-registry.md': { sha256: sha256(HEALTHY_REGISTRY), owner: 'generated' },
      '.agentic/agents/schema-writer.md': { sha256: sha256('contract\n'), owner: 'generated' },
    });
    const results = await runNativeChecks(await Target.open(root));
    const registry = getCheck(results, 'registry');
    expect(registry.passed).toBe(true);
  });

  it('fails (8a) when the routing header is not followed by a valid delimiter row', async () => {
    const root = await makeRoot();
    const broken = `# Agent Registry

| Trigger / intent | Owning asset | Human gate / escalation notes |
Not a delimiter row at all.
| <!-- generated-agent-rows --> | | |

## Orchestration rules
`;
    await put(root, '.agentic/guides/agent-registry.md', broken);
    await writeJournal(root, {
      '.agentic/guides/agent-registry.md': { sha256: sha256(broken), owner: 'generated' },
    });
    const results = await runNativeChecks(await Target.open(root));
    const registry = getCheck(results, 'registry');
    expect(registry.passed).toBe(false);
    expect(registry.detail).toContain('8a');
  });

  it('fails (8e) when a generated contract has no row in the routing table', async () => {
    const root = await makeRoot();
    const noRow = `# Agent Registry

| Trigger / intent | Owning asset | Human gate / escalation notes |
| --- | --- | --- |
| Route ambiguous requests | \`.agentic/agents/dispatcher.md\` | read-only |
| <!-- generated-agent-rows --> | | |

## Orchestration rules
`;
    await put(root, '.agentic/guides/agent-registry.md', noRow);
    await put(root, '.agentic/agents/schema-writer.md', 'contract\n');
    await writeJournal(root, {
      '.agentic/guides/agent-registry.md': { sha256: sha256(noRow), owner: 'generated' },
      '.agentic/agents/schema-writer.md': { sha256: sha256('contract\n'), owner: 'generated' },
    });
    const results = await runNativeChecks(await Target.open(root));
    const registry = getCheck(results, 'registry');
    expect(registry.passed).toBe(false);
    expect(registry.detail).toContain('8e');
    expect(registry.detail).toContain('.agentic/agents/schema-writer.md');
  });

  it('fails (8d) on an orphaned pipe-delimited row outside any valid table block', async () => {
    const root = await makeRoot();
    const orphaned = `# Agent Registry

| Trigger / intent | Owning asset | Human gate / escalation notes |
| --- | --- | --- |
| Route ambiguous requests | \`.agentic/agents/dispatcher.md\` | read-only |
| <!-- generated-agent-rows --> | | |

Some prose paragraph breaks the block here.
| An orphaned row | \`.agentic/agents/schema-writer.md\` | this renders as a paragraph on GitHub |

## Orchestration rules
`;
    await put(root, '.agentic/guides/agent-registry.md', orphaned);
    await writeJournal(root, {
      '.agentic/guides/agent-registry.md': { sha256: sha256(orphaned), owner: 'generated' },
    });
    const results = await runNativeChecks(await Target.open(root));
    const registry = getCheck(results, 'registry');
    expect(registry.passed).toBe(false);
    expect(registry.detail).toContain('8d');
  });

  it('fails (8g) when the tail after the routing table is missing the Orchestration rules section', async () => {
    const root = await makeRoot();
    const truncated = `# Agent Registry

| Trigger / intent | Owning asset | Human gate / escalation notes |
| --- | --- | --- |
| Route ambiguous requests | \`.agentic/agents/dispatcher.md\` | read-only |
| <!-- generated-agent-rows --> | | |
`;
    await put(root, '.agentic/guides/agent-registry.md', truncated);
    await writeJournal(root, {
      '.agentic/guides/agent-registry.md': { sha256: sha256(truncated), owner: 'generated' },
    });
    const results = await runNativeChecks(await Target.open(root));
    const registry = getCheck(results, 'registry');
    expect(registry.passed).toBe(false);
    expect(registry.detail).toContain('8g');
  });
});

describe('completeness and path hygiene', () => {
  it('runs all five checks (in addition to a healthy manifest) even when several checks fail', async () => {
    const root = await makeRoot();
    // Nothing installed at all except the journal itself: every check should
    // still produce a result, and several should legitimately fail.
    await writeJournal(root, {
      '.claude/hooks/missing_hook.py': { sha256: sha256('x'), owner: 'managed' },
    });
    const results = await runNativeChecks(await Target.open(root));
    const keys = results.map((r) => r.key).sort();
    expect(keys).toEqual(['githook', 'manifest', 'registry', 'scorecard', 'settings']);
  });

  it('never includes an absolute filesystem path in any detail string', async () => {
    const root = await makeRoot();
    const hookBody = '# hook\n';
    await put(root, '.claude/hooks/human_gated_commands.py', hookBody);
    await writeJournal(root, {
      '.claude/hooks/human_gated_commands.py': { sha256: sha256(hookBody), owner: 'managed' },
      '.claude/hooks/really_missing.py': { sha256: sha256('nope'), owner: 'managed' },
    });
    const results = await runNativeChecks(await Target.open(root));
    for (const r of results) {
      expect(r.detail).not.toContain(root);
      expect(r.detail).not.toMatch(/^\/|[^:]\/(Users|home|tmp)\//);
    }
  });
});
