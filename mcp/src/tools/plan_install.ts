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
    .describe(
      'Role preset names to compose, e.g. ["developer","qa"]. At least one is ' +
      'required. Get the valid names from list_presets — an unrecognized name ' +
      'is an error, not a silent skip, and no partial plan is returned. ' +
      'Composition is additive: pass every role the repo needs in one call ' +
      'rather than planning each separately.',
    ),
};

const outputShape = {
  roles: z.array(z.string()).describe(
    'The roles this plan composes, echoed back in the order given (which ' +
    'determines orchestration_default).',
  ),
  hitl_default: z.string().describe(
    'The human-in-the-loop level to install: the strictest among the chosen ' +
    'roles ("strict" > "gated-autonomous" > "autonomous"). Empty if no role ' +
    'declared a recognized level, in which case follow_ups says so.',
  ),
  orchestration_installed: z.array(z.string()).describe(
    'Every orchestration style to install — the union across roles, not a ' +
    'single choice, because a mixed team needs each one present.',
  ),
  orchestration_default: z.string().describe(
    'The style to pre-select as active: the first listed role\'s default, ' +
    'except that a "strict" hitl_default forces "dispatcher". Empty if ' +
    'undeterminable, in which case follow_ups says to set it explicitly.',
  ),
  files: z.array(z.object({
    template_id: z.string().describe(
      'The template\'s id in the agentic-os template manifest.',
    ),
    source_uri: z.string().describe(
      'Read this with get_document to get the template body to write. It is ' +
      'the source to copy from, not the destination path.',
    ),
    owner: z.string().describe(
      'Ownership semantics for the written file. Always "managed" here: ' +
      'agentic-os owns it and upgrades may rewrite it, so it is not a place ' +
      'for hand edits.',
    ),
  })).describe(
    'The files to scaffold, ordered by template id. This is the plan\'s ' +
    'payload: you read each source_uri and perform the writes yourself. Any ' +
    'template with no file in the bundle is reported in follow_ups and ' +
    'omitted here rather than emitted as a broken entry.',
  ),
  generated_candidates: z.array(z.string()).describe(
    'Stack-specific agent contracts this role set *could* generate — ' +
    'candidates, not commitments. Generating one requires facts about the ' +
    'target stack that this server does not have, so filter them against the ' +
    'actual repository before writing any.',
  ),
  sdlc_skills: z.array(z.string()).describe(
    'agentic-sdlc pipeline skills the composed roles enable. Empty if no ' +
    'chosen role takes part in the SDLC flow.',
  ),
  follow_ups: z.array(z.string()).describe(
    'Problems and decisions this plan could not settle — a missing template, ' +
    'an undeterminable HITL level or orchestration default. Surface these ' +
    'rather than installing past them: an empty array means the plan is ' +
    'complete as returned.',
  ),
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
        'Compose one or more agentic-os role presets into an ordered manifest ' +
        'of the files an install should scaffold, each with a uri to read its ' +
        'template from. Use it after list_presets to turn chosen roles into ' +
        'concrete steps. Composition is additive: roles are unioned, the ' +
        'strictest HITL level wins, and every orchestration style in the union ' +
        'is installed. **This returns a plan and writes nothing** — no file is ' +
        'created, and the target repository is neither read nor touched, so ' +
        'the plan is not validated against what may already be installed ' +
        '(use run_doctor for that). You perform every write yourself, so the ' +
        'user can review each one. Read-only and idempotent.',
      inputSchema: inputShape,
      outputSchema: outputShape,
      annotations: {
        readOnlyHint: true,
        openWorldHint: false,
        idempotentHint: true,
        destructiveHint: false,
      },
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
