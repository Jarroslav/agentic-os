/** Every repo-relative path shape the server recognises, in one place.
 *  Previously copied across resources.ts and two tool files; Phase 2b would
 *  have made a fourth copy. */
export const PRESET_PATH =
  /^plugins\/agentic-os\/presets\/roles\/([^/]+)\.json$/;
export const BLUEPRINT_PATH =
  /^plugins\/agentic-qe\/skills\/qe-blueprints\/references\/catalog\/([^/]+)\/([^/]+)\.md$/;
export const SKILL_PATH =
  /^plugins\/([^/]+)\/skills\/([^/]+)\/SKILL\.md$/;
export const TEMPLATE_ROOT = 'plugins/agentic-os/templates/';
