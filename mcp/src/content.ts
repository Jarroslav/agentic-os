import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export type Doc = { path: string; title: string; text: string };
export type Skill = {
  plugin: string;
  skill: string;
  path: string;
  title: string;
  description: string;
};

const HERE = dirname(fileURLToPath(import.meta.url));

// Under `npm run build` the server runs from dist/, with content beside it.
// Under vitest the source runs from src/, so content lives one level up.
// Both resolve to <mcp>/dist/content.
const CONTENT_ROOT = join(HERE, '..', 'dist', 'content');
const INDEX_PATH = join(HERE, '..', 'content-index.json');

const SKILL_RE = /^plugins\/([^/]+)\/skills\/([^/]+)\/SKILL\.md$/;

/** Pull `name:` and `description:` out of YAML frontmatter without a YAML dep.
 *  Skill frontmatter is flat scalar key/value only — see any SKILL.md. */
function frontmatter(text: string): Record<string, string> {
  const m = /^---\r?\n([\s\S]*?)\r?\n---/.exec(text);
  if (!m?.[1]) return {};
  const out: Record<string, string> = {};
  for (const line of m[1].split(/\r?\n/)) {
    const kv = /^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$/.exec(line);
    if (kv?.[1] && kv[2] !== undefined) out[kv[1]] = kv[2].trim();
  }
  return out;
}

function firstHeading(text: string, fallback: string): string {
  const m = /^#\s+(.+)$/m.exec(text.replace(/^---[\s\S]*?---\r?\n/, ''));
  return m?.[1]?.trim() || fallback;
}

/** A path is servable only if it is a literal key of the build-time index.
 *  Membership in that set is the whole access-control model: no path
 *  arithmetic, so traversal and absolute paths cannot express anything. */
export class Content {
  private constructor(
    private readonly docs: Map<string, Doc>,
    private readonly skills: Skill[],
  ) {}

  static async load(): Promise<Content> {
    const index: Record<string, string> = JSON.parse(
      await readFile(INDEX_PATH, 'utf8'),
    );
    const docs = new Map<string, Doc>();
    const skills: Skill[] = [];

    for (const path of Object.keys(index)) {
      if (!/\.(md|json|txt)$/.test(path)) continue;
      const text = await readFile(join(CONTENT_ROOT, path), 'utf8');
      docs.set(path, { path, title: firstHeading(text, path), text });

      const m = SKILL_RE.exec(path);
      if (m?.[1] && m[2]) {
        const fm = frontmatter(text);
        skills.push({
          plugin: m[1],
          skill: m[2],
          path,
          title: firstHeading(text, m[2]),
          description: fm['description'] ?? '',
        });
      }
    }
    skills.sort((a, b) => a.path.localeCompare(b.path));
    return new Content(docs, skills);
  }

  listSkills(): Skill[] { return this.skills; }
  readDoc(path: string): Doc | undefined { return this.docs.get(path); }
  markdownDocs(): Doc[] {
    return [...this.docs.values()].filter(d => d.path.endsWith('.md'));
  }
}

export async function loadContent(): Promise<Content> { return Content.load(); }
