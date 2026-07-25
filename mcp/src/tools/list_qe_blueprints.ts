import { z } from 'zod';
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { Content } from '../content.js';
import { pathToUri } from '../resources.js';
import { truncateCodePoints } from '../text.js';
import { BLUEPRINT_PATH as CATALOG } from '../paths.js';

const outputShape = {
  blueprints: z.array(z.object({
    id: z.string().describe(
      'Blueprint identifier, e.g. "coverage-analysis". Unique within its ' +
      'stage; pair it with stage to refer to one unambiguously.',
    ),
    stage: z.string().describe(
      'The STLC stage this blueprint belongs to — the same value the stage ' +
      'argument filters on.',
    ),
    title: z.string().describe("The blueprint's first markdown heading."),
    summary: z.string().describe(
      "The blueprint's opening purpose statement, collapsed to one line and " +
      'capped at 300 code points with a trailing ellipsis when longer. Enough ' +
      'to choose between blueprints, not to act on one — read the uri for that.',
    ),
    uri: z.string().describe(
      'Read this with get_document for the full blueprint.',
    ),
  })).describe(
    'Matching blueprints, ordered by stage then id. Empty only when a stage ' +
    'filter matched nothing; an unfiltered call that finds nothing is ' +
    'reported as an error instead, since that means the catalog failed to load.',
  ),
};

/** First non-empty paragraph after the H1, collapsed to one line and capped.
 *  Blueprints open with a one-sentence purpose statement; that is the summary. */
function summarize(text: string): string {
  const body = text.replace(/^#[^\n]*\n/, '');
  const para = body.split(/\n\s*\n/).map(s => s.trim()).find(s => s && !s.startsWith('#'));
  const line = (para ?? '').replace(/\s+/g, ' ').trim();
  const { text: capped, truncated } = truncateCodePoints(line, 300);
  return truncated ? capped + '…' : capped;
}

export function registerListQeBlueprints(server: McpServer, content: Content): void {
  // Derived from the build-time index rather than a hand-written tuple, so a
  // stage directory added to or removed from the catalog is reflected in the
  // schema automatically — the same "derive, don't hardcode" fix already
  // applied to list_presets.ts's role list. Sorted so the generated schema
  // is stable across runs (of no functional consequence to zod, but it keeps
  // e.g. `tools/list` output diffable).
  const stages = [...new Set(
    content.paths()
      .map(path => CATALOG.exec(path)?.[1])
      .filter((s): s is string => s !== undefined),
  )].sort();

  // z.enum() requires a non-empty tuple type at the type level, so an empty
  // `stages` (the catalog directory missing or unreadable from the content
  // bundle) can't be handed to it directly. Throwing here would crash the
  // whole server at startup — taking every other tool down over one missing
  // directory — so instead fall back to an unconstrained string filter: the
  // tool still registers, and a broken catalog then surfaces at call time as
  // the empty-result isError below (matching list_sdlc_phases's "produced
  // nothing means broken" convention) rather than as a hard startup crash.
  const stageSchema = stages.length > 0
    ? z.enum(stages as [string, ...string[]])
    : z.string();

  const inputShape = {
    stage: stageSchema.optional().describe(
      'Restrict results to a single STLC stage. Omit to return the whole ' +
      'catalog, which is small enough to scan in one call.',
    ),
  };

  server.registerTool(
    'list_qe_blueprints',
    {
      title: 'List QE blueprints',
      description:
        'Browse the agentic-qe Quality Engineering blueprint catalog, ' +
        'organized by STLC stage. Each blueprint describes how to build one ' +
        'piece of QE capability (test-coverage analysis, flaky-test debugging, ' +
        'and so on); use this to find the blueprint that fits a QE task, then ' +
        'read its uri for the instructions. Returns titles and one-line ' +
        'summaries only — it is a catalog index, not the blueprint content. ' +
        'The stage argument enumerates the valid stages. Read-only and ' +
        'idempotent.',
      inputSchema: inputShape,
      outputSchema: outputShape,
      annotations: {
        readOnlyHint: true,
        openWorldHint: false,
        idempotentHint: true,
        destructiveHint: false,
      },
    },
    async ({ stage }) => {
      const blueprints = content.markdownDocs().flatMap(doc => {
        const m = CATALOG.exec(doc.path);
        if (!m?.[1] || !m[2]) return [];
        if (stage && m[1] !== stage) return [];
        return [{
          id: m[2],
          stage: m[1],
          title: doc.title,
          summary: summarize(doc.text),
          uri: pathToUri(doc.path),
        }];
      }).sort((a, b) =>
        a.stage.localeCompare(b.stage) || a.id.localeCompare(b.id));

      // A stage-filtered query naming a real stage that just happens to have
      // no blueprints (or no matches) is a legitimate empty result. But an
      // *unfiltered* call returning nothing means the whole catalog failed
      // to load — that's the same "produced nothing means broken" signal
      // list_sdlc_phases treats as isError, so match it here too.
      if (blueprints.length === 0 && !stage) {
        return {
          isError: true,
          content: [{
            type: 'text' as const,
            text: 'No QE blueprints were found in the content bundle. The catalog ' +
              'under plugins/agentic-qe/skills/qe-blueprints/references/catalog/ ' +
              'may be missing or empty.',
          }],
        };
      }

      return {
        content: [{ type: 'text' as const, text: JSON.stringify({ blueprints }, null, 2) }],
        structuredContent: { blueprints },
      };
    },
  );
}
