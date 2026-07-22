import { z } from 'zod';
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { Content } from '../content.js';
import { pathToUri } from '../resources.js';
import { PRESET_PATH } from '../paths.js';
import { resolveTemplateId } from '../templates.js';

/** Strictest wins, most-restrictive first. */
const HITL_ORDER = ['strict', 'gated-autonomous', 'autonomous'];

const inputShape = {
  roles: z.array(z.string()).min(1)
    .describe('Role preset names to compose, e.g. ["developer","qa"]. ' +
              'Get valid names from list_presets.'),
};

const outputShape = {
  roles: z.array(z.string()),
  hitl_default: z.string(),
  orchestration_installed: z.array(z.string()),
  orchestration_default: z.string(),
  files: z.array(z.object({
    template_id: z.string(), source_uri: z.string(), owner: z.string(),
  })),
  generated_candidates: z.array(z.string()),
  sdlc_skills: z.array(z.string()),
  follow_ups: z.array(z.string()),
};

type Preset = {
  name?: string; templates?: string[]; generated?: string[];
  sdlc_skills?: string[];
  default_hitl?: string; default_orchestration?: string;
};

export function registerPlanInstall(server: McpServer, content: Content): void {
  server.registerTool(
    'plan_install',
    {
      title: 'Plan an agentic-os install',
      description:
        'Given one or more role presets, return the ordered list of files to ' +
        'scaffold into a repo, each with a uri to read its template. Unions the ' +
        'roles, applies strictest-HITL-wins, and installs every orchestration ' +
        'style in the union. generated_candidates still need filtering against ' +
        'the target stack. Returns a plan only — you perform the writes yourself.',
      inputSchema: inputShape,
      outputSchema: outputShape,
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    async ({ roles }) => {
      const paths = content.paths();
      const presets: Preset[] = [];
      const missing: string[] = [];

      for (const role of roles) {
        const path = `plugins/agentic-os/presets/roles/${role}.json`;
        const doc = PRESET_PATH.test(path) ? content.readDoc(path) : undefined;
        if (!doc) { missing.push(role); continue; }
        try { presets.push(JSON.parse(doc.text) as Preset); }
        catch { missing.push(role); }
      }

      if (missing.length) {
        return {
          isError: true,
          content: [{
            type: 'text' as const,
            text: `Unknown role preset(s): ${missing.join(', ')}. ` +
                  `Call list_presets for the valid names.`,
          }],
        };
      }

      const ids = [...new Set(presets.flatMap(p => p.templates ?? []))].sort();
      const files: Array<{ template_id: string; source_uri: string; owner: string }> = [];
      const follow_ups: string[] = [];

      for (const id of ids) {
        const path = resolveTemplateId(id, paths);
        if (!path) { follow_ups.push(`Template "${id}" has no file in the bundle.`); continue; }
        files.push({ template_id: id, source_uri: pathToUri(path), owner: 'managed' });
      }

      // Strictest wins: strict > gated-autonomous > autonomous.
      const hitl = HITL_ORDER.find(level =>
        presets.some(p => p.default_hitl === level)) ?? '';
      if (!hitl) {
        follow_ups.push(
          `No selected preset (${roles.join(', ')}) declares a recognized ` +
          `default_hitl; hitl_default is empty, not a valid HITL level — ` +
          `set it explicitly before installing.`,
        );
      }

      // Every style in the union installs — a dev+qa team needs BOTH
      // orchestrators. Separately, the pre-filled default comes from the
      // first role the caller listed, except that strict HITL forces
      // dispatcher. See presets/README.md § "How the installer resolves".
      const orchestration_installed =
        [...new Set(presets.map(p => p.default_orchestration ?? '').filter(Boolean))].sort();
      const orchestration_default = hitl === 'strict'
        ? 'dispatcher'
        : (presets[0]?.default_orchestration ?? '');
      if (!orchestration_default) {
        follow_ups.push(
          `No selected preset (${roles.join(', ')}) declares a ` +
          `default_orchestration; orchestration_default is empty, not a ` +
          `valid orchestration style — set it explicitly before installing.`,
        );
      }

      const out = {
        roles, hitl_default: hitl,
        orchestration_installed, orchestration_default, files,
        // Conditional on the host's stack-fact record; the server has none
        // for someone else's repo, so these are candidates, not commitments.
        generated_candidates: [...new Set(presets.flatMap(p => p.generated ?? []))].sort(),
        sdlc_skills: [...new Set(presets.flatMap(p => p.sdlc_skills ?? []))].sort(),
        follow_ups,
      };
      return {
        content: [{ type: 'text' as const, text: JSON.stringify(out, null, 2) }],
        structuredContent: out,
      };
    },
  );
}
