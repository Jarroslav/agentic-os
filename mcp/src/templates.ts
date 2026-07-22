import { TEMPLATE_ROOT } from './paths.js';

/** Where each template-ID prefix looks for its file, in order.
 *  Mirrors the "Template IDs" table in
 *  plugins/agentic-os/templates/VARIABLES.md — that document is the spec;
 *  this is its executable form, and templates.test.ts asserts the two agree
 *  by resolving every id every preset references. */
const DIRS: Record<string, string[]> = {
  hooks: ['hooks/claude', 'hooks'],
  githooks: ['githooks'],
  scripts: ['scripts'],
  governance: ['governance'],
  policy: ['policy'],
  guides: ['guides/standards'],
  agents: ['agents/core', 'agents/qa'],
  commands: ['commands/core'],
  sdlc: ['sdlc'],
};

const EXTS = ['', '.md', '.py', '.json', '.sh',
              '.md.tmpl', '.py.tmpl', '.json.tmpl', '.sh.tmpl'];

/** Ids whose file name is not derivable from the id by any general rule. */
const EXCEPTIONS: Record<string, string> = {
  'governance/claude-section': 'governance/CLAUDE.section.md.tmpl',
  'hooks/session-bootstrap': 'hooks/claude/session_start_bootstrap.py.tmpl',
};

/** Resolve a preset template id to its repo-relative bundle path.
 *  Lookup is case-insensitive: ids are kebab-case but several files are
 *  upper-case (AGENTS.md.tmpl, PATTERNS.md.tmpl), and matching exact-case
 *  would silently pass on a case-insensitive filesystem and fail on Linux. */
export function resolveTemplateId(
  id: string,
  paths: string[],
): string | undefined {
  const byLower = new Map<string, string>();
  for (const p of paths) if (p.startsWith(TEMPLATE_ROOT)) byLower.set(p.toLowerCase(), p);

  const exception = EXCEPTIONS[id];
  if (exception) return byLower.get((TEMPLATE_ROOT + exception).toLowerCase());

  const slash = id.indexOf('/');
  if (slash < 1) return undefined;
  const prefix = id.slice(0, slash);
  const name = id.slice(slash + 1);
  if (!name) return undefined;

  for (const dir of DIRS[prefix] ?? []) {
    for (const stem of [name, name.replace(/-/g, '_')]) {
      for (const ext of EXTS) {
        const hit = byLower.get(`${TEMPLATE_ROOT}${dir}/${stem}${ext}`.toLowerCase());
        if (hit) return hit;
      }
    }
  }
  return undefined;
}
