import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { ResourceTemplate } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { Content } from './content.js';

const SKILL_URI = /^agentic-os:\/\/skills\/([^/]+)\/([^/]+)$/;
const FILE_URI = /^agentic-os:\/\/file\/(.+)$/;
const PRESET_URI = /^agentic-os:\/\/presets\/([^/]+)$/;
const BLUEPRINT_URI = /^agentic-os:\/\/qe\/blueprints\/([^/]+)\/([^/]+)$/;

const PRESET_PATH = /^plugins\/agentic-os\/presets\/roles\/([^/]+)\.json$/;
const BLUEPRINT_PATH =
  /^plugins\/agentic-qe\/skills\/qe-blueprints\/references\/catalog\/([^/]+)\/([^/]+)\.md$/;

/** Translate a URI to a repo-relative path. Returns undefined for anything
 *  malformed; Content.readDoc is the authority on whether the path exists. */
export function uriToPath(uri: string): string | undefined {
  const skill = SKILL_URI.exec(uri);
  if (skill?.[1] && skill[2]) {
    return `plugins/${skill[1]}/skills/${skill[2]}/SKILL.md`;
  }

  const preset = PRESET_URI.exec(uri);
  if (preset?.[1]) return `plugins/agentic-os/presets/roles/${preset[1]}.json`;

  const bp = BLUEPRINT_URI.exec(uri);
  if (bp?.[1] && bp[2]) {
    return `plugins/agentic-qe/skills/qe-blueprints/references/catalog/${bp[1]}/${bp[2]}.md`;
  }

  const file = FILE_URI.exec(uri);
  if (file?.[1]) return `plugins/${file[1]}`;
  return undefined;
}

export function pathToUri(path: string): string {
  const m = /^plugins\/([^/]+)\/skills\/([^/]+)\/SKILL\.md$/.exec(path);
  if (m?.[1] && m[2]) return `agentic-os://skills/${m[1]}/${m[2]}`;

  const preset = PRESET_PATH.exec(path);
  if (preset?.[1]) return `agentic-os://presets/${preset[1]}`;

  const bp = BLUEPRINT_PATH.exec(path);
  if (bp?.[1] && bp[2]) return `agentic-os://qe/blueprints/${bp[1]}/${bp[2]}`;

  return `agentic-os://file/${path.replace(/^plugins\//, '')}`;
}

function mime(path: string): string {
  if (path.endsWith('.json')) return 'application/json';
  if (path.endsWith('.md')) return 'text/markdown';
  return 'text/plain';
}

export function registerResources(server: McpServer, content: Content): void {
  for (const skill of content.listSkills()) {
    const uri = pathToUri(skill.path);
    server.registerResource(
      `${skill.plugin}/${skill.skill}`,
      uri,
      { title: skill.title, description: skill.description, mimeType: 'text/markdown' },
      async () => {
        const doc = content.readDoc(skill.path);
        if (!doc) throw new Error(`missing content: ${skill.path}`);
        return { contents: [{ uri, mimeType: 'text/markdown', text: doc.text }] };
      },
    );
  }

  server.registerResource(
    'plugin-file',
    new ResourceTemplate('agentic-os://file/{+path}', { list: undefined }),
    {
      title: 'Plugin file',
      description:
        'Serves the markdown, JSON, and text files shipped by the agentic-os, ' +
        'agentic-sdlc, and agentic-qe plugins, addressed as ' +
        'agentic-os://file/<plugin>/<path>.',
    },
    async (uri: URL) => {
      const path = uriToPath(uri.href);
      const doc = path ? content.readDoc(path) : undefined;
      if (!doc) throw new Error(`unknown resource: ${uri.href}`);
      return {
        contents: [{ uri: uri.href, mimeType: mime(doc.path), text: doc.text }],
      };
    },
  );

  server.registerResource(
    'role-preset',
    new ResourceTemplate('agentic-os://presets/{role}', { list: undefined }),
    {
      title: 'Role preset',
      description:
        'One agentic-os role preset as JSON: capabilities, template set, ' +
        'HITL default, and orchestration mode.',
    },
    async (uri: URL) => {
      const path = uriToPath(uri.href);
      const doc = path ? content.readDoc(path) : undefined;
      if (!doc) throw new Error(`unknown resource: ${uri.href}`);
      return {
        contents: [{ uri: uri.href, mimeType: 'application/json', text: doc.text }],
      };
    },
  );

  server.registerResource(
    'qe-blueprint',
    new ResourceTemplate('agentic-os://qe/blueprints/{stage}/{id}', { list: undefined }),
    {
      title: 'QE blueprint',
      description:
        'One Quality Engineering blueprint from the agentic-qe catalog, ' +
        'addressed by STLC stage and id.',
    },
    async (uri: URL) => {
      const path = uriToPath(uri.href);
      const doc = path ? content.readDoc(path) : undefined;
      if (!doc) throw new Error(`unknown resource: ${uri.href}`);
      return {
        contents: [{ uri: uri.href, mimeType: 'text/markdown', text: doc.text }],
      };
    },
  );
}
