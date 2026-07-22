import { z } from 'zod';
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { Content, Doc } from '../content.js';
import { pathToUri } from '../resources.js';

const PLUGINS = ['agentic-os', 'agentic-sdlc', 'agentic-qe'] as const;

const inputShape = {
  query: z.string().min(1).describe('Words to search for, e.g. "write scope enforcement".'),
  plugin: z.enum(PLUGINS).optional().describe('Restrict results to one plugin.'),
  limit: z.number().int().min(1).max(25).default(8)
    .describe('Maximum results to return.'),
};

const outputShape = {
  results: z.array(z.object({
    uri: z.string(), title: z.string(), plugin: z.string(),
    score: z.number(), snippet: z.string(),
  })),
};

const tokenize = (s: string): string[] =>
  s.toLowerCase().match(/[a-z0-9]{2,}/g) ?? [];

function pluginOf(path: string): string {
  return /^plugins\/([^/]+)\//.exec(path)?.[1] ?? '';
}

/** Term-frequency scoring with a title boost. Deliberately dependency-free:
 *  the corpus is ~200 small files, so an index is not worth the weight. */
function score(doc: Doc, terms: string[]): number {
  const body = doc.text.toLowerCase();
  const title = doc.title.toLowerCase();
  let total = 0;
  for (const term of terms) {
    let hits = 0, from = 0, at: number;
    while ((at = body.indexOf(term, from)) !== -1) { hits++; from = at + term.length; }
    if (hits === 0) return 0;          // every term must appear — AND, not OR
    total += Math.log1p(hits) + (title.includes(term) ? 3 : 0);
  }
  return total;
}

function snippet(doc: Doc, term: string): string {
  const at = doc.text.toLowerCase().indexOf(term);
  if (at === -1) return doc.text.slice(0, 200).trim();
  return doc.text.slice(Math.max(0, at - 80), at + 160).replace(/\s+/g, ' ').trim();
}

export function registerSearchMethodology(server: McpServer, content: Content): void {
  server.registerTool(
    'search_methodology',
    {
      title: 'Search agentic-os methodology',
      description:
        'Search the agentic-os governance, agentic-sdlc pipeline, and agentic-qe ' +
        'blueprint documentation. Use this first to locate the right document, ' +
        'then fetch it with get_document.',
      inputSchema: inputShape,
      outputSchema: outputShape,
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    async ({ query, plugin, limit }) => {
      const terms = tokenize(query);
      const results = terms.length === 0 ? [] : content.markdownDocs()
        .filter(d => !plugin || pluginOf(d.path) === plugin)
        .map(d => ({ doc: d, score: score(d, terms) }))
        .filter(r => r.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, limit)
        .map(r => ({
          uri: pathToUri(r.doc.path),
          title: r.doc.title,
          plugin: pluginOf(r.doc.path),
          score: Number(r.score.toFixed(3)),
          snippet: snippet(r.doc, terms[0]!),
        }));

      return {
        content: [{ type: 'text' as const, text: JSON.stringify({ results }, null, 2) }],
        structuredContent: { results },
      };
    },
  );
}
