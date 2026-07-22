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
    for (const key of ['manifest', 'settings', 'git_hook', 'dependencies', 'scorecard', 'registry']) {
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

  // F2: EXPECTED_WIRING was transcribed from SKILL.md's Check 5 parenthetical
  // rather than from settings-fragment.json.tmpl, the file that parenthetical
  // cites, and dropped four hooks the fragment actually wires. Each of these
  // would previously PASS with the hook installed and journaled but never
  // wired anywhere in settings.json — including prompt_scan_guard.py, the
  // prompt-injection scanner.
  const MISSING_WIRINGS: [string, string][] = [
    ['prompt_scan_guard.py', 'UserPromptSubmit'],
    ['lint_on_save.py', 'PostToolUse'],
    ['context_monitor.py', 'PostToolUse'],
    ['session_learnings_notice.py', 'Stop'],
  ];

  for (const [file, event] of MISSING_WIRINGS) {
    it(`fails when managed ${file} is installed and journaled but not wired under ${event}`, async () => {
      const root = await makeRoot();
      const hookBody = '# hook\n';
      await put(root, `.claude/hooks/${file}`, hookBody);
      await put(root, '.claude/settings.json', JSON.stringify(MINIMAL_SETTINGS));
      await writeJournal(root, {
        [`.claude/hooks/${file}`]: { sha256: sha256(hookBody), owner: 'managed' },
      });
      const results = await runNativeChecks(await Target.open(root));
      const settings = getCheck(results, 'settings');
      expect(settings.passed).toBe(false);
      expect(settings.detail).toContain(file);
      expect(settings.detail).toContain(event);
    });
  }
});

describe('git_hook check', () => {
  it('passes when the installed hook exists, is executable, carries the marker, and the tracked twin exists', async () => {
    const root = await makeRoot();
    const body = '#!/usr/bin/env bash\n# agentic-os: pre-commit gate\necho ok\n';
    await putExecutable(root, '.git/hooks/pre-commit', body);
    await put(root, '.githooks/pre-commit', body);
    await writeJournal(root, {});
    const results = await runNativeChecks(await Target.open(root));
    expect(getCheck(results, 'git_hook').passed).toBe(true);
  });

  it('fails when the installed hook is missing', async () => {
    const root = await makeRoot();
    await put(root, '.githooks/pre-commit', '#!/usr/bin/env bash\n# agentic-os: pre-commit gate\necho ok\n');
    await writeJournal(root, {});
    const results = await runNativeChecks(await Target.open(root));
    const gitHook = getCheck(results, 'git_hook');
    expect(gitHook.passed).toBe(false);
    expect(gitHook.detail).toContain('install-git-hooks.sh');
  });

  it('fails when the installed hook exists but is not executable', async () => {
    const root = await makeRoot();
    const body = '#!/usr/bin/env bash\n# agentic-os: pre-commit gate\necho ok\n';
    await put(root, '.git/hooks/pre-commit', body); // no chmod -> not executable
    await put(root, '.githooks/pre-commit', body);
    await writeJournal(root, {});
    const results = await runNativeChecks(await Target.open(root));
    const gitHook = getCheck(results, 'git_hook');
    expect(gitHook.passed).toBe(false);
    expect(gitHook.detail).toContain('not executable');
  });

  it('resolves a relative core.hooksPath from .git/config and checks the hook there', async () => {
    const root = await makeRoot();
    const body = '#!/usr/bin/env bash\n# agentic-os: pre-commit gate\necho ok\n';
    await put(root, '.git/config', '[core]\n\trepositoryformatversion = 0\n\thooksPath = .customhooks\n');
    await putExecutable(root, '.customhooks/pre-commit', body);
    await put(root, '.githooks/pre-commit', body);
    await writeJournal(root, {});
    const results = await runNativeChecks(await Target.open(root));
    const gitHook = getCheck(results, 'git_hook');
    expect(gitHook.passed).toBe(true);
    expect(gitHook.detail).toContain('.customhooks/pre-commit');
  });

  // F4: an absolute hooksPath must never leak the operator's filesystem path
  // into `detail`, even though the check correctly fails (Target refuses to
  // resolve an absolute path, so the configured hook is unreachable).
  it('rejects an absolute core.hooksPath and never leaks it into detail', async () => {
    const root = await makeRoot();
    await put(root, '.git/config', '[core]\n\thooksPath = /opt/elsewhere/.githooks\n');
    await put(root, '.githooks/pre-commit', '#!/usr/bin/env bash\n# agentic-os: pre-commit gate\necho ok\n');
    await writeJournal(root, {});
    const results = await runNativeChecks(await Target.open(root));
    const gitHook = getCheck(results, 'git_hook');
    expect(gitHook.passed).toBe(false);
    expect(gitHook.detail).not.toContain('/opt/elsewhere');
    expect(gitHook.detail).toContain('.git/hooks/pre-commit'); // falls back to the default
  });

  it('anchors hooksPath parsing to [core] and ignores a comment or a value from another section', async () => {
    const root = await makeRoot();
    const body = '#!/usr/bin/env bash\n# agentic-os: pre-commit gate\necho ok\n';
    await put(
      root,
      '.git/config',
      '[core]\n' +
        '\t# hooksPath = .stale-comment\n' +
        '\thooksPath = .customhooks\n' +
        '[someother]\n' +
        '\thooksPath = .not-this-one\n',
    );
    await putExecutable(root, '.customhooks/pre-commit', body);
    await put(root, '.githooks/pre-commit', body);
    await writeJournal(root, {});
    const results = await runNativeChecks(await Target.open(root));
    const gitHook = getCheck(results, 'git_hook');
    expect(gitHook.passed).toBe(true);
    expect(gitHook.detail).toContain('.customhooks/pre-commit');
  });

  // F3: a gitlink (.git is a *file*, as in a worktree or submodule) must
  // never fall through to a hard FAIL with an unactionable remedy — the real
  // hooks dir it points to is outside the target root and unfixable from
  // inside it.
  it('reports the gitlink case (worktree/submodule) honestly instead of a false FAIL', async () => {
    const root = await makeRoot();
    await put(root, '.git', 'gitdir: /somewhere/outside/the/target/.git/worktrees/thisone\n');
    await put(root, '.githooks/pre-commit', '#!/usr/bin/env bash\n# agentic-os: pre-commit gate\necho ok\n');
    await writeJournal(root, {});
    const results = await runNativeChecks(await Target.open(root));
    const gitHook = getCheck(results, 'git_hook');
    expect(gitHook.passed).toBe(true);
    expect(gitHook.detail.toLowerCase()).toContain('gitlink');
    expect(gitHook.detail).not.toContain('install-git-hooks.sh');
  });
});

describe('dependencies check (F1)', () => {
  // The dependency half of SKILL.md's Check 6 needs
  // ~/.claude/plugins/installed_plugins.json, outside the target root and
  // unreachable through Target — it cannot run natively. The prior
  // implementation silently dropped the key; a consumer diffing this report
  // against the skill's six-key schema could not tell whether it passed,
  // failed, or never ran.
  it('emits an explicit, honest, fail-closed result naming the host follow-up', async () => {
    const root = await makeRoot();
    await writeJournal(root, {});
    const results = await runNativeChecks(await Target.open(root));
    const deps = getCheck(results, 'dependencies');
    expect(deps.passed).toBe(false);
    expect(deps.detail).toContain('installed_plugins.json');
    expect(deps.detail).not.toContain(root);
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

  // 7a stale-vs-missing distinction: a scorecard entry for a generated
  // contract whose file is no longer on disk must never be reported as
  // "stale" (target.sha256 returns undefined for a missing file, and an
  // unguarded `!==` comparison against that undefined makes every missing
  // file look like a content change). The file's absence is the manifest
  // check's finding; 7a must describe it accurately, not as staleness.
  it('reports a missing (not stale) message when a generated contract file is absent from disk', async () => {
    const root = await makeRoot();
    const gateBody = '# gate\n';
    const agentBody = '# generated agent contract\n';
    await put(root, '.claude/hooks/instruction_gate.py', gateBody);
    // Note: the agent file itself is never written to disk.
    await put(
      root,
      'docs/audits/instruction-scorecard.json',
      JSON.stringify({
        schema: 1,
        threshold: 95,
        files: {
          '.agentic/agents/schema-writer.md': { content_sha256: sha256(agentBody), composite_score: 100 },
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
    expect(scorecard.detail).not.toContain('stale');
    expect(scorecard.detail.toLowerCase()).toContain('missing');
  });

  // F5 (disclosure only): 7b enumerates the fleet from journal.files because
  // Target has no directory-listing primitive, so an agent contract dropped
  // straight into .agentic/agents/ without going through the installer is
  // invisible to this check. That limitation must be visible in the detail,
  // not silently assumed.
  it('discloses that the fleet was enumerated from the journal, not a directory scan', async () => {
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
    const scorecard = getCheck(results, 'scorecard');
    expect(scorecard.detail.toLowerCase()).toContain('journal');
  });

  // Minor: 7b previously added .claude/agents/<name>.md to the fleet
  // unconditionally, while gating CLAUDE.md/AGENTS.md/PATTERNS.md on
  // `exists`. A generated agent whose pointer file was never created (e.g.
  // an install that stopped short) got a spurious "no scorecard entry"
  // failure for a file that isn't there at all.
  it('does not require a scorecard entry for a .claude/agents pointer that was never created', async () => {
    const root = await makeRoot();
    const gateBody = '# gate\n';
    const agentBody = '# generated agent contract\n';
    await put(root, '.claude/hooks/instruction_gate.py', gateBody);
    await put(root, '.agentic/agents/schema-writer.md', agentBody);
    // Note: .claude/agents/schema-writer.md pointer is never created.
    await put(
      root,
      'docs/audits/instruction-scorecard.json',
      JSON.stringify({
        schema: 1,
        threshold: 95,
        files: { '.agentic/agents/schema-writer.md': { content_sha256: sha256(agentBody), composite_score: 100 } },
      }),
    );
    await writeJournal(root, {
      '.claude/hooks/instruction_gate.py': { sha256: sha256(gateBody), owner: 'managed' },
      '.agentic/agents/schema-writer.md': { sha256: sha256(agentBody), owner: 'generated' },
    });
    const results = await runNativeChecks(await Target.open(root));
    const scorecard = getCheck(results, 'scorecard');
    expect(scorecard.passed).toBe(true);
    expect(scorecard.detail).not.toContain('.claude/agents/schema-writer.md');
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

  // Minor: 8g's regex must anchor to exactly two leading hashes at line
  // start, or a deeper heading like "### Orchestration rules" (from a
  // mis-rendered or hand-edited tail) would be misread as the required
  // section and let a truncated registry pass.
  it('fails (8g) when only a deeper heading ("### Orchestration rules") is present, not "##"', async () => {
    const root = await makeRoot();
    const deeperHeading = `# Agent Registry

| Trigger / intent | Owning asset | Human gate / escalation notes |
| --- | --- | --- |
| Route ambiguous requests | \`.agentic/agents/dispatcher.md\` | read-only |
| <!-- generated-agent-rows --> | | |

### Orchestration rules
`;
    await put(root, '.agentic/guides/agent-registry.md', deeperHeading);
    await writeJournal(root, {
      '.agentic/guides/agent-registry.md': { sha256: sha256(deeperHeading), owner: 'generated' },
    });
    const results = await runNativeChecks(await Target.open(root));
    const registry = getCheck(results, 'registry');
    expect(registry.passed).toBe(false);
    expect(registry.detail).toContain('8g');
  });
});

describe('completeness and path hygiene', () => {
  it('runs all six checks (in addition to a healthy manifest) even when several checks fail', async () => {
    const root = await makeRoot();
    // Nothing installed at all except the journal itself: every check should
    // still produce a result, and several should legitimately fail.
    await writeJournal(root, {
      '.claude/hooks/missing_hook.py': { sha256: sha256('x'), owner: 'managed' },
    });
    const results = await runNativeChecks(await Target.open(root));
    const keys = results.map((r) => r.key).sort();
    expect(keys).toEqual(['dependencies', 'git_hook', 'manifest', 'registry', 'scorecard', 'settings']);
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
