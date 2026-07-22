import { readFile, realpath, stat } from 'node:fs/promises';
import { constants } from 'node:fs';
import { access } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { isAbsolute, join, relative, resolve, sep } from 'node:path';

/** The server's second filesystem reader, and the first that accepts a
 *  caller-supplied path (a target repo the caller names for run_doctor).
 *  content.ts's access-control model — index membership — has no analogue
 *  here: there is no build-time index for someone else's repository. This
 *  class instead enforces containment explicitly, on every call, against a
 *  canonicalized root.
 *
 *  Containment rule (non-negotiable):
 *   1. An absolute `rel` is rejected outright — it never gets to see the root.
 *   2. `rel` is resolved against the canonicalized root.
 *   3. The resolved path is itself canonicalized (fs.realpath) and checked
 *      against the canonicalized root before any read. A linked path inside
 *      the target repo that ultimately resolves outside it must fail this
 *      check — that's exactly the case a comparison against the
 *      *unresolved* joined path would miss, because textually the joined
 *      path is still under root right up until the last path segment is
 *      followed.
 *   4. Any violation — absolute input, escape, missing file, unreadable
 *      file, a link that cannot be resolved — returns `undefined` (or
 *      `false` for the boolean-returning methods). Nothing here throws for
 *      an untrusted `rel`, and no error message ever carries a filesystem
 *      path.
 *
 *  The containment comparison itself is deliberately not `resolvedPath
 *  .startsWith(root)`: two sibling directories such as `/tmp/repo` and
 *  `/tmp/repo-evil` both satisfy that naive check for anything under the
 *  second one, because the string "/tmp/repo-evil" starts with the string
 *  "/tmp/repo". Comparing with `path.relative` instead — and requiring the
 *  result be neither empty, `.`, nor start with `..`/be absolute — treats
 *  root as a directory boundary rather than a string prefix.
 *
 *  Read-only: only readFile, stat, realpath, and access are used here. No
 *  write API of any kind, and no import of node:child_process — both are
 *  enforced independently by the static scan in mcp/tests/readonly.test.ts.
 */
export class Target {
  private constructor(private readonly root: string) {}

  /** Resolves and canonicalizes `root`. Rejects (a thrown Error, distinct
   *  from the undefined/false sentinels the per-file methods return) when
   *  the root does not exist or is not a directory — that failure is about
   *  the caller's own setup, not about untrusted per-file input, so it is
   *  surfaced rather than swallowed. The rejection carries no filesystem
   *  path. */
  static async open(root: string): Promise<Target> {
    let real: string;
    try {
      real = await realpath(root);
    } catch {
      throw new Error('target root does not exist');
    }
    let info;
    try {
      info = await stat(real);
    } catch {
      throw new Error('target root does not exist');
    }
    if (!info.isDirectory()) {
      throw new Error('target root is not a directory');
    }
    return new Target(real);
  }

  /** Resolves `rel` against the canonicalized root and re-canonicalizes the
   *  result, returning it only if still contained within root. Returns
   *  undefined for every kind of violation: absolute input, an escaping
   *  `..`, a path that does not exist, or a link whose ultimate target
   *  falls outside root. This is the single choke point every public
   *  method below goes through. */
  private async containedRealPath(rel: string): Promise<string | undefined> {
    if (isAbsolute(rel)) return undefined;

    const joined = resolve(this.root, rel);

    // Even before touching the filesystem, reject anything whose lexical
    // resolution already escapes root — this also catches the case where
    // realpath below would otherwise throw ENOENT on a path we can tell up
    // front is out of bounds.
    if (!isContained(this.root, joined)) return undefined;

    let real: string;
    try {
      real = await realpath(joined);
    } catch {
      return undefined;
    }

    if (!isContained(this.root, real)) return undefined;
    return real;
  }

  /** utf8 contents of `rel`, or undefined if it is missing, unreadable, out
   *  of bounds, or not a regular file. */
  async read(rel: string): Promise<string | undefined> {
    const real = await this.containedRealPath(rel);
    if (real === undefined) return undefined;
    try {
      const info = await stat(real);
      if (!info.isFile()) return undefined;
      return await readFile(real, 'utf8');
    } catch {
      return undefined;
    }
  }

  /** Lowercase hex sha256 of `rel`'s contents, or undefined under the same
   *  conditions as read(). */
  async sha256(rel: string): Promise<string | undefined> {
    const real = await this.containedRealPath(rel);
    if (real === undefined) return undefined;
    try {
      const info = await stat(real);
      if (!info.isFile()) return undefined;
      const bytes = await readFile(real);
      return createHash('sha256').update(bytes).digest('hex');
    } catch {
      return undefined;
    }
  }

  /** True only if `rel` is contained within root and refers to an existing
   *  regular file. */
  async exists(rel: string): Promise<boolean> {
    const real = await this.containedRealPath(rel);
    if (real === undefined) return false;
    try {
      const info = await stat(real);
      return info.isFile();
    } catch {
      return false;
    }
  }

  /** True only if `rel` is contained within root, refers to an existing
   *  regular file, and carries an execute bit for at least one of
   *  owner/group/other. */
  async isExecutable(rel: string): Promise<boolean> {
    const real = await this.containedRealPath(rel);
    if (real === undefined) return false;
    try {
      const info = await stat(real);
      if (!info.isFile()) return false;
      await access(real, constants.X_OK);
      return true;
    } catch {
      return false;
    }
  }
}

/** True when `candidate` is root itself or a descendant of it. Deliberately
 *  not `candidate.startsWith(root)` — that also matches an unrelated
 *  sibling directory whose name happens to extend root's as a string (e.g.
 *  root `/tmp/repo` against sibling `/tmp/repo-evil`). path.relative gives
 *  the actual directory-boundary-aware answer: anything outside root
 *  relativizes to something starting with `..` or to an absolute path (on
 *  Windows, crossing drives). */
function isContained(root: string, candidate: string): boolean {
  if (candidate === root) return true;
  const rel = relative(root, candidate);
  if (rel === '') return true;
  if (rel.startsWith('..')) return false;
  if (isAbsolute(rel)) return false;
  // Belt-and-suspenders alongside the relative() check above: candidate
  // must literally begin with root + separator once we know it isn't a
  // `..`-prefixed or absolute relative path.
  return candidate === root || candidate.startsWith(root + sep) || candidate.startsWith(join(root, rel));
}
