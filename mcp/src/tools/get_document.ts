import { z } from 'zod';
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { Content } from '../content.js';
import { uriToPath } from '../resources.js';

const DEFAULT_MAX = 40_000;

const inputShape = {
  uri: z.string().describe(
    'An agentic-os:// URI, e.g. agentic-os://skills/agentic-sdlc/qa-gates ' +
    'or agentic-os://file/agentic-os/presets/roles/qa.json. ' +
    'Get these from search_methodology.',
  ),
  max_chars: z.number().int().min(200).max(200_000).default(DEFAULT_MAX)
    .describe('Truncate the body at this many characters.'),
};

const outputShape = {
  uri: z.string(), title: z.string(), text: z.string(),
  truncated: z.boolean(), total_chars: z.number(),
};

export function registerGetDocument(server: McpServer, content: Content): void {
  server.registerTool(
    'get_document',
    {
      title: 'Get an agentic-os document',
      description:
        'Fetch one agentic-os methodology document by its agentic-os:// URI. ' +
        'Long documents are truncated; the truncated flag says so.',
      inputSchema: inputShape,
      outputSchema: outputShape,
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    async ({ uri, max_chars }) => {
      const path = uriToPath(uri);
      const doc = path ? content.readDoc(path) : undefined;
      if (!doc) {
        return {
          isError: true,
          content: [{
            type: 'text' as const,
            text: `No document at ${uri}. Use search_methodology to find valid URIs.`,
          }],
        };
      }
      const truncated = doc.text.length > max_chars;
      const out = {
        uri,
        title: doc.title,
        text: truncated ? doc.text.slice(0, max_chars) : doc.text,
        truncated,
        total_chars: doc.text.length,
      };
      return {
        content: [{ type: 'text' as const, text: out.text }],
        structuredContent: out,
      };
    },
  );
}
