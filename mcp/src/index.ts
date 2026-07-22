#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { loadContent, type Content } from './content.js';
import { registerResources } from './resources.js';
import { registerPrompts } from './prompts.js';
import { registerSearchMethodology } from './tools/search_methodology.js';
import { registerGetDocument } from './tools/get_document.js';
import { registerListPresets } from './tools/list_presets.js';
import { registerListQeBlueprints } from './tools/list_qe_blueprints.js';
import { registerListSdlcPhases } from './tools/list_sdlc_phases.js';
import { registerPlanInstall } from './tools/plan_install.js';

export function createServer(content: Content): McpServer {
  const server = new McpServer(
    { name: 'agentic-os', version: '0.1.0' },
    {
      capabilities: { resources: {}, prompts: {}, tools: {} },
      instructions:
        'Serves the agentic-os governance, agentic-sdlc pipeline, and agentic-qe ' +
        'blueprint methodology. Read-only: it returns documents and plans, and ' +
        'never writes to the repository. Start with search_methodology.',
    },
  );
  registerResources(server, content);
  registerPrompts(server, content);
  registerSearchMethodology(server, content);
  registerGetDocument(server, content);
  registerListPresets(server, content);
  registerListQeBlueprints(server, content);
  registerListSdlcPhases(server, content);
  registerPlanInstall(server, content);
  return server;
}

async function main(): Promise<void> {
  const server = createServer(await loadContent());
  await server.connect(new StdioServerTransport());
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err: unknown) => {
    console.error(
      'agentic-os-mcp failed to start:',
      err instanceof Error ? err.message : String(err),
    );
    process.exit(1);
  });
}
