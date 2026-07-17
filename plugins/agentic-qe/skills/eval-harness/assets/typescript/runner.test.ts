/**
 * runner.test.ts — unit tests for the deterministic eval runner (Vitest).
 *
 * Builds synthetic skill trees inside a temp directory and exercises
 * discovery, spec validation, universal document checks, contract
 * enforcement, script contracts, and the repo-wide summary. Tests that need
 * a Python interpreter auto-skip when none is runnable.
 */

import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import {
  checkSkill,
  checkSkillDocument,
  discoverSkills,
  evaluateRepo,
  loadSpec,
  pythonAvailable,
  renderSummary,
  validateSpec,
} from "./runner.js";

let sandbox: string;

beforeAll(() => {
  sandbox = fs.mkdtempSync(path.join(os.tmpdir(), "eval-runner-test-"));
});

afterAll(() => {
  fs.rmSync(sandbox, { recursive: true, force: true });
});

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------

let counter = 0;

function freshDir(label: string): string {
  const dir = path.join(sandbox, `${label}-${counter++}`);
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function defaultSkillMd(name: string): string {
  return [
    "---",
    `name: ${name}`,
    "description: Synthetic skill used by the runner unit tests.",
    "---",
    "",
    `# ${name}`,
    "",
    "Body text.",
    "",
  ].join("\n");
}

interface SkillFixture {
  md?: string;
  spec?: unknown;
  files?: Record<string, string>;
}

function makeSkill(parent: string, name: string, fixture: SkillFixture = {}): string {
  const dir = path.join(parent, name);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "SKILL.md"), fixture.md ?? defaultSkillMd(name));
  if (fixture.spec !== undefined) {
    fs.mkdirSync(path.join(dir, "eval"), { recursive: true });
    fs.writeFileSync(path.join(dir, "eval", "evals.json"), JSON.stringify(fixture.spec, null, 2));
  }
  for (const [rel, content] of Object.entries(fixture.files ?? {})) {
    const target = path.join(dir, rel);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, content);
  }
  return dir;
}

function minimalSpec(name: string, extra: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    skill_name: name,
    contracts: { skill_md_includes: ["Body text."] },
    ...extra,
  };
}

// ---------------------------------------------------------------------------
// Discovery
// ---------------------------------------------------------------------------

describe("discoverSkills", () => {
  it("finds skills, skips dot-dirs and node_modules, ignores nested SKILL.md", () => {
    const root = freshDir("discovery");
    makeSkill(path.join(root, "skills"), "beta");
    const alpha = makeSkill(path.join(root, "skills"), "alpha");
    // Nested SKILL.md below an existing skill must not surface.
    makeSkill(alpha, "inner");
    // These whole subtrees are skipped.
    makeSkill(path.join(root, ".hidden"), "gamma");
    makeSkill(path.join(root, "node_modules"), "dep");

    const found = discoverSkills(root);
    expect(found.map((d) => path.basename(d))).toEqual(["alpha", "beta"]);
  });

  it("returns [] for a missing root", () => {
    expect(discoverSkills(path.join(sandbox, "does-not-exist"))).toEqual([]);
  });

  it("treats a root that itself holds SKILL.md as a single skill", () => {
    const root = freshDir("self");
    fs.writeFileSync(path.join(root, "SKILL.md"), defaultSkillMd(path.basename(root)));
    expect(discoverSkills(root)).toEqual([root]);
  });
});

// ---------------------------------------------------------------------------
// Spec validation
// ---------------------------------------------------------------------------

describe("validateSpec", () => {
  it("accepts a full well-formed spec", () => {
    const verdict = validateSpec({
      skill_name: "widget",
      contracts: {
        required_paths: ["SKILL.md"],
        skill_md_includes: ["## Usage"],
        skill_md_matches: ["blast\\s+radius"],
        scripts: {
          "scripts/tool.py": {
            compile: true,
            smoke: { argv: [], exit: [2], output_includes: ["usage"] },
            includes: ["def main"],
            matches: ["argparse"],
          },
        },
      },
      context_files: ["docs/ref.md"],
      evals: [
        {
          id: 1,
          prompt: "Do the thing.",
          expected_output: "A thing, done.",
          files: ["fixtures/input.txt"],
          assertions: [{ name: "does_thing", description: "The thing gets done." }],
        },
      ],
    });
    expect(verdict.errors).toEqual([]);
    expect(verdict.valid).toBe(true);
  });

  it("rejects a non-object root", () => {
    for (const bad of [null, [], "spec", 7]) {
      const verdict = validateSpec(bad);
      expect(verdict.valid).toBe(false);
      expect(verdict.errors[0]).toMatch(/JSON object/);
    }
  });

  it("rejects a missing or blank skill_name", () => {
    const verdict = validateSpec({ skill_name: "  ", contracts: { required_paths: ["x"] } });
    expect(verdict.valid).toBe(false);
    expect(verdict.errors.join("\n")).toMatch(/skill_name/);
  });

  it("rejects a missing contracts block", () => {
    const verdict = validateSpec({ skill_name: "widget" });
    expect(verdict.valid).toBe(false);
    expect(verdict.errors.join("\n")).toMatch(/contracts/);
  });

  it("rejects unknown contract keys so typos cannot become no-ops", () => {
    const verdict = validateSpec({
      skill_name: "widget",
      contracts: { required_pathz: ["SKILL.md"] },
    });
    expect(verdict.valid).toBe(false);
    expect(verdict.errors.join("\n")).toMatch(/unknown key "required_pathz"/);
  });

  it("rejects unknown script and smoke keys", () => {
    const verdict = validateSpec({
      skill_name: "widget",
      contracts: {
        scripts: {
          "a.py": { compil: false, smoke: { argv: [], exits: [0] } },
        },
      },
    });
    expect(verdict.valid).toBe(false);
    const text = verdict.errors.join("\n");
    expect(text).toMatch(/unknown key "compil"/);
    expect(text).toMatch(/unknown key "exits"/);
  });

  it("rejects a smoke block without argv", () => {
    const verdict = validateSpec({
      skill_name: "widget",
      contracts: { scripts: { "a.py": { smoke: { exit: [0] } } } },
    });
    expect(verdict.valid).toBe(false);
    expect(verdict.errors.join("\n")).toMatch(/argv/);
  });

  it("rejects a contracts block whose checks are all empty", () => {
    const verdict = validateSpec({
      skill_name: "widget",
      contracts: { required_paths: [], skill_md_includes: [], skill_md_matches: [] },
    });
    expect(verdict.valid).toBe(false);
    expect(verdict.errors.join("\n")).toMatch(/no non-empty checks/);
  });

  it("counts a non-empty scripts object as a declared check", () => {
    const verdict = validateSpec({
      skill_name: "widget",
      contracts: { scripts: { "a.py": { compile: false, includes: ["x"] } } },
    });
    expect(verdict.errors).toEqual([]);
    expect(verdict.valid).toBe(true);
  });

  it("flags malformed evals entries", () => {
    const verdict = validateSpec({
      skill_name: "widget",
      contracts: { required_paths: ["SKILL.md"] },
      evals: [{ id: "one", prompt: "", assertions: [{ name: 3 }] }],
    });
    expect(verdict.valid).toBe(false);
    const text = verdict.errors.join("\n");
    expect(text).toMatch(/id must be a number/);
    expect(text).toMatch(/prompt must be a non-empty string/);
    expect(text).toMatch(/assertions\[0\]/);
  });
});

// ---------------------------------------------------------------------------
// Universal document checks
// ---------------------------------------------------------------------------

describe("checkSkillDocument", () => {
  it("reports a missing SKILL.md and stops", () => {
    const dir = freshDir("no-md");
    expect(checkSkillDocument(dir)).toEqual(["SKILL.md not found"]);
  });

  it("flags a frontmatter name that differs from the directory", () => {
    const parent = freshDir("names");
    const dir = makeSkill(parent, "actual", {
      md: ["---", "name: other", "description: Something.", "---", "body", ""].join("\n"),
    });
    expect(checkSkillDocument(dir).join("\n")).toMatch(/"other" does not match directory "actual"/);
  });

  it("flags a missing description", () => {
    const parent = freshDir("nodesc");
    const dir = makeSkill(parent, "quiet", {
      md: ["---", "name: quiet", "---", "body", ""].join("\n"),
    });
    expect(checkSkillDocument(dir).join("\n")).toMatch(/description/);
  });

  it("enforces the 500-line budget, ignoring the trailing newline", () => {
    const parent = freshDir("lines");
    const head = ["---", "name: long", "description: Fits.", "---"];
    const okBody = Array.from({ length: 496 }, (_, i) => `line ${i}`);
    const ok = makeSkill(parent, "long", { md: [...head, ...okBody].join("\n") + "\n" });
    expect(checkSkillDocument(ok)).toEqual([]);

    const over = makeSkill(freshDir("lines2"), "long", {
      md: [...head, ...okBody, "one more"].join("\n") + "\n",
    });
    expect(checkSkillDocument(over).join("\n")).toMatch(/501 lines/);
  });

  it("folds block-scalar descriptions before measuring them", () => {
    const parent = freshDir("folded");
    const short = makeSkill(parent, "folded", {
      md: [
        "---",
        "name: folded",
        "description: >-",
        "  Spread over",
        "  two lines.",
        "---",
        "body",
        "",
      ].join("\n"),
    });
    expect(checkSkillDocument(short)).toEqual([]);

    const long = makeSkill(freshDir("folded2"), "folded", {
      md: [
        "---",
        "name: folded",
        "description: |",
        `  ${"x".repeat(1200)}`,
        "---",
        "body",
        "",
      ].join("\n"),
    });
    expect(checkSkillDocument(long).join("\n")).toMatch(/budget 1000/);
  });
});

// ---------------------------------------------------------------------------
// Spec loading + contract enforcement via checkSkill
// ---------------------------------------------------------------------------

describe("checkSkill", () => {
  it("reports a missing spec after the universal checks", () => {
    const dir = makeSkill(freshDir("nospec"), "bare");
    const errors = checkSkill(dir);
    expect(errors).toHaveLength(1);
    expect(errors[0]).toMatch(/evals\.json/);
  });

  it("prefixes schema errors with the spec file name", () => {
    const dir = makeSkill(freshDir("badspec"), "typo", {
      spec: { skill_name: "typo", contracts: { required_pathz: ["x"] } },
    });
    const errors = checkSkill(dir);
    expect(errors.some((e) => e.startsWith("evals.json:"))).toBe(true);
  });

  it("passes when every contract is satisfied", () => {
    const dir = makeSkill(freshDir("good"), "widget", {
      md: [
        "---",
        "name: widget",
        "description: A well-behaved synthetic skill.",
        "---",
        "",
        "Blast Radius: R1",
        "",
      ].join("\n"),
      spec: {
        skill_name: "widget",
        contracts: {
          required_paths: ["assets/data.json"],
          skill_md_includes: ["Blast Radius"],
          skill_md_matches: ["blast radius:\\s*r1"],
        },
      },
      files: { "assets/data.json": "{}" },
    });
    expect(checkSkill(dir)).toEqual([]);
  });

  it("yields one error per broken contract, including bad regexes", () => {
    const dir = makeSkill(freshDir("broken"), "widget", {
      spec: {
        skill_name: "widget",
        contracts: {
          required_paths: ["assets/missing.json"],
          skill_md_includes: ["No Such Heading"],
          skill_md_matches: ["(["],
        },
      },
    });
    const errors = checkSkill(dir);
    expect(errors.join("\n")).toMatch(/required path missing: assets\/missing\.json/);
    expect(errors.join("\n")).toMatch(/does not include "No Such Heading"/);
    expect(errors.join("\n")).toMatch(/invalid regex/);
    expect(errors).toHaveLength(3);
  });

  it("loadSpec surfaces invalid JSON as a single error", () => {
    const dir = makeSkill(freshDir("badjson"), "widget");
    fs.mkdirSync(path.join(dir, "eval"), { recursive: true });
    fs.writeFileSync(path.join(dir, "eval", "evals.json"), "{ not json");
    const { spec, errors } = loadSpec(dir);
    expect(spec).toBeUndefined();
    expect(errors).toHaveLength(1);
    expect(errors[0]).toMatch(/not valid JSON/);
  });
});

// ---------------------------------------------------------------------------
// Script contracts
// ---------------------------------------------------------------------------

describe("script contracts", () => {
  it("emits the distinct interpreter-missing error when PYTHON points nowhere", () => {
    const saved = process.env.PYTHON;
    process.env.PYTHON = path.join(sandbox, "no-such-python");
    try {
      const dir = makeSkill(freshDir("nopython"), "widget", {
        spec: {
          skill_name: "widget",
          contracts: { scripts: { "tool.py": {} } },
        },
        files: { "tool.py": "print('hi')\n" },
      });
      expect(checkSkill(dir).join("\n")).toMatch(/set PYTHON or install Python 3/);
    } finally {
      if (saved === undefined) delete process.env.PYTHON;
      else process.env.PYTHON = saved;
    }
  });

  it("reports a missing script file without invoking the interpreter", () => {
    const dir = makeSkill(freshDir("noscript"), "widget", {
      spec: { skill_name: "widget", contracts: { scripts: { "gone.py": {} } } },
    });
    expect(checkSkill(dir).join("\n")).toMatch(/script missing: gone\.py/);
  });

  describe.skipIf(!pythonAvailable())("with a runnable interpreter", () => {
    const USAGE_SCRIPT = [
      "import sys",
      "",
      "def main() -> int:",
      "    if len(sys.argv) < 2:",
      '        sys.stderr.write("usage: greet.py NAME\\n")',
      "        return 2",
      '    print(f"hello {sys.argv[1]}")',
      "    return 0",
      "",
      'if __name__ == "__main__":',
      "    raise SystemExit(main())",
      "",
    ].join("\n");

    it("byte-compiles clean scripts and checks source text", () => {
      const dir = makeSkill(freshDir("compileok"), "widget", {
        spec: {
          skill_name: "widget",
          contracts: {
            scripts: {
              "greet.py": { includes: ["def main"], matches: ["SystemExit"] },
            },
          },
        },
        files: { "greet.py": USAGE_SCRIPT },
      });
      expect(checkSkill(dir)).toEqual([]);
    });

    it("fails byte-compile on broken syntax, and compile:false skips it", () => {
      const broken = "def broken(:\n    pass\n";
      const failing = makeSkill(freshDir("compilebad"), "widget", {
        spec: { skill_name: "widget", contracts: { scripts: { "bad.py": {} } } },
        files: { "bad.py": broken },
      });
      expect(checkSkill(failing).join("\n")).toMatch(/byte-compile failed/);

      const skipped = makeSkill(freshDir("compileskip"), "widget", {
        spec: {
          skill_name: "widget",
          contracts: { scripts: { "bad.py": { compile: false, includes: ["pass"] } } },
        },
        files: { "bad.py": broken },
      });
      expect(checkSkill(skipped)).toEqual([]);
    });

    it("accepts declared non-zero smoke exits (usage-on-no-args)", () => {
      const dir = makeSkill(freshDir("smokeusage"), "widget", {
        spec: {
          skill_name: "widget",
          contracts: {
            scripts: {
              "greet.py": {
                smoke: { argv: [], exit: [2], output_includes: ["usage:"] },
              },
            },
          },
        },
        files: { "greet.py": USAGE_SCRIPT },
      });
      expect(checkSkill(dir)).toEqual([]);
    });

    it("rejects smoke exits outside the allowed set", () => {
      const dir = makeSkill(freshDir("smokebad"), "widget", {
        spec: {
          skill_name: "widget",
          contracts: { scripts: { "greet.py": { smoke: { argv: [] } } } },
        },
        files: { "greet.py": USAGE_SCRIPT },
      });
      expect(checkSkill(dir).join("\n")).toMatch(/exited 2, expected one of \[0\]/);
    });

    it("checks smoke stdout for happy-path runs", () => {
      const dir = makeSkill(freshDir("smokeok"), "widget", {
        spec: {
          skill_name: "widget",
          contracts: {
            scripts: {
              "greet.py": { smoke: { argv: ["world"], output_includes: ["hello world"] } },
            },
          },
        },
        files: { "greet.py": USAGE_SCRIPT },
      });
      expect(checkSkill(dir)).toEqual([]);
    });

    it("feeds smoke runs a closed empty stdin so readers see EOF", () => {
      const script = [
        "import sys",
        "data = sys.stdin.read()",
        'print(f"EOF-OK {len(data)}")',
        "",
      ].join("\n");
      const dir = makeSkill(freshDir("stdineof"), "widget", {
        spec: {
          skill_name: "widget",
          contracts: {
            scripts: {
              "drain.py": { smoke: { argv: [], output_includes: ["EOF-OK 0"] } },
            },
          },
        },
        files: { "drain.py": script },
      });
      expect(checkSkill(dir)).toEqual([]);
    });
  });
});

// ---------------------------------------------------------------------------
// Repo-wide aggregation and summary
// ---------------------------------------------------------------------------

describe("evaluateRepo / renderSummary", () => {
  it("aggregates rows, prefixes errors with skill names, and renders a table", () => {
    const root = freshDir("repo");
    makeSkill(root, "good", { spec: minimalSpec("good") });
    makeSkill(root, "unruly"); // no spec -> one violation

    const result = evaluateRepo(root);
    expect(result.rows.map((r) => [r.skillName, r.status])).toEqual([
      ["good", "pass"],
      ["unruly", "fail"],
    ]);
    expect(result.ok).toBe(false);
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0]).toMatch(/^unruly: /);

    const summary = renderSummary(result, root);
    expect(summary).toContain("PASS");
    expect(summary).toContain("FAIL");
    expect(summary).toContain("1 violation(s) found.");
  });

  it("declares success when every skill passes", () => {
    const root = freshDir("repo-ok");
    makeSkill(root, "solo", { spec: minimalSpec("solo") });
    const result = evaluateRepo(root);
    expect(result.ok).toBe(true);
    expect(renderSummary(result, root)).toContain("All skills satisfy their contracts.");
  });
});
