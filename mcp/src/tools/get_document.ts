import { z } from 'zod';
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { Content } from '../content.js';
import { uriToPath } from '../resources.js';
import { truncateCodePoints } from '../text.js';

const DEFAULT_MAX = 40_000;

const inputShape = {
  uri: z.string().describe(
    'An agentic-os:// URI, e.g. agentic-os://skills/agentic-sdlc/qa-gates ' +
    'or agentic-os://file/agentic-sdlc/agents/guide-sync.md. ' +
    'Get these from search_methodology.',
  ),
  // Ceiling lowered from 200_000 to 50_000: the largest real document in the
  // corpus is ~40 KB, so a 200 KB ceiling was five times what the content
  // can ever produce, and the body is already carried twice per response
  // (content[0].text and structuredContent.text, per MCP spec compliance).
  max_chars: z.number().int().min(200).max(50_000).default(DEFAULT_MAX)
    .describe(
      'Truncate the body at this many Unicode code points (not UTF-16 ' +
      'code units — astral-plane characters such as emoji count as one).',
    ),
};

const outputShape = {
  uri: z.string().describe('The requested URI, echoed back unchanged.'),
  title: z.string().describe(
    "The document's first markdown heading, or its path within the content " +
    'bundle when it has no heading.',
  ),
  text: z.string().describe(
    'The document body — complete, or cut to max_chars code points when ' +
    'truncated is true.',
  ),
  truncated: z.boolean().describe(
    'true when the body was cut because it exceeded max_chars. There is no ' +
    'offset or paging parameter: re-request with a larger max_chars to get ' +
    'the rest.',
  ),
  total_chars: z.number().describe(
    'Length of the complete, untruncated body in Unicode code points — the ' +
    'same unit max_chars is measured in, so total_chars > max_chars is ' +
    'precisely the condition that sets truncated.',
  ),
};

export function registerGetDocument(server: McpServer, content: Content): void {
  server.registerTool(
    'get_document',
    {
      title: 'Get an agentic-os document',
      description:
        'Fetch the full text of one agentic-os methodology document, named by ' +
        'its exact agentic-os:// URI. Use it to read a document you have ' +
        'already located — normally via search_methodology, whose every result ' +
        'carries the URI to pass here. It resolves exact URIs only and cannot ' +
        'search, so a guessed URI returns an error rather than a near match. ' +
        'Read-only and idempotent: nothing is ever written, and the same URI ' +
        'returns the same document. A body longer than max_chars comes back ' +
        'cut at a code-point boundary with truncated set and total_chars ' +
        'giving the full length.',
      inputSchema: inputShape,
      outputSchema: outputShape,
      annotations: {
        readOnlyHint: true,
        openWorldHint: false,
        idempotentHint: true,
        destructiveHint: false,
      },
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
      // Slicing by UTF-16 code unit (`doc.text.slice(0, max_chars)`) can cut
      // a surrogate pair in half — the corpus really does contain astral
      // characters (e.g. emoji in agents/guide-sync.md) — and an unpaired
      // surrogate is malformed text once handed back to the calling model.
      // truncateCodePoints() (mcp/src/text.ts) slices by code point instead,
      // so it can never land inside a pair, and hands back the input's total
      // code-point count as `total` from that same pass — so total_chars
      // below is free, rather than a second `Array.from(doc.text)` just to
      // count it again. Materializing the code-point array is O(n), but the
      // corpus tops out around 40 KB, so the cost is negligible; total_chars
      // and max_chars are both counted in this same code-point unit so the
      // truncated flag stays meaningful.
      const { text, truncated, total } = truncateCodePoints(doc.text, max_chars);
      const out = {
        uri,
        title: doc.title,
        text,
        truncated,
        total_chars: total,
      };
      return {
        content: [{ type: 'text' as const, text: out.text }],
        structuredContent: out,
      };
    },
  );
}
