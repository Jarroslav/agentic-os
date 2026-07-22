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
 *  the module-specifier match even if a caller renamed the call.
 */
export const BANNED_PATTERN =
  /\b(writeFile|writeFileSync|mkdir|mkdirSync|rm|rmSync|rmdir|rmdirSync|unlink|appendFile|createWriteStream|copyFile|copyFileSync|rename|renameSync|truncate|truncateSync|symlink|symlinkSync|execSync|execFileSync|execFile|spawnSync|spawn|fork)\b|['"]\s*(?:node:)?child_process\s*['"]/;
