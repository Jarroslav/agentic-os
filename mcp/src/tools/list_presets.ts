import { z } from 'zod';
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { Content } from '../content.js';
import { pathToUri } from '../resources.js';
import { PRESET_PATH } from '../paths.js';

const outputShape = {
  presets: z.array(z.object({
    name: z.string().describe(
      'The preset\'s own declared name. This is the identifier to pass to ' +
      "plan_install's roles argument.",
    ),
    description: z.string().describe(
      'One-line statement of the role this preset equips, from the preset file.',
    ),
    uri: z.string().describe(
      'Read this with get_document for the preset\'s full JSON, including the ' +
      'template and capability lists this summary only counts.',
    ),
    hitl_default: z.string().describe(
      'Default human-in-the-loop strictness: "strict", "gated-autonomous", or ' +
      '"autonomous". Composing roles takes the strictest of the set, so ' +
      'adding a role can only tighten this, never loosen it.',
    ),
    orchestration: z.string().describe(
      'The orchestration style this role installs by default. Composing roles ' +
      'installs every style in the union, not just one.',
    ),
    template_count: z.number().describe(
      'How many managed template files an install of this role scaffolds. A ' +
      'size indicator only — call plan_install for the actual file list.',
    ),
    generated_count: z.number().describe(
      'How many stack-specific agent contracts this role can generate. These ' +
      'are candidates filtered against the target stack at install time, so ' +
      'fewer than this may actually be written.',
    ),
    sdlc_skills: z.array(z.string()).describe(
      'agentic-sdlc pipeline skills this role enables. Empty for roles that ' +
      'do not take part in the SDLC flow.',
    ),
  })).describe(
    'Every role preset in the bundle, ordered by role name. Never empty in a ' +
    'healthy install — an empty list means the preset directory failed to ' +
    'load and is returned as an error instead.',
  ),
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
        'List the agentic-os role presets — the named role bundles ' +
        '(developer, qa, architect, devops, and so on) that decide which ' +
        'governance files an install scaffolds and how much human approval it ' +
        'demands. Use it to discover the valid role names before calling ' +
        'plan_install, or to compare what roles differ on; each entry carries ' +
        'a uri you can read for the preset in full. Takes no arguments and ' +
        'always returns every preset. Read-only and idempotent.',
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
