import { z } from 'zod';
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { Content } from '../content.js';
import { pathToUri } from '../resources.js';

const STAGES = ['analyze', 'build', 'design', 'execute', 'operate', 'report'] as const;

const CATALOG =
  /^plugins\/agentic-qe\/skills\/qe-blueprints\/references\/catalog\/([^/]+)\/([^/]+)\.md$/;

const inputShape = {
  stage: z.enum(STAGES).optional()
    .describe('Restrict to one STLC stage.'),
};

const outputShape = {
  blueprints: z.array(z.object({
    id: z.string(), stage: z.string(), title: z.string(),
    summary: z.string(), uri: z.string(),
  })),
};

/** First non-empty paragraph after the H1, collapsed to one line and capped.
 *  Blueprints open with a one-sentence purpose statement; that is the summary. */
function summarize(text: string): string {
  const body = text.replace(/^#[^\n]*\n/, '');
  const para = body.split(/\n\s*\n/).map(s => s.trim()).find(s => s && !s.startsWith('#'));
  const line = (para ?? '').replace(/\s+/g, ' ').trim();
  return line.length > 300 ? line.slice(0, 300) + '…' : line;
}

export function registerListQeBlueprints(server: McpServer, content: Content): void {
  server.registerTool(
    'list_qe_blueprints',
    {
      title: 'List QE blueprints',
      description:
        'List the agentic-qe Quality Engineering blueprints, organized by STLC ' +
        'stage (analyze, design, build, execute, report, operate). Each entry ' +
        'carries a uri you can read for the full blueprint.',
      inputSchema: inputShape,
      outputSchema: outputShape,
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    async ({ stage }) => {
      const blueprints = content.markdownDocs().flatMap(doc => {
        const m = CATALOG.exec(doc.path);
        if (!m?.[1] || !m[2]) return [];
        if (stage && m[1] !== stage) return [];
        return [{
          id: m[2],
          stage: m[1],
          title: doc.title,
          summary: summarize(doc.text),
          uri: pathToUri(doc.path),
        }];
      }).sort((a, b) =>
        a.stage.localeCompare(b.stage) || a.id.localeCompare(b.id));

      return {
        content: [{ type: 'text' as const, text: JSON.stringify({ blueprints }, null, 2) }],
        structuredContent: { blueprints },
      };
    },
  );
}
