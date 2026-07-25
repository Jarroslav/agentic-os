import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { Content } from './content.js';

// The host's model executes these; the server never writes. The preamble is
// the only text authored here — the body is the plugin's own SKILL.md, so
// there is exactly one copy of the methodology.
const PREAMBLE = [
  'The following is an agentic-os workflow skill, delivered over MCP.',
  '',
  'The agentic-os MCP server is strictly read-only: it can hand you documents,',
  'templates, and plans, but you must perform every file write yourself with',
  'your own editing tools, so the user sees and approves each one.',
  '',
  'Wherever the skill refers to PLUGIN paths, fetch that file from this server',
  'as agentic-os://file/<plugin>/<path> instead of reading it from disk. Role',
  'presets and QE blueprints also have shorter canonical URIs —',
  'agentic-os://presets/{role} and agentic-os://qe/blueprints/{stage}/{id} —',
  'which tools and search results may return instead; both forms resolve.',
  '',
  '---',
  '',
].join('\n');

const PROMPTS: Array<{ name: string; path: string }> = [
  { name: 'agentic-init', path: 'plugins/agentic-os/skills/agentic-init/SKILL.md' },
  { name: 'agentic-doctor', path: 'plugins/agentic-os/skills/agentic-doctor/SKILL.md' },
  { name: 'agentic-upgrade', path: 'plugins/agentic-os/skills/agentic-upgrade/SKILL.md' },
  { name: 'sdlc-start', path: 'plugins/agentic-sdlc/skills/sdlc-start/SKILL.md' },
  { name: 'sdlc-task', path: 'plugins/agentic-sdlc/skills/sdlc-task/SKILL.md' },
  { name: 'qe-blueprint-scaffold', path: 'plugins/agentic-qe/skills/qe-blueprints/SKILL.md' },
];

export function registerPrompts(server: McpServer, content: Content): void {
  for (const { name, path } of PROMPTS) {
    const doc = content.readDoc(path);
    if (!doc) throw new Error(`prompt ${name}: missing ${path}`);
    const skill = content.listSkills().find(s => s.path === path);
    server.registerPrompt(
      name,
      { title: doc.title, description: skill?.description ?? doc.title },
      async () => ({
        messages: [{
          role: 'user' as const,
          content: { type: 'text' as const, text: PREAMBLE + doc.text },
        }],
      }),
    );
  }
}
