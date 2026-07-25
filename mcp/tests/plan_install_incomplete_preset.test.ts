import { describe, expect, it } from 'vitest';
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { Content, Doc } from '../src/content.js';
import { registerPlanInstall } from '../src/tools/plan_install.js';

type PlanOutput = {
  hitl_default: string;
  orchestration_default: string;
  follow_ups: string[];
};

type Handler = (args: { roles: string[] }) => Promise<{
  isError?: boolean;
  structuredContent?: unknown;
  content: Array<{ text: string }>;
}>;

/** Captures the handler passed to registerTool without spinning up a real
 *  McpServer or going through the stdio transport — this test only needs
 *  to exercise plan_install's own branch logic against a synthetic preset,
 *  not the protocol plumbing that tests/contract.test.ts already covers. */
function captureHandler(content: Content): Handler {
  let handler: Handler | undefined;
  const fakeServer = {
    registerTool: (_name: string, _config: unknown, h: Handler) => {
      handler = h;
    },
  } as unknown as McpServer;
  registerPlanInstall(fakeServer, content);
  if (!handler) throw new Error('registerTool was never called');
  return handler;
}

/** A minimal Content stand-in: just enough of the surface plan_install
 *  actually calls (paths(), readDoc()) to drive it with a preset fixture
 *  that omits default_hitl/default_orchestration — every real preset sets
 *  both, so this path is otherwise untestable through the real bundle. */
function fakeContentWithPresets(presets: Record<string, object>): Content {
  const docs = new Map<string, Doc>();
  for (const [role, preset] of Object.entries(presets)) {
    const path = `plugins/agentic-os/presets/roles/${role}.json`;
    docs.set(path, { path, title: role, text: JSON.stringify(preset) });
  }
  return {
    paths: () => [...docs.keys()],
    readDoc: (p: string) => docs.get(p),
    listSkills: () => [],
    markdownDocs: () => [],
  } as unknown as Content;
}

describe('plan_install — incomplete preset fallback', () => {
  it('flags an empty hitl_default and orchestration_default in follow_ups instead of presenting them as valid', async () => {
    const content = fakeContentWithPresets({
      incomplete: { name: 'incomplete', templates: [] },
    });
    const handler = captureHandler(content);
    const res = await handler({ roles: ['incomplete'] });
    const out = res.structuredContent as PlanOutput;

    expect(out.hitl_default).toBe('');
    expect(out.orchestration_default).toBe('');
    expect(out.follow_ups.some(f => /hitl/i.test(f))).toBe(true);
    expect(out.follow_ups.some(f => /orchestration/i.test(f))).toBe(true);
  });

  it('does not flag anything when the preset fully specifies both defaults', async () => {
    const content = fakeContentWithPresets({
      complete: {
        name: 'complete',
        templates: [],
        default_hitl: 'gated-autonomous',
        default_orchestration: 'pipeline',
      },
    });
    const handler = captureHandler(content);
    const res = await handler({ roles: ['complete'] });
    const out = res.structuredContent as PlanOutput;

    expect(out.hitl_default).toBe('gated-autonomous');
    expect(out.orchestration_default).toBe('pipeline');
    expect(out.follow_ups).toEqual([]);
  });
});
