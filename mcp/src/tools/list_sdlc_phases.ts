import { z } from 'zod';
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { Content } from '../content.js';
import { pathToUri } from '../resources.js';

const SOURCE = 'plugins/agentic-sdlc/skills/sdlc-pipeline/SKILL.md';

const outputShape = {
  phases: z.array(z.object({
    number: z.number().describe(
      'Phase number, starting at 0. Phases run in this order.',
    ),
    name: z.string().describe(
      'The phase name, e.g. "Requirements" or "Final code review".',
    ),
    skippable: z.string().describe(
      'Free-text skip condition copied verbatim from the pipeline table — ' +
      'deliberately a string, not a boolean, because the real answers are ' +
      'conditional: "no", "yes", "per phase_set" (derived from the work-type ' +
      'classification), or "never once Phase 7 is reached". Do not coerce it ' +
      'to a boolean; a phase marked "per phase_set" is skippable only for ' +
      'some kinds of work.',
    ),
    gates: z.array(z.string()).describe(
      'Judgment gates this phase raises, as dotted ids (e.g. ' +
      '"spec.approved", "qa.drift"). Each is a point where the pipeline stops ' +
      'for a human decision. Empty means the phase runs to completion without ' +
      'raising one.',
    ),
  })).describe('Every pipeline phase, in execution order from phase 0.'),
  source_uri: z.string().describe(
    'URI of the pipeline skill this map was parsed from. Read it with ' +
    'get_document for what each phase actually does — this tool returns only ' +
    'the phase/gate skeleton.',
  ),
};

type Phase = { number: number; name: string; skippable: string; gates: string[] };

/** Parse the `## Phase map` GFM table. Upstream markdown is the source of
 *  truth, so a phase added there appears here with no code change — and the
 *  contract tests assert the shape so a restructure fails loudly. */
export function parsePhaseMap(markdown: string): Phase[] {
  const section = markdown.split(/^##\s+Phase map\s*$/m)[1];
  if (!section) return [];

  const phases: Phase[] = [];
  let sawSeparatorRow = false;
  for (const line of section.split('\n')) {
    if (!line.startsWith('|')) {
      if (phases.length > 0) break;   // table ended
      continue;
    }
    const cells = line.split('|').slice(1, -1).map(c => c.trim());
    if (cells.length < 4) continue;

    // A GFM separator row (e.g. `|---|:--|--:|`) marks the boundary between
    // a header and its body. The *first* one belongs to this table's own
    // header and is skipped below along with it. A *second* one — reached
    // with no blank line in between, as when a second table immediately
    // follows in the same section — means a new table has begun; stop here
    // rather than absorbing its rows as if they were more phases.
    const isSeparatorRow = cells.every(c => /^:?-+:?$/.test(c));
    if (isSeparatorRow) {
      if (sawSeparatorRow) break;
      sawSeparatorRow = true;
      continue;
    }

    const num = Number(cells[0]);
    if (!Number.isInteger(num)) continue;          // header row

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
        'List the agentic-sdlc pipeline phases in execution order, with each ' +
        "phase's skip condition and the judgment gates it raises — the points " +
        'where the flow must stop for a human decision. Use it to drive the ' +
        'SDLC flow yourself in a host that cannot run the plugin, or to answer ' +
        'what happens when in the pipeline. Returns the phase and gate ' +
        'skeleton only; read source_uri for what each phase actually does. ' +
        'Takes no arguments. Read-only and idempotent.',
      inputSchema: {},
      outputSchema: outputShape,
      annotations: {
        readOnlyHint: true,
        openWorldHint: false,
        idempotentHint: true,
        destructiveHint: false,
      },
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
      const phases = parsePhaseMap(doc.text);
      // list_sdlc_phases has no filter parameter, so — same convention now
      // applied to list_presets and list_qe_blueprints's unfiltered case —
      // an empty result here can only mean the parser broke, not a
      // legitimate empty answer.
      if (phases.length === 0) {
        return {
          isError: true,
          content: [{
            type: 'text' as const,
            text: `Could not parse the phase-map table out of the SDLC pipeline ` +
              `skill (${SOURCE}). The document is present, but its "## Phase map" ` +
              `section is missing or its table could not be read.`,
          }],
        };
      }
      const out = { phases, source_uri: pathToUri(SOURCE) };
      return {
        content: [{ type: 'text' as const, text: JSON.stringify(out, null, 2) }],
        structuredContent: out,
      };
    },
  );
}
