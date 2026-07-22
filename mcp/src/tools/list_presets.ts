import { z } from 'zod';
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { Content } from '../content.js';
import { pathToUri } from '../resources.js';

// Same shape as resources.ts's own PRESET_PATH — kept as a local copy rather
// than importing, so this tool depends only on Content.paths() (the index)
// and not on resources.ts's internals. resources.ts does not export its
// regex, and exporting it solely for this one caller would widen that
// module's public surface for no benefit to its own responsibilities.
const PRESET_PATH = /^plugins\/agentic-os\/presets\/roles\/([^/]+)\.json$/;

const outputShape = {
  presets: z.array(z.object({
    name: z.string(),
    description: z.string(),
    uri: z.string(),
    hitl_default: z.string(),
    orchestration: z.string(),
    template_count: z.number(),
    generated_count: z.number(),
    sdlc_skills: z.array(z.string()),
  })),
};

/** The preset JSON's own shape. Parsed defensively: a preset that gains a key
 *  must not break the tool, and a preset missing one must not crash it. */
type PresetFile = {
  name?: string;
  description?: string;
  templates?: unknown[];
  generated?: unknown[];
  default_hitl?: string;
  default_orchestration?: string;
  sdlc_skills?: string[];
};

export function registerListPresets(server: McpServer, content: Content): void {
  server.registerTool(
    'list_presets',
    {
      title: 'List agentic-os role presets',
      description:
        'List the agentic-os role presets (developer, qa, architect, devops, ' +
        'ba-po, pm-delivery, portfolio) with each one\'s HITL default, ' +
        'orchestration mode, and SDLC skills. Read a preset in full via its uri.',
      inputSchema: {},
      outputSchema: outputShape,
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    async () => {
      // Derived from the build-time index rather than a hardcoded list, so a
      // preset added to or removed from plugins/agentic-os/presets/roles/ is
      // reflected here automatically. The corpus is tiny, so deriving this
      // once per call (rather than caching) keeps the class simple.
      const roles = content.paths()
        .map(path => PRESET_PATH.exec(path)?.[1])
        .filter((role): role is string => role !== undefined)
        .sort();

      const presets = roles.flatMap(role => {
        const path = `plugins/agentic-os/presets/roles/${role}.json`;
        const doc = content.readDoc(path);
        if (!doc) return [];
        const p = JSON.parse(doc.text) as PresetFile;
        return [{
          name: p.name ?? role,
          description: p.description ?? '',
          uri: pathToUri(path),
          hitl_default: p.default_hitl ?? '',
          orchestration: p.default_orchestration ?? '',
          template_count: p.templates?.length ?? 0,
          generated_count: p.generated?.length ?? 0,
          sdlc_skills: p.sdlc_skills ?? [],
        }];
      });

      return {
        content: [{ type: 'text' as const, text: JSON.stringify({ presets }, null, 2) }],
        structuredContent: { presets },
      };
    },
  );
}
