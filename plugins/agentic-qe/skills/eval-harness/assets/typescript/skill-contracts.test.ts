/**
 * skill-contracts.test.ts — integration suite for the REAL skills in this
 * repository (Vitest).
 *
 * Discovers every skill under the skills root (default <repoRoot>/.claude,
 * override with SKILLS_ROOT) and generates one test group per skill:
 *   1. an eval spec exists at <skill>/eval/evals.json
 *   2. the spec passes schema validation
 *   3. every declared contract (plus the universal document checks) holds
 * plus a whole-tree pass that prints the PASS/FAIL summary on failure.
 *
 * The suite skips itself when the skills root is absent (e.g. when the
 * harness template is exercised outside a host repository).
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { describe, expect, it } from "vitest";

import {
  checkSkill,
  discoverSkills,
  evaluateRepo,
  loadSpec,
  renderSummary,
  skillsRoot,
  specPath,
} from "./runner.js";

const root = skillsRoot();
const rootExists = fs.existsSync(root);
const skills = rootExists ? discoverSkills(root) : [];

describe.skipIf(!rootExists)(`skill contracts under ${root}`, () => {
  it("discovers at least one skill", () => {
    expect(skills.length).toBeGreaterThan(0);
  });

  for (const skillDir of skills) {
    const label = path.relative(root, skillDir) || path.basename(skillDir);

    describe(label, () => {
      it("ships an eval spec", () => {
        expect(fs.existsSync(specPath(skillDir))).toBe(true);
      });

      it("has a schema-valid eval spec", () => {
        const { spec, errors } = loadSpec(skillDir);
        expect(errors).toEqual([]);
        expect(spec).toBeDefined();
      });

      it("satisfies its declared contracts", () => {
        expect(checkSkill(skillDir)).toEqual([]);
      });
    });
  }

  it("whole skill tree passes", () => {
    const result = evaluateRepo(root);
    if (!result.ok) {
      // Surface the full table so a CI failure is actionable at a glance.
      console.error(renderSummary(result, root));
    }
    expect(result.ok).toBe(true);
  });
});
