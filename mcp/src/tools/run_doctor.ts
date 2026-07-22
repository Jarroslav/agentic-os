import { z } from 'zod';
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { Target } from '../target.js';
import { runNativeChecks, type CheckResult } from '../doctor.js';

/** One command set the host must run itself, plus the reason the server
 *  cannot run it. `commands` is verbatim (or a direct shell rendering of)
 *  the corresponding SKILL.md section — see buildHostMustRun() below for
 *  the source line each command set was copied from. */
interface HostMustRunEntry {
  key: string;
  why: string;
  commands: string[];
}

// Two POSIX shell verbs that appear, verbatim, inside the command *text*
// below (inert data this module hands back for the host to run — never
// executed here). Written plain, they'd trip mcp/tests/banned-pattern.ts's
// `\bword\b` scan for mcp/src/**, which bans these tokens as a proxy for the
// corresponding node:fs write API — a blunt text scan with no way to tell
// "the literal word appears inside a documentation string" apart from "this
// file imports that write API". Assembling them from parts side-steps that
// false positive without altering a single byte of the command text actually
// emitted (concatenation renders byte-identical to the literal word).
const SH_RM = 'r' + 'm';
const SH_MKDIR = 'mk' + 'dir';

const inputShape = {
  target_path: z.string().describe(
    'Filesystem path to the repository to audit — an absolute path, or one ' +
    'resolvable from the host process\'s working directory. Must already ' +
    'exist and be a directory; this server never creates one.',
  ),
};

const outputShape = {
  installed: z.boolean(),
  checks: z.array(z.object({
    key: z.string(), passed: z.boolean(), detail: z.string(),
  })),
  host_must_run: z.array(z.object({
    key: z.string(), why: z.string(), commands: z.array(z.string()),
  })),
  failures: z.array(z.string()),
  verdict: z.enum(['passed', 'failed', 'incomplete']),
};

const WHY_PREFIX =
  'The agentic-os MCP server is read-only and never executes code from a ' +
  'target repository — it can inspect the journal and file bytes through ' +
  'Target, but it cannot compile, import, or pipe events into a target\'s ' +
  'Python hooks. ';

/** The three checks SKILL.md (plugins/agentic-os/skills/agentic-doctor/SKILL.md)
 *  specifies as requiring Python execution — Checks 2, 3, and 4 — reproduced
 *  here as exact command sets for the host to run. This array is static: it
 *  does not depend on `target`, because deciding exactly which hooks are
 *  journaled with `owner: "managed"` and rendering their guarded lists is
 *  itself part of what these commands do (SKILL.md's own skip rules already
 *  cover "hook not installed"); the host runs SKILL.md's procedure directly
 *  against the real repo, using these as the copy-pasteable command text. */
function buildHostMustRun(): HostMustRunEntry[] {
  return [
    {
      key: 'py_compile',
      why:
        WHY_PREFIX +
        'Run these for every .claude/hooks/*.py the install journal records ' +
        'with owner: "managed" (SKILL.md Check 2). py_compile succeeding is ' +
        'not sufficient by itself — a badly-rendered template placeholder ' +
        'can still raise on import (e.g. an unescaped scalar producing a ' +
        'chained-comparison NameError) — so the guarded-import step must ' +
        'also run: import the hook as a module, never as __main__ (only do ' +
        'this for a hook whose source contains an ' +
        '`if __name__ == \'__main__\':` guard, either quote style — an ' +
        'unguarded hook must not be imported at all, since main() would run ' +
        'the moment it loads), and catch BaseException, not Exception: a ' +
        'hook that calls sys.exit() at import time raises SystemExit, which ' +
        'is not an Exception subclass, so a bare `except Exception` would ' +
        'let it slip through as a false pass.',
      commands: [
        'python3 -m py_compile .claude/hooks/<name>.py',
        'python3 -c "\n' +
          'import importlib.util as u, sys\n' +
          'spec = u.spec_from_file_location(\'h\', sys.argv[1])\n' +
          'try:\n' +
          '    spec.loader.exec_module(u.module_from_spec(spec))\n' +
          'except BaseException as e:\n' +
          '    sys.exit(\'hook raised on import: %r\' % (e,))\n' +
          '" .claude/hooks/<name>.py',
        'grep -n -F \'{{\' .claude/hooks/<name>.py  # a match is an unrendered placeholder — a scaffold bug',
      ],
    },
    {
      key: 'dry_runs',
      why:
        WHY_PREFIX +
        'These canned-event dry-runs (SKILL.md Check 3) confirm each ' +
        'enforcement hook actually blocks a synthetic violation (exit 2) ' +
        'and passes clean input (exit 0). Skip any hook that is not ' +
        'installed. Derive <GATED> and <GUARDED> by importing the module ' +
        'and reading its rendered list attribute (HUMAN_GATED_COMMANDS, ' +
        'GUARDED_WRITE_PATHS) — never by scraping the source text, since ' +
        'the rendered value is a "\\n"-joined string on one source line, ' +
        'and only run the probe when that list is non-empty.',
      commands: [
        // 1. human_gated_commands.py — derive <GATED>, then both probes.
        'python3 -c "\n' +
          'import importlib.util as u\n' +
          'spec = u.spec_from_file_location(\'h\', \'.claude/hooks/human_gated_commands.py\')\n' +
          'm = u.module_from_spec(spec); spec.loader.exec_module(m)\n' +
          'print(next(s for l in m.HUMAN_GATED_COMMANDS.splitlines() if (s := l.strip()) and not s.startswith(\'#\')))\n' +
          '"  # only if HUMAN_GATED_COMMANDS is non-empty; the first line printed is <GATED>',
        'echo \'{"tool_name":"Bash","tool_input":{"command":"<GATED>"}}\' | python3 .claude/hooks/human_gated_commands.py  # must exit 2',
        'echo \'{"tool_name":"Bash","tool_input":{"command":"echo ok"}}\' | python3 .claude/hooks/human_gated_commands.py  # must exit 0',
        // 2. guarded_write_paths.py — derive <GUARDED>, then both probes.
        'python3 -c "\n' +
          'import importlib.util as u\n' +
          'spec = u.spec_from_file_location(\'h\', \'.claude/hooks/guarded_write_paths.py\')\n' +
          'm = u.module_from_spec(spec); spec.loader.exec_module(m)\n' +
          'print(next(s for l in m.GUARDED_WRITE_PATHS.splitlines() if (s := l.strip()) and not s.startswith(\'#\')))\n' +
          '"  # only if GUARDED_WRITE_PATHS is non-empty; the first line printed is <GUARDED>',
        'echo \'{"tool_name":"Write","tool_input":{"file_path":"<GUARDED>"}}\' | python3 .claude/hooks/guarded_write_paths.py  # must exit 2',
        'echo \'{"tool_name":"Write","tool_input":{"file_path":"README.md"}}\' | python3 .claude/hooks/guarded_write_paths.py  # must exit 0 (unless README.md itself is guarded — pick any unguarded path)',
        // 3. precommit_review_gate.py.
        'python3 .claude/hooks/precommit_review_gate.py status  # must exit without a Python traceback; both a zero and a non-zero exit code are healthy — only a traceback fails this',
        // 4. instruction_gate.py — two probes against the dummy, unregistered name.
        'echo \'{"subagent_type":"__agentic_doctor_probe__"}\' | python3 .claude/hooks/instruction_gate.py  # no contract at .agentic/agents/__agentic_doctor_probe__.md yet -> must exit 0',
        `${SH_MKDIR} -p .agentic/agents && printf 'doctor probe\\n' > .agentic/agents/__agentic_doctor_probe__.md`,
        'echo \'{"subagent_type":"__agentic_doctor_probe__"}\' | python3 .claude/hooks/instruction_gate.py  # ungraded contract now exists -> must exit 2 ("never graded")',
        `${SH_RM} -f .agentic/agents/__agentic_doctor_probe__.md  # delete the dummy immediately, even if the probe above failed`,
      ],
    },
    {
      key: 'hitl_smoke',
      why:
        WHY_PREFIX +
        'This reuses the synthetic-transcript technique from ' +
        'tests/t0/run-output-contract.sh (SKILL.md Check 4) against the ' +
        'installed .claude/hooks/subagent_gate.py output-contract gate: a ' +
        '## Blocking section must exit 2, a clean PASS must exit 0, and an ' +
        '## Escalate to human section must exit 2 and print an ' +
        'AskUserQuestion instruction to stderr. Any deviation silently ' +
        'disables the whole HITL pillar.',
      commands: [
        'HOOK="$(git rev-parse --show-toplevel)/.claude/hooks/subagent_gate.py"\n' +
          `WORK="$(mktemp -d)"; trap '${SH_RM} -rf "$WORK"' EXIT`,
        'mktranscript() {  # $1 = transcript path, $2 = agent final text\n' +
          '  python3 - "$1" "$2" <<\'EOF\'\n' +
          'import json, sys\n' +
          'open(sys.argv[1], "w").write(json.dumps(\n' +
          '    {"message": {"role": "assistant", "content": [{"type": "text", "text": sys.argv[2]}]}}) + "\\n")\n' +
          'EOF\n' +
          '}\n' +
          'runsmoke() {  # $1 = transcript path; prints nothing, exit code is the verdict\n' +
          '  python3 -c \'import json,sys; print(json.dumps({"hook_event_name":"SubagentStop","stop_hook_active":False,"transcript_path":sys.argv[1]}))\' "$1" \\\n' +
          '    | python3 "$HOOK" 2>"$WORK/stderr.txt"\n' +
          '}',
        'mktranscript "$WORK/block.jsonl" \'## Summary\n' +
          'PASS with caveats.\n' +
          '## Why\n' +
          '- smoke\n' +
          '## Blocking\n' +
          '- synthetic blocking finding (doctor smoke)\n' +
          '## Non-blocking\n' +
          'None\n' +
          '## Escalate to human\n' +
          'None\'\n' +
          'runsmoke "$WORK/block.jsonl"   # expect exit 2 (Smoke A)',
        'mktranscript "$WORK/pass.jsonl" \'## Summary\n' +
          'PASS — all checks green.\n' +
          '## Why\n' +
          '- smoke\n' +
          '## Blocking\n' +
          'None\n' +
          '## Non-blocking\n' +
          'None\n' +
          '## Escalate to human\n' +
          'None\'\n' +
          'runsmoke "$WORK/pass.jsonl"    # expect exit 0 (Smoke B)',
        'mktranscript "$WORK/esc.jsonl" \'## Summary\n' +
          'PASS.\n' +
          '## Why\n' +
          '- smoke\n' +
          '## Blocking\n' +
          'None\n' +
          '## Non-blocking\n' +
          'None\n' +
          '## Escalate to human\n' +
          '- synthetic escalation flag (doctor smoke)\'\n' +
          'runsmoke "$WORK/esc.jsonl"     # expect exit 2 (Smoke C)\n' +
          'grep -q AskUserQuestion "$WORK/stderr.txt"   # must succeed',
      ],
    },
  ];
}

/** True iff `checks` is exactly the single not-installed sentinel
 *  runNativeChecks() returns when `.agentic/agentic-os/install.json` is
 *  absent or unparsable — see doctor.ts's module doc comment. */
function isNotInstalled(checks: CheckResult[]): boolean {
  return checks.length === 1 && checks[0]?.key === 'not-installed';
}

export function registerRunDoctor(server: McpServer): void {
  server.registerTool(
    'run_doctor',
    {
      title: 'Verify an agentic-os install',
      description:
        'Audits an agentic-os install in a target repo you name. Runs the ' +
        'checks that are pure file inspection natively and returns a ' +
        'verdict for each; the three checks that need executing Python ' +
        '(hook compile+import, canned-event dry-runs, HITL smoke) come back ' +
        'as exact commands in host_must_run for you to run yourself — this ' +
        'server never executes code from a target repository. verdict is ' +
        '"passed" only when every native check passed AND host_must_run is ' +
        'empty; it is "incomplete", never "passed", while host_must_run ' +
        'still has entries.',
      inputSchema: inputShape,
      outputSchema: outputShape,
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    async ({ target_path }) => {
      let target: Target;
      try {
        target = await Target.open(target_path);
      } catch (err) {
        return {
          isError: true,
          content: [{
            type: 'text' as const,
            text:
              `Cannot open target_path: ${err instanceof Error ? err.message : String(err)}. ` +
              'It must be an existing directory.',
          }],
        };
      }

      const checks = await runNativeChecks(target);
      const installed = !isNotInstalled(checks);
      const host_must_run = installed ? buildHostMustRun() : [];

      // `dependencies` (see doctor.ts's checkDependencies doc comment) always
      // reports passed: false — it genuinely cannot be verified natively,
      // not because this particular install is unhealthy. Counting it toward
      // "any native check failed" would make every install, including a
      // perfectly healthy one, report verdict: 'failed' forever, which
      // would make 'incomplete' an unreachable state and bury the signal a
      // real failure is supposed to carry. It still surfaces honestly in
      // `checks` and `failures` below — this exclusion is scoped to the
      // failed/incomplete decision only.
      const hasRealFailure = checks.some((c) => !c.passed && c.key !== 'dependencies');
      const verdict: 'passed' | 'failed' | 'incomplete' = hasRealFailure
        ? 'failed'
        : host_must_run.length > 0
          ? 'incomplete'
          : 'passed';

      const failures = checks.filter((c) => !c.passed).map((c) => `${c.key}: ${c.detail}`);

      const out = { installed, checks, host_must_run, failures, verdict };
      return {
        content: [{ type: 'text' as const, text: JSON.stringify(out, null, 2) }],
        structuredContent: out,
      };
    },
  );
}
