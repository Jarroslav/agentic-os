import { describe, expect, it } from 'vitest';
import { BANNED_PATTERN } from './banned-pattern.js';

// Exercises the banned-construct pattern directly against a table of
// strings, independent of the file-scan test in readonly.test.ts. Testing
// the pattern this way is load-bearing: the scan test passes vacuously
// when no source file happens to be malicious, so it can't by itself prove
// the pattern catches what it claims to catch.
describe('banned pattern (process-execution half)', () => {
  const mustMatch: [string, string][] = [
    ["require('child_process')", "single-quoted require"],
    ['require("child_process")', "double-quoted require"],
    ['import { execSync } from "node:child_process"', "double-quoted node: import"],
    ["import cp from 'node:child_process'", "single-quoted node: import"],
    ['import cp from "child_process"', "double-quoted bare import"],
    ["import cp from 'child_process'", "single-quoted bare import"],
    ["import vm from 'node:vm'", "single-quoted node: vm import"],
    ['require("vm")', "double-quoted bare vm require"],
    ["import { Worker } from 'node:worker_threads'", "single-quoted node: worker_threads import"],
    ['require("worker_threads")', "double-quoted bare worker_threads require"],
    ['eval("2 + 2")', "eval( call"],
    ['new Function("return 1")', "new Function( call"],
    ["await import('./plugin.js')", "dynamic import( call"],
    ['await import("./plugin.js")', "dynamic import( call, double-quoted"],
    ['await fs.cp(src, dst, { recursive: true })', "fs.cp bare word"],
    ['await fs.cpSync(src, dst)', "fs.cpSync bare word"],
    ['await mkdtemp(join(tmpdir(), "x-"))', "mkdtemp bare word"],
    ['mkdtempSync(prefix)', "mkdtempSync bare word"],
  ];

  for (const [input, label] of mustMatch) {
    it(`flags ${label}: ${input}`, () => {
      expect(BANNED_PATTERN.test(input)).toBe(true);
    });
  }

  const mustNotMatch: [string, string][] = [
    ['const x = RE.exec(s);', "RegExp.prototype.exec on a short-named RE"],
    ['const m = PRESET_URI.exec(uri);', "RegExp.prototype.exec used elsewhere in this codebase"],
    ['import type { Worker } from "worker_threads_types";', "module specifier that merely starts with worker_threads"],
    ['const vmOptions = {};', "identifier that merely starts with vm"],
    ['const cpu = os.cpus().length;', "identifier that merely starts with cp (cpu)"],
    ['function retrieval(x) { return x; }', "identifier containing eval as a substring, not a call"],
    ['const x = new FunctionComponent();', "new FunctionComponent(...) — a real identifier, not literal `new Function`"],
    ['import { registerTool } from "./tool.js";', "an ordinary static import, no dynamic import( call"],
  ];

  for (const [input, label] of mustNotMatch) {
    it(`does not flag ${label}: ${input}`, () => {
      expect(BANNED_PATTERN.test(input)).toBe(false);
    });
  }

  // NOTE on the "comment containing spawn/fork" case the review asked for:
  // unlike `exec`, the bare words `spawn` and `fork` ARE in the banned list
  // (there is no common non-process-execution API named RegExp.prototype.spawn
  // or .fork to collide with, the way exec collides with RegExp.prototype.exec).
  // So a prose comment such as `// spawn a helper agent to fork off work`
  // legitimately DOES fire under this pattern — that's a known, accepted
  // false positive of the same shape as the historically-omitted
  // link/open/chmod/chown words (see the comment atop readonly.test.ts),
  // not a bug. It is deliberately not asserted here as a must-not-match
  // case because asserting `false` for it would be asserting the wrong
  // thing: the correct behavior for that input is `true`.
});
