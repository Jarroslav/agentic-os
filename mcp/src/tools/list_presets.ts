import { z } from 'zod';
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { Content } from '../content.js';
import { pathToUri } from '../resources.js';
import { PRESET_PATH } from '../paths.js';

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
        'List the agentic-os role presets, each with its HITL default, ' +
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
        // JSON.parse can throw on a malformed preset file. The PresetFile
        // type above is already defensive about missing/extra *keys*; this
        // extends that same defensiveness to a malformed *parse*. One bad
        // file is skipped — the same flatMap-skip pattern used just above
        // for a missing doc — rather than failing the whole call, so a
        // single corrupt preset doesn't take every other preset down with
        // it. (The all-presets-broken case is still caught below.)
        let p: PresetFile;
        try {
          p = JSON.parse(doc.text) as PresetFile;
        } catch {
          return [];
        }
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

      // list_presets has no filter parameter — every call is "unfiltered" —
      // so zero presets can only mean the preset directory itself failed to
      // load (missing files, or every file unparseable), not a legitimate
      // empty result. Matches list_sdlc_phases's "produced nothing means
      // broken" convention.
      if (presets.length === 0) {
        return {
          isError: true,
          content: [{
            type: 'text' as const,
            text: 'No agentic-os role presets were found in the content bundle. ' +
              'plugins/agentic-os/presets/roles/ may be missing or empty.',
          }],
        };
      }

      return {
        content: [{ type: 'text' as const, text: JSON.stringify({ presets }, null, 2) }],
        structuredContent: { presets },
      };
    },
  );
}
