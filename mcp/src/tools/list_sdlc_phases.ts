import { z } from 'zod';
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { Content } from '../content.js';
import { pathToUri } from '../resources.js';

const SOURCE = 'plugins/agentic-sdlc/skills/sdlc-pipeline/SKILL.md';

const outputShape = {
  phases: z.array(z.object({
    number: z.number(), name: z.string(),
    skippable: z.string(), gates: z.array(z.string()),
  })),
  source_uri: z.string(),
};

type Phase = { number: number; name: string; skippable: string; gates: string[] };

/** Parse the `## Phase map` GFM table. Upstream markdown is the source of
 *  truth, so a phase added there appears here with no code change — and the
 *  contract tests assert the shape so a restructure fails loudly. */
export function parsePhaseMap(markdown: string): Phase[] {
  const section = markdown.split(/^##\s+Phase map\s*$/m)[1];
  if (!section) return [];

  const phases: Phase[] = [];
  for (const line of section.split('\n')) {
    if (!line.startsWith('|')) {
      if (phases.length > 0) break;   // table ended
      continue;
    }
    const cells = line.split('|').slice(1, -1).map(c => c.trim());
    if (cells.length < 4) continue;
    const num = Number(cells[0]);
    if (!Number.isInteger(num)) continue;          // header and separator rows

    const gateCell = cells[3] ?? '';
    const gates = [...gateCell.matchAll(/`([^`]+)`/g)]
      .map(m => m[1]!)
      .filter(g => /^[a-z][a-z-]*\.[a-z][a-z-]*$/.test(g));

    phases.push({
      number: num,
      name: cells[1] ?? '',
      skippable: cells[2] ?? '',
      gates,
    });
  }
  return phases;
}

export function registerListSdlcPhases(server: McpServer, content: Content): void {
  server.registerTool(
    'list_sdlc_phases',
    {
      title: 'List SDLC pipeline phases',
      description:
        'List the agentic-sdlc pipeline phases in order, with which are ' +
        'skippable and which judgment gates each one raises. Use this to drive ' +
        'the SDLC flow in a host that cannot run the plugin.',
      inputSchema: {},
      outputSchema: outputShape,
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    async () => {
      const doc = content.readDoc(SOURCE);
      if (!doc) {
        return {
          isError: true,
          content: [{
            type: 'text' as const,
            text: `The SDLC pipeline skill is missing from the bundle (${SOURCE}).`,
          }],
        };
      }
      const out = { phases: parsePhaseMap(doc.text), source_uri: pathToUri(SOURCE) };
      return {
        content: [{ type: 'text' as const, text: JSON.stringify(out, null, 2) }],
        structuredContent: out,
      };
    },
  );
}
