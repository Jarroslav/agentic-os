/** The read-only guarantee's banned-construct pattern, single-sourced so
 *  both the file-scan test (readonly.test.ts) and the pattern's own unit
 *  test (banned-pattern.test.ts) exercise the exact same regex object.
 *
 *  Deliberately NOT under mcp/src/ — that directory is what the scan
 *  inspects, and a file there containing the literal banned strings would
 *  make the scan flag itself.
 *
 *  The process-execution half bans the unambiguous call names
 *  (execSync/execFile/execFileSync/spawn/spawnSync/fork) rather than the
 *  bare word `exec`, which would false-positive on RegExp.prototype.exec —
 *  used throughout this codebase (PRESET_URI.exec(uri), CATALOG.exec(doc.path),
 *  SKILL_RE.exec(path), etc.). The reliable signal is banning the module
 *  itself: no source file may reference the `child_process` specifier in
 *  any of its four spellings (single/double quotes, with/without the
 *  `node:` prefix), so even an aliased import
 *  (`import { execSync as run } from 'node:child_process'`) is caught by
 *  the module-specifier match even if a caller renamed the call. `vm` and
 *  `worker_threads` (also code-execution surfaces — a sandboxed `vm.Script`
 *  or a worker can run arbitrary code same as child_process can spawn it)
 *  are banned the same way, as a quoted module specifier, rather than as a
 *  bare word: `vm` collides with plausible variable/parameter names, so
 *  banning it unqualified would be noisy where banning the import/require
 *  specifier is not. `eval(`, `new Function` (with a required word boundary
 *  after `Function` so `new FunctionComponent(...)` doesn't false-positive),
 *  and a dynamic `import(` call are banned as literal in-code constructs —
 *  none of these three has a legitimate use in this read-only server, and
 *  none collides with prose the way `exec` would.
 *
 *  The write half adds `cp`/`cpSync` (recursive copy — writes a new path)
 *  and `mkdtemp`/`mkdtempSync` (creates a new directory) alongside the
 *  existing write APIs, for the same reason `mkdir` and `writeFile` are
 *  already banned: SECURITY.md and the README both claim this server
 *  "never writes", and these are two more `node:fs` entry points that would
 *  break that claim if `mcp/src/**` ever called them.
 */
export const BANNED_PATTERN =
  /\b(writeFile|writeFileSync|mkdir|mkdirSync|rm|rmSync|rmdir|rmdirSync|unlink|appendFile|createWriteStream|copyFile|copyFileSync|cp|cpSync|mkdtemp|mkdtempSync|rename|renameSync|truncate|truncateSync|symlink|symlinkSync|execSync|execFileSync|execFile|spawnSync|spawn|fork)\b|['"]\s*(?:node:)?(?:child_process|vm|worker_threads)\s*['"]|\beval\(|\bnew\s+Function\b|\bimport\(/;
