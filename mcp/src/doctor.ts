import type { Target } from './target.js';

/** The result of one doctor check. `detail` is always target-relative text —
 *  never an absolute filesystem path — since this server may be auditing a
 *  repo it did not choose the location of. */
export type CheckResult = { key: string; passed: boolean; detail: string };

/** One entry in the install journal's `files` map
 *  (`.agentic/agentic-os/install.json`). */
interface JournalFileEntry {
  sha256: string;
  owner: string;
  template?: string;
}

interface Journal {
  agentic_os_version?: string;
  files?: Record<string, JournalFileEntry>;
}

/** Runs the five doctor checks that are pure file inspection against
 *  `target` — no Python execution, no filesystem access outside `target`.
 *  Checks 2 (hook compile/import), 3 (canned-event dry-runs), and 4 (HITL
 *  smoke) require running Python and are out of scope here; the host runs
 *  those from a command plan `run_doctor` returns separately.
 *
 *  Precondition: `.agentic/agentic-os/install.json` missing (or unparsable)
 *  ⇒ a single failed `not-installed` check, and none of the five run. */
export async function runNativeChecks(target: Target): Promise<CheckResult[]> {
  const raw = await target.read('.agentic/agentic-os/install.json');
  if (raw === undefined) {
    return [
      {
        key: 'not-installed',
        passed: false,
        detail: '.agentic/agentic-os/install.json is missing — run /agentic-init',
      },
    ];
  }

  let journal: Journal;
  try {
    journal = JSON.parse(raw) as Journal;
  } catch {
    return [
      {
        key: 'not-installed',
        passed: false,
        detail: '.agentic/agentic-os/install.json is not valid JSON — run /agentic-init',
      },
    ];
  }

  const files = journal.files ?? {};

  // Every check runs to completion even after an earlier one fails — the
  // report must be complete — so these are independent calls, not a
  // short-circuiting chain.
  return [
    await checkManifest(target, files),
    await checkSettings(target, files),
    await checkGitHook(target),
    checkDependencies(),
    await checkScorecard(target, files),
    await checkRegistry(target, files),
  ];
}

// ---------------------------------------------------------------------------
// Check 1 — File manifest vs journal
// ---------------------------------------------------------------------------
//
// SKILL.md: "File missing ⇒ fail (manifest), unless owner: "user" ... Current
// sha256 ... differs from journaled ⇒ not a failure: report as modified."
// The trap: a hash mismatch is never a failure by itself, regardless of
// owner; only a missing file counts against `passed`, and even then only
// when its owner is not "user".
async function checkManifest(
  target: Target,
  files: Record<string, JournalFileEntry>,
): Promise<CheckResult> {
  const entries = Object.entries(files);
  const missing: string[] = [];
  const missingUserOwned: string[] = [];
  const modified: string[] = [];

  for (const [path, entry] of entries) {
    const exists = await target.exists(path);
    if (!exists) {
      if (entry.owner === 'user') {
        missingUserOwned.push(path);
      } else {
        missing.push(path);
      }
      continue;
    }
    const currentHash = await target.sha256(path);
    if (currentHash !== entry.sha256) {
      modified.push(path);
    }
  }

  const passed = missing.length === 0;
  const parts: string[] = [`${entries.length} journaled file(s) checked`];
  if (missing.length > 0) parts.push(`missing: ${missing.join(', ')}`);
  if (modified.length > 0) parts.push(`modified (not a failure): ${modified.join(', ')}`);
  if (missingUserOwned.length > 0) {
    parts.push(`missing, owner=user (not a failure): ${missingUserOwned.join(', ')}`);
  }
  if (missing.length === 0 && modified.length === 0 && missingUserOwned.length === 0) {
    parts.push('all present and matching');
  }
  return { key: 'manifest', passed, detail: parts.join('; ') };
}

// ---------------------------------------------------------------------------
// Check 5 — Settings registration
// ---------------------------------------------------------------------------

interface HookWiring {
  file: string;
  event: string;
  command: string;
}

/** The fragment's actual layout — read from
 *  `plugins/agentic-os/templates/hooks/settings-fragment.json.tmpl` directly,
 *  not from SKILL.md Check 5's parenthetical illustration, which turned out
 *  to omit four of the fragment's fifteen entries (prompt_scan_guard.py,
 *  lint_on_save.py, context_monitor.py, session_learnings_notice.py) — a
 *  settings.json that dropped the prompt-injection scanner previously PASSED
 *  this check. `doctor.ts` receives a `Target`, not the bundle `Content`, so
 *  this list cannot be derived from the template file at check time; it must
 *  be kept in lockstep with the fragment by hand. If the fragment's wiring
 *  changes, update this list to match — only these named "gate" hooks are
 *  checked; a mature repo's `.claude/hooks/` may also carry a team's own
 *  scripts, which are none of this check's business. */
const EXPECTED_WIRING: HookWiring[] = [
  { file: 'prompt_scan_guard.py', event: 'UserPromptSubmit', command: 'python3 .claude/hooks/prompt_scan_guard.py' },
  { file: 'human_gated_commands.py', event: 'PreToolUse', command: 'python3 .claude/hooks/human_gated_commands.py' },
  { file: 'precommit_review_gate.py', event: 'PreToolUse', command: 'python3 .claude/hooks/precommit_review_gate.py' },
  { file: 'guarded_write_paths.py', event: 'PreToolUse', command: 'python3 .claude/hooks/guarded_write_paths.py' },
  { file: 'write_scope_guard.py', event: 'PreToolUse', command: 'python3 .claude/hooks/write_scope_guard.py block' },
  { file: 'migration_notice.py', event: 'PostToolUse', command: 'python3 .claude/hooks/migration_notice.py' },
  { file: 'instruction_stale_notice.py', event: 'PostToolUse', command: 'python3 .claude/hooks/instruction_stale_notice.py' },
  { file: 'lint_on_save.py', event: 'PostToolUse', command: 'python3 .claude/hooks/lint_on_save.py' },
  { file: 'context_monitor.py', event: 'PostToolUse', command: 'python3 .claude/hooks/context_monitor.py' },
  { file: 'instruction_gate.py', event: 'SubagentStart', command: 'python3 .claude/hooks/instruction_gate.py' },
  { file: 'subagent_gate.py', event: 'Stop', command: 'python3 .claude/hooks/subagent_gate.py' },
  { file: 'session_learnings_notice.py', event: 'Stop', command: 'python3 .claude/hooks/session_learnings_notice.py' },
  { file: 'subagent_gate.py', event: 'SubagentStop', command: 'python3 .claude/hooks/subagent_gate.py' },
  { file: 'session_start_bootstrap.py', event: 'SessionStart', command: 'python3 .claude/hooks/session_start_bootstrap.py' },
  { file: 'precompact_checkpoint.py', event: 'PreCompact', command: 'python3 .claude/hooks/precompact_checkpoint.py' },
];

const REQUIRED_DENY = ['Read(.env*)', 'Read(.auth/**)', 'Read(*token*.env)'];

interface SettingsHookEntry {
  command?: string;
}
interface SettingsHookGroup {
  matcher?: string;
  hooks?: SettingsHookEntry[];
}
interface SettingsJson {
  permissions?: { deny?: string[] };
  hooks?: Record<string, SettingsHookGroup[]>;
}

function collectCommands(settings: SettingsJson): string[] {
  const out: string[] = [];
  for (const groups of Object.values(settings.hooks ?? {})) {
    for (const group of groups) {
      for (const h of group.hooks ?? []) {
        if (typeof h.command === 'string') out.push(h.command);
      }
    }
  }
  return out;
}

const HOOK_COMMAND_RE = /(\.claude\/hooks\/[A-Za-z0-9_.-]+\.py)/;

async function checkSettings(
  target: Target,
  files: Record<string, JournalFileEntry>,
): Promise<CheckResult> {
  const raw = await target.read('.claude/settings.json');
  if (raw === undefined) {
    return { key: 'settings', passed: false, detail: '.claude/settings.json is missing' };
  }
  let settings: SettingsJson;
  try {
    settings = JSON.parse(raw) as SettingsJson;
  } catch {
    return { key: 'settings', passed: false, detail: '.claude/settings.json is not valid JSON' };
  }

  const failures: string[] = [];

  for (const wiring of EXPECTED_WIRING) {
    const journalPath = `.claude/hooks/${wiring.file}`;
    const entry = files[journalPath];
    if (entry === undefined || entry.owner !== 'managed') continue; // not part of this install
    const eventGroups = settings.hooks?.[wiring.event] ?? [];
    const wired = eventGroups.some((g) => (g.hooks ?? []).some((h) => h.command === wiring.command));
    if (!wired) {
      failures.push(`${journalPath} is not wired under ${wiring.event} (expected command "${wiring.command}")`);
    }
  }

  // The inverse: a wired hook command whose script file does not exist would
  // exit 2 on every event and block all tool use.
  const seen = new Set<string>();
  for (const command of collectCommands(settings)) {
    const match = HOOK_COMMAND_RE.exec(command);
    if (match === null) continue;
    const hookPath = match[1];
    if (hookPath === undefined || seen.has(hookPath)) continue;
    seen.add(hookPath);
    if (!(await target.exists(hookPath))) {
      failures.push(`${hookPath} is wired in .claude/settings.json but the script does not exist`);
    }
  }

  const currentDeny = settings.permissions?.deny ?? [];
  const missingDeny = REQUIRED_DENY.filter((d) => !currentDeny.includes(d));
  if (missingDeny.length > 0) {
    failures.push(`permissions.deny is missing required entries: ${missingDeny.join(', ')}`);
  }

  const passed = failures.length === 0;
  const detail = passed
    ? 'every managed gate hook is registered at its documented event; permissions.deny complete'
    : failures.join('; ');
  return { key: 'settings', passed, detail };
}

// ---------------------------------------------------------------------------
// Check 6 — git_hook + dependencies
// ---------------------------------------------------------------------------
//
// SKILL.md's Check 6 defines two verdict keys: `git_hook` and `dependencies`.
// The dependency half verifies plugin sources against
// `~/.claude/plugins/installed_plugins.json` — a path outside the target
// repository entirely — cross-referenced with `manifest/dependencies.json` (a
// plugin-bundle file, not a target-repo file). Neither is reachable through
// `Target`, whose containment guarantee is scoped to the target repo, so that
// half cannot be a "pure file inspection" of the target and is not
// implemented natively; `checkDependencies` below emits an explicit,
// honest placeholder instead of silently dropping the key (see its doc
// comment for why `passed: false`, not a skip-shaped `true`).

/** True for anything that is not a plain repo-relative path: a POSIX absolute
 *  path, a Windows drive-letter path, or a UNC path. `Target` already refuses
 *  an absolute `rel` outright (see target.ts's containment rule), so
 *  accepting one here would only produce a failing check whose message
 *  embeds the operator's real filesystem path — exactly the leak this
 *  guards against (F4). */
function isAbsoluteHooksPath(value: string): boolean {
  return value.startsWith('/') || value.startsWith('\\') || /^[A-Za-z]:[\\/]/.test(value);
}

/** The value of the *last* `hooksPath = ...` assignment inside the `[core]`
 *  section of a git config file — git's own precedence rule (last wins),
 *  restricted to the section the key is actually scoped to. A commented-out
 *  line (`#`/`;` after trimming) is skipped, and a `hooksPath` sitting under
 *  some other `[section]` is ignored, so `# hooksPath = old` or a same-named
 *  key in an unrelated section can never shadow the real value. */
function lastCoreHooksPath(config: string): string | undefined {
  let inCore = false;
  let found: string | undefined;
  for (const rawLine of config.split('\n')) {
    const line = rawLine.trim();
    if (line.length === 0 || line.startsWith('#') || line.startsWith(';')) continue;
    const section = /^\[([^\]]+)\]/.exec(line);
    if (section) {
      inCore = (section[1] ?? '').trim().toLowerCase() === 'core';
      continue;
    }
    if (!inCore) continue;
    const match = /^hooksPath\s*=\s*(.+)$/.exec(line);
    const raw = match?.[1];
    if (raw !== undefined) found = raw.trim();
  }
  return found;
}

async function resolveHooksDir(target: Target): Promise<string> {
  const config = await target.read('.git/config');
  if (config !== undefined) {
    const raw = lastCoreHooksPath(config);
    if (raw !== undefined) {
      const value = raw.replace(/\/+$/, '');
      // An absolute hooksPath is rejected outright rather than surfaced: it
      // is unreachable through Target (containment refuses absolute input)
      // and interpolating it into a failure message would leak the
      // operator's filesystem path (F4). Falling back to the conventional
      // default is the honest behavior — the check still fails, just
      // without a leak.
      if (value.length > 0 && !isAbsoluteHooksPath(value)) return value;
    }
  }
  return '.git/hooks';
}

async function checkGitHook(target: Target): Promise<CheckResult> {
  const trackedTwin = '.githooks/pre-commit';
  const trackedExists = await target.exists(trackedTwin);

  // A gitlink — `.git` is a regular *file* containing `gitdir: <path>`,
  // rather than a directory — means this checkout is a git worktree or
  // submodule (F3). The real hooks directory the gitlink points to lives
  // outside the target root, and `Target`'s containment guarantee will never
  // follow it there. Falling through to the directory-based logic below
  // would read `.git/config` as undefined (there is no such path under a
  // gitlink), fall back to the default `.git/hooks`, find nothing there
  // either, and report a hard FAIL whose remedy
  // (`bash scripts/install-git-hooks.sh`) installs into the *real* repo's
  // hooks dir, not this checkout's — a failure that could never clear.
  // `target.exists` reports true only for a regular file, so this one call
  // is sufficient to distinguish the gitlink case from an ordinary `.git/`
  // directory.
  const gitIsGitlink = await target.exists('.git');
  if (gitIsGitlink) {
    const parts = [
      '.git is a gitlink (this checkout is a git worktree or submodule); the installed ' +
        'git hooks directory it points to is outside the target root and is not verifiable natively',
    ];
    parts.push(trackedExists ? `tracked twin ${trackedTwin} present` : `tracked twin ${trackedTwin} is missing`);
    // Only the part that is genuinely unreachable (the installed hook) is
    // treated as non-authoritative; the tracked twin is an ordinary
    // repo-relative file and stays a real failure if missing.
    return { key: 'git_hook', passed: trackedExists, detail: parts.join('; ') };
  }

  const hooksDir = await resolveHooksDir(target);
  const installedPath = `${hooksDir}/pre-commit`;
  const localPath = `${hooksDir}/pre-commit.local`;

  const installedExists = await target.exists(installedPath);
  const installedExecutable = installedExists && (await target.isExecutable(installedPath));
  const installedContent = installedExists ? await target.read(installedPath) : undefined;
  const hasMarker = installedContent !== undefined && installedContent.includes('agentic-os:');
  const installed = installedExists && installedExecutable && hasMarker;

  const hasLocal = await target.exists(localPath);

  const failures: string[] = [];
  if (!installed) {
    const reason = !installedExists
      ? 'missing'
      : !installedExecutable
        ? 'not executable'
        : 'missing the agentic-os: marker';
    failures.push(`installed git hook ${installedPath} is ${reason} (remedy: bash scripts/install-git-hooks.sh)`);
  }
  if (!trackedExists) {
    failures.push(`tracked twin ${trackedTwin} is missing`);
  }

  const passed = failures.length === 0;
  const parts = passed
    ? [`installed hook present, executable, and marked at ${installedPath}; tracked twin ${trackedTwin} present`]
    : [...failures];
  if (hasLocal) parts.push(`chained foreign hook detected at ${localPath} (informational)`);
  return { key: 'git_hook', passed, detail: parts.join('; ') };
}

/** The `dependencies` half of SKILL.md's Check 6, emitted as an explicit,
 *  honest placeholder rather than silently omitted (F1). It genuinely cannot
 *  run natively (see the comment atop this section), but it DOES apply to
 *  every install — unlike the true "not applicable" skips elsewhere in this
 *  module (registry when its template wasn't installed, scorecard when the
 *  gate isn't installed), where `passed: true` correctly means "this check
 *  has nothing to say here." Reporting dependencies as passed by default
 *  would silently hide a genuinely missing non-optional plugin behind a
 *  green check, so this is a deliberate fail-closed `passed: false`: a
 *  consumer must see it as outstanding, and the host is expected to replace
 *  this placeholder with the real verdict after resolving
 *  installed_plugins.json itself. */
function checkDependencies(): CheckResult {
  return {
    key: 'dependencies',
    passed: false,
    detail:
      'not verifiable natively — requires ~/.claude/plugins/installed_plugins.json, ' +
      'outside the target root; the host must run this check',
  };
}

// ---------------------------------------------------------------------------
// Check 7 — Scorecard coverage and thresholds
// ---------------------------------------------------------------------------

interface ScorecardEntry {
  content_sha256?: string;
  composite_score?: number;
  gate_threshold?: number;
  source?: string;
}
interface ScorecardJson {
  threshold?: number;
  files?: Record<string, ScorecardEntry>;
}

const DEFAULT_THRESHOLD = 95;
const GENERATED_AGENT_RE = /^\.agentic\/agents\/[^/]+\.md$/;

async function checkScorecard(
  target: Target,
  files: Record<string, JournalFileEntry>,
): Promise<CheckResult> {
  const gateEntry = files['.claude/hooks/instruction_gate.py'];
  const gateInstalled = gateEntry !== undefined && gateEntry.owner === 'managed';
  if (!gateInstalled) {
    return { key: 'scorecard', passed: true, detail: 'skipped — instruction_gate.py not installed' };
  }

  const raw = await target.read('docs/audits/instruction-scorecard.json');
  if (raw === undefined) {
    return {
      key: 'scorecard',
      passed: false,
      detail:
        'docs/audits/instruction-scorecard.json is missing while instruction_gate.py is installed — ' +
        'every governed agent invocation will hard-block as never graded',
    };
  }

  let scorecard: ScorecardJson;
  try {
    scorecard = JSON.parse(raw) as ScorecardJson;
  } catch {
    return { key: 'scorecard', passed: false, detail: 'docs/audits/instruction-scorecard.json is not valid JSON' };
  }
  const scored = scorecard.files ?? {};

  const failures: string[] = [];
  const warnings: string[] = [];

  // 7a — generated-agent thresholds.
  const generatedAgentPaths = Object.entries(files)
    .filter(([path, entry]) => entry.owner === 'generated' && GENERATED_AGENT_RE.test(path))
    .map(([path]) => path);

  for (const path of generatedAgentPaths) {
    const entry = scored[path];
    if (entry === undefined) {
      failures.push(`${path} has no scorecard entry (invocations will hard-block as never graded)`);
      continue;
    }
    const currentHash = await target.sha256(path);
    // A missing file (sha256 undefined) is not staleness — content_sha256
    // !== undefined would otherwise be true for every missing file and
    // mislabel it as "stale (content changed since grading)". The file's
    // absence is already the manifest check's finding; report it accurately
    // here instead of implying content drift that never happened.
    if (currentHash === undefined) {
      failures.push(`${path} is missing from disk (see the manifest check) — no content change occurred`);
      continue;
    }
    if (entry.content_sha256 !== currentHash) {
      failures.push(`${path} scorecard entry is stale (content changed since grading)`);
      continue;
    }
    const effectiveThreshold = entry.gate_threshold ?? DEFAULT_THRESHOLD;
    const score = entry.composite_score ?? 0;
    if (score < effectiveThreshold) {
      failures.push(`${path} composite_score ${score} is below its effective threshold ${effectiveThreshold}`);
    } else if (entry.gate_threshold !== undefined && entry.gate_threshold < DEFAULT_THRESHOLD) {
      warnings.push(`${path} has a relaxed gate_threshold ${entry.gate_threshold} (PLAN decision-6)`);
    }
  }

  // 7b — full-fleet coverage.
  //
  // F5 (disclosure only): SKILL.md says "every .md file in the canonical
  // agents dir"; `Target` has no directory-listing primitive, so the fleet
  // below is enumerated from `journal.files` instead — a contract dropped
  // straight into `.agentic/agents/` without going through the installer is
  // invisible here, the exact hole 7b exists to close. That limitation is
  // surfaced in this check's `detail` below rather than left implicit.
  const fleet = new Set<string>();
  for (const path of Object.keys(files)) {
    const match = /^\.agentic\/agents\/([^/]+)\.md$/.exec(path);
    if (match !== null) {
      fleet.add(path);
      const name = match[1];
      // Gated on existence, same as the CLAUDE.md/AGENTS.md/PATTERNS.md
      // pointers below — a generated contract whose .claude/agents/<name>.md
      // pointer was never created must not manufacture a "no scorecard
      // entry" failure for a file that isn't there at all.
      if (name !== undefined) {
        const pointerPath = `.claude/agents/${name}.md`;
        if (await target.exists(pointerPath)) fleet.add(pointerPath);
      }
    }
  }
  for (const extra of ['CLAUDE.md', 'AGENTS.md', 'PATTERNS.md']) {
    if (await target.exists(extra)) fleet.add(extra);
  }

  const escalatedToFailure = new Set(generatedAgentPaths);
  for (const path of fleet) {
    const entry = scored[path];
    if (entry === undefined) {
      failures.push(`${path} has no scorecard entry (instruction_gate.py blocks this agent's invocation)`);
      continue;
    }
    if (escalatedToFailure.has(path)) continue; // 7a already covers staleness as a failure for these
    const currentHash = await target.sha256(path);
    if (
      entry.content_sha256 !== undefined &&
      currentHash !== undefined &&
      entry.content_sha256 !== currentHash
    ) {
      warnings.push(`${path} scorecard entry is stale (warning — invocation blocked until re-graded)`);
    }
  }

  const passed = failures.length === 0;
  const parts: string[] = [];
  if (failures.length > 0) parts.push(...failures);
  if (warnings.length > 0) parts.push(...warnings.map((w) => `warning: ${w}`));
  if (parts.length === 0) {
    parts.push(
      `${fleet.size} fleet file(s) and ${generatedAgentPaths.length} generated contract(s) scorecarded above threshold`,
    );
  }
  // F5 (disclosure only): make the journal-only enumeration visible on every
  // outcome, not just the passing path.
  parts.push(
    'fleet enumerated from the install journal (7b) — a file not journaled (e.g. an agent contract ' +
      'hand-dropped into .agentic/agents/ outside the installer) is not enumerated by this check',
  );
  return { key: 'scorecard', passed, detail: parts.join('; ') };
}

// ---------------------------------------------------------------------------
// Check 8 — Agent-registry integrity
// ---------------------------------------------------------------------------

/** A line counts as "pipe-delimited" (GFM table row candidate) when it
 *  starts with `|` after trimming leading whitespace. */
function isPipeLine(line: string): boolean {
  return line.trim().startsWith('|');
}

/** Splits a pipe-delimited line into trimmed cells, dropping a leading and
 *  trailing empty cell produced by the line's own leading/trailing `|`. Does
 *  not handle escaped `\|` inside a cell — none of the template output or
 *  the appended rows ever needs one. */
function splitRow(line: string): string[] {
  let t = line.trim();
  if (t.startsWith('|')) t = t.slice(1);
  if (t.endsWith('|')) t = t.slice(0, -1);
  return t.split('|').map((c) => c.trim());
}

function isDelimiterRow(line: string, expectedCells: number): boolean {
  if (!isPipeLine(line)) return false;
  const cells = splitRow(line);
  if (cells.length !== expectedCells) return false;
  return cells.every((c) => /^:?-+:?$/.test(c));
}

interface TableBlock {
  start: number;
  end: number; // inclusive
  headerCells: string[];
}

/** A valid GFM table block: a header row, immediately followed by a
 *  delimiter row with a matching cell count, followed by the run of
 *  consecutive pipe-delimited lines after it. A blank line, prose, or a bare
 *  `<!-- comment -->` line ends the block (none of those are pipe-delimited
 *  lines, so the scan simply stops there). */
function findTableBlocks(lines: string[]): TableBlock[] {
  const blocks: TableBlock[] = [];
  const consumed = new Array<boolean>(lines.length).fill(false);

  for (let i = 0; i < lines.length; i++) {
    if (consumed[i]) continue;
    const line = lines[i];
    if (line === undefined || !isPipeLine(line)) continue;

    const headerCells = splitRow(line);
    const delimLine = lines[i + 1];
    if (delimLine === undefined || !isDelimiterRow(delimLine, headerCells.length)) continue;

    let j = i + 2;
    while (j < lines.length) {
      const next = lines[j];
      if (next === undefined || !isPipeLine(next)) break;
      j++;
    }
    for (let k = i; k < j; k++) consumed[k] = true;
    blocks.push({ start: i, end: j - 1, headerCells });
    i = j - 1;
  }

  return blocks;
}

function extractBacktickedPaths(cell: string): string[] {
  const out: string[] = [];
  const re = /`([^`]+)`/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(cell)) !== null) {
    const p = m[1];
    if (p !== undefined) out.push(p);
  }
  return out;
}

const ROUTING_HEADER_FIRST_CELL = 'Trigger / intent';
const MARKER_CELL = '<!-- generated-agent-rows -->';
const OWNING_ASSET_HEADER = 'Owning asset';

async function checkRegistry(
  target: Target,
  files: Record<string, JournalFileEntry>,
): Promise<CheckResult> {
  const REGISTRY_PATH = '.agentic/guides/agent-registry.md';

  // "Skip only when .agentic/guides/agent-registry.md is absent from
  // journal.files (the governance/agent-registry template wasn't in the
  // preset union)."
  if (files[REGISTRY_PATH] === undefined) {
    return { key: 'registry', passed: true, detail: 'skipped — agent-registry.md is not part of this install' };
  }

  const content = await target.read(REGISTRY_PATH);
  if (content === undefined) {
    // "When it is journaled but missing from disk, that is Check 1's
    // failure, not this one — report registry as N/A and move on."
    return { key: 'registry', passed: true, detail: 'N/A — journaled but missing from disk (see manifest check)' };
  }

  const lines = content.split('\n');
  const blocks = findTableBlocks(lines);

  // 8a — the routing table is a valid GFM table, identified by its header
  // row's first cell.
  let headerLineIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line === undefined || !isPipeLine(line)) continue;
    if (splitRow(line)[0] === ROUTING_HEADER_FIRST_CELL) {
      headerLineIdx = i;
      break;
    }
  }
  if (headerLineIdx === -1) {
    return {
      key: 'registry',
      passed: false,
      detail: `8a: no routing-table header row found (first cell "${ROUTING_HEADER_FIRST_CELL}")`,
    };
  }
  const routing = blocks.find((b) => b.start === headerLineIdx);
  if (routing === undefined) {
    return {
      key: 'registry',
      passed: false,
      detail: '8a: routing-table header row is not immediately followed by a valid delimiter row — ' +
        'the whole matrix renders as prose',
    };
  }

  const failures: string[] = [];

  // 8b — marker row present, exactly once, as a table row.
  const markerLines: number[] = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line === undefined || !isPipeLine(line)) continue;
    if (splitRow(line)[0] === MARKER_CELL) markerLines.push(i);
  }
  let markerIdx: number | undefined;
  if (markerLines.length === 0) {
    failures.push(
      `8b: no marker row found (${MARKER_CELL} must appear as a table row's first cell, not a bare comment line)`,
    );
  } else if (markerLines.length > 1) {
    failures.push(`8b: marker row appears ${markerLines.length} times, expected exactly 1`);
  } else {
    markerIdx = markerLines[0];
  }

  // 8c — marker row inside the routing block.
  if (markerIdx !== undefined && (markerIdx < routing.start || markerIdx > routing.end)) {
    failures.push('8c: marker row exists but is outside the routing table block');
    markerIdx = undefined; // rows "below the marker" are undefined without this
  }

  // 8d — no orphaned rows: every pipe-delimited line belongs to some valid
  // table block.
  const inAnyBlock = (i: number): boolean => blocks.some((b) => i >= b.start && i <= b.end);
  const orphans: string[] = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line === undefined || !isPipeLine(line)) continue;
    if (!inAnyBlock(i)) orphans.push(line.trim());
  }
  if (orphans.length > 0) {
    failures.push(`8d: orphaned row(s) outside any valid table block: ${orphans.join(' | ')}`);
  }

  // Rows strictly below the marker row, within the routing block — these are
  // the rows Phase 5 step 6 appends.
  const owningIdx = routing.headerCells.findIndex((c) => c === OWNING_ASSET_HEADER);
  const rowOwningPaths = new Map<number, string[]>();
  if (markerIdx !== undefined && owningIdx !== -1) {
    for (let i = markerIdx + 1; i <= routing.end; i++) {
      const line = lines[i];
      if (line === undefined) continue;
      const cells = splitRow(line);
      rowOwningPaths.set(i, extractBacktickedPaths(cells[owningIdx] ?? ''));
    }
  }

  // 8e — every generated contract has exactly one row below the marker.
  const generatedAgentPaths = Object.entries(files)
    .filter(([path, entry]) => entry.owner === 'generated' && GENERATED_AGENT_RE.test(path))
    .map(([path]) => path);

  for (const path of generatedAgentPaths) {
    let count = 0;
    for (const paths of rowOwningPaths.values()) {
      if (paths.includes(path)) count++;
    }
    if (count === 0) {
      failures.push(`8e: ${path} has no row in the routing table (agent exists but is undiscoverable)`);
    } else if (count > 1) {
      failures.push(`8e: ${path} has ${count} rows in the routing table (expected exactly 1)`);
    }
  }

  // 8f — no stale rows: every row below the marker cites a path that exists.
  for (const [i, paths] of rowOwningPaths) {
    for (const p of paths) {
      if (!(await target.exists(p))) {
        failures.push(`8f: row at line ${i + 1} cites ${p}, which does not exist on disk`);
      }
    }
  }

  // 8g — the tail survived: after the routing block, a non-empty tail
  // containing "## Orchestration rules" as an actual level-2 heading.
  // Anchored to line start with exactly two hashes (`(?!#)` refuses a third)
  // so a deeper heading like "### Orchestration rules" — from a mis-rendered
  // or hand-edited tail — is never mistaken for the required section.
  const tailText = lines.slice(routing.end + 1).join('\n');
  if (tailText.trim().length === 0 || !/^##(?!#)\s+Orchestration rules/m.test(tailText)) {
    failures.push(
      '8g: no non-empty tail with "## Orchestration rules" after the routing table ' +
        '(registry truncated at the marker row)',
    );
  }

  const passed = failures.length === 0;
  const detail = passed
    ? `routing table valid; ${generatedAgentPaths.length} generated agent(s) routed below the marker; tail intact`
    : failures.join('; ');
  return { key: 'registry', passed, detail };
}
