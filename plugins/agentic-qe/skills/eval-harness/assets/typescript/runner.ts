/**
 * runner.ts — deterministic (no-LLM) eval checks for Claude Code skills.
 *
 * A "skill" is any directory that contains a SKILL.md. Each skill may ship a
 * spec at <skill>/eval/evals.json whose `contracts` block declares
 * machine-checkable guarantees:
 *
 *   - required_paths       paths (relative to the skill dir) that must exist
 *   - skill_md_includes    literal substrings SKILL.md must contain
 *   - skill_md_matches     regex sources tested case-insensitively on SKILL.md
 *   - scripts              per-script contracts: Python byte-compile, source
 *                          text checks, and smoke runs with an allowed exit set
 *
 * Independent of any spec, every skill gets universal document checks:
 * SKILL.md exists, frontmatter `name` matches the directory basename, a
 * non-blank `description` is present, the file stays under a line budget, and
 * the (block-scalar aware) description stays under a character budget.
 *
 * This module is a library only — the Vitest suites (runner.test.ts and
 * skill-contracts.test.ts) drive it. Blast radius: R0 for all document and
 * spec checks; smoke runs execute the skill's own scripts (R1 — run artifacts
 * only, no repo writes).
 *
 * Layout contract: these harness files live at <repoRoot>/eval/. The skills
 * root defaults to <repoRoot>/.claude and can be overridden with the
 * SKILLS_ROOT env var (resolved against the repo root).
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { spawnSync } from "node:child_process";

// ---------------------------------------------------------------------------
// Budgets and constants
// ---------------------------------------------------------------------------

/** Maximum number of lines allowed in SKILL.md (trailing newline ignored). */
export const MAX_SKILL_MD_LINES = 500;

/** Maximum length of the normalized frontmatter description. */
export const MAX_DESCRIPTION_CHARS = 1000;

/** Wall-clock budget for a single script smoke run or byte-compile. */
export const SMOKE_TIMEOUT_MS = 60_000;

const SPEC_RELATIVE = path.join("eval", "evals.json");

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SmokeContract {
  /** Arguments passed to the script. Required, may be empty. */
  argv: string[];
  /** Allowed exit codes; defaults to [0]. Non-zero sets support usage-on-no-args CLIs. */
  exit?: number[];
  /** Substrings that must appear in stdout+stderr combined. */
  output_includes?: string[];
}

export interface ScriptContract {
  /** When false, skip the Python byte-compile step. Defaults to true. */
  compile?: boolean;
  smoke?: SmokeContract;
  /** Literal substrings the script SOURCE must contain. */
  includes?: string[];
  /** Regex sources tested (case-insensitively) against the script SOURCE. */
  matches?: string[];
}

export interface ContractBlock {
  required_paths?: string[];
  skill_md_includes?: string[];
  skill_md_matches?: string[];
  scripts?: Record<string, ScriptContract>;
}

export interface AssertionSpec {
  name: string;
  description: string;
}

export interface EvalCaseSpec {
  id: number;
  prompt: string;
  /** Report-only prose describing a good answer. Never graded. */
  expected_output?: string;
  files?: string[];
  assertions: AssertionSpec[];
}

export interface EvalSpec {
  skill_name: string;
  contracts: ContractBlock;
  context_files?: string[];
  evals?: EvalCaseSpec[];
}

export interface SpecValidation {
  valid: boolean;
  errors: string[];
}

export interface SkillRow {
  skillName: string;
  skillDir: string;
  status: "pass" | "fail";
  errors: string[];
}

export interface RepoResult {
  ok: boolean;
  rows: SkillRow[];
  /** Flat list of all violations, each prefixed with the skill name. */
  errors: string[];
}

// ---------------------------------------------------------------------------
// Roots
// ---------------------------------------------------------------------------

/**
 * Repository root. The harness is designed to live at <repoRoot>/eval and be
 * driven by Vitest from the repository root; EVAL_REPO_ROOT overrides for
 * unusual layouts.
 */
export function repoRoot(): string {
  const override = process.env.EVAL_REPO_ROOT;
  return override ? path.resolve(override) : process.cwd();
}

/** Skills root: <repoRoot>/.claude unless SKILLS_ROOT overrides it. */
export function skillsRoot(root: string = repoRoot()): string {
  const custom = process.env.SKILLS_ROOT;
  return custom ? path.resolve(root, custom) : path.join(root, ".claude");
}

/** Path to a skill's eval spec file. */
export function specPath(skillDir: string): string {
  return path.join(skillDir, SPEC_RELATIVE);
}

// ---------------------------------------------------------------------------
// Discovery
// ---------------------------------------------------------------------------

/**
 * Depth-first walk collecting every directory that holds a SKILL.md.
 * Recursion stops at a skill boundary (nested SKILL.md files are ignored),
 * dot-directories and node_modules are skipped, unreadable entries are
 * silently ignored, and the result is sorted for stable output.
 */
export function discoverSkills(root: string): string[] {
  const found: string[] = [];

  const walk = (dir: string): void => {
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return; // unreadable — ignore
    }
    if (entries.some((e) => e.isFile() && e.name === "SKILL.md")) {
      found.push(dir);
      return; // a skill's own subtree is opaque to discovery
    }
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      if (entry.name.startsWith(".") || entry.name === "node_modules") continue;
      walk(path.join(dir, entry.name));
    }
  };

  walk(root);
  return found.sort();
}

// ---------------------------------------------------------------------------
// Frontmatter
// ---------------------------------------------------------------------------

function stripQuotes(value: string): string {
  const m = /^(['"])(.*)\1$/.exec(value);
  return m ? m[2] : value;
}

/**
 * Deliberately minimal frontmatter reader: only the `name` and `description`
 * keys of a leading `--- ... ---` block, with surrounding quotes stripped.
 * Block scalars are NOT resolved here — see extractDescription.
 */
export function parseFrontmatter(text: string): { name?: string; description?: string } {
  const lines = text.split(/\r?\n/);
  if ((lines[0] ?? "").trim() !== "---") return {};
  const out: { name?: string; description?: string } = {};
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    if (line.trim() === "---") break;
    const m = /^(name|description):\s*(.*)$/.exec(line);
    if (m) out[m[1] as "name" | "description"] = stripQuotes(m[2].trim());
  }
  return out;
}

/**
 * Description extractor that also understands YAML block scalars
 * (`>`, `|`, and their `+`/`-` chomping variants): the indented lines that
 * follow are joined with single spaces so multi-line descriptions can be
 * measured against the character budget.
 */
export function extractDescription(text: string): string | undefined {
  const lines = text.split(/\r?\n/);
  if ((lines[0] ?? "").trim() !== "---") return undefined;
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    if (line.trim() === "---") break;
    const m = /^description:\s*(.*)$/.exec(line);
    if (!m) continue;
    const inline = m[1].trim();
    if (!/^[>|][+-]?$/.test(inline)) {
      const value = stripQuotes(inline);
      return value === "" ? undefined : value;
    }
    // Block scalar: gather the indented continuation lines.
    const parts: string[] = [];
    for (let j = i + 1; j < lines.length; j++) {
      const cont = lines[j];
      if (cont.trim() === "---") break;
      if (cont.trim() === "") continue;
      if (!/^\s/.test(cont)) break; // dedent ends the scalar
      parts.push(cont.trim());
    }
    const joined = parts.join(" ").trim();
    return joined === "" ? undefined : joined;
  }
  return undefined;
}

function normalizeWhitespace(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

// ---------------------------------------------------------------------------
// Universal document checks
// ---------------------------------------------------------------------------

/**
 * Checks that apply to every skill whether or not a spec exists:
 * SKILL.md present, frontmatter name equals the directory basename,
 * non-blank description, line budget, description character budget.
 */
export function checkSkillDocument(skillDir: string): string[] {
  const errors: string[] = [];
  const skillMd = path.join(skillDir, "SKILL.md");

  if (!fs.existsSync(skillMd)) {
    return ["SKILL.md not found"];
  }

  let text: string;
  try {
    text = fs.readFileSync(skillMd, "utf8");
  } catch (err) {
    return [`SKILL.md unreadable: ${(err as Error).message}`];
  }

  const lineCount = text.replace(/\r?\n$/, "").split(/\r?\n/).length;
  if (lineCount > MAX_SKILL_MD_LINES) {
    errors.push(`SKILL.md has ${lineCount} lines (budget ${MAX_SKILL_MD_LINES})`);
  }

  const fm = parseFrontmatter(text);
  const dirName = path.basename(skillDir);
  if (!fm.name) {
    errors.push("frontmatter is missing `name`");
  } else if (fm.name !== dirName) {
    errors.push(`frontmatter name "${fm.name}" does not match directory "${dirName}"`);
  }

  const description = extractDescription(text);
  if (!description || normalizeWhitespace(description) === "") {
    errors.push("frontmatter is missing a non-blank `description`");
  } else {
    const normalized = normalizeWhitespace(description);
    if (normalized.length > MAX_DESCRIPTION_CHARS) {
      errors.push(
        `description is ${normalized.length} chars after normalization (budget ${MAX_DESCRIPTION_CHARS})`,
      );
    }
  }

  return errors;
}

// ---------------------------------------------------------------------------
// Spec schema validation
// ---------------------------------------------------------------------------

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((v) => typeof v === "string");
}

function isNumberArray(value: unknown): value is number[] {
  return Array.isArray(value) && value.every((v) => typeof v === "number" && Number.isFinite(v));
}

const CONTRACT_KEYS = new Set(["required_paths", "skill_md_includes", "skill_md_matches", "scripts"]);
const SCRIPT_KEYS = new Set(["compile", "smoke", "includes", "matches"]);
const SMOKE_KEYS = new Set(["argv", "exit", "output_includes"]);

function validateSmoke(label: string, value: unknown, errors: string[]): void {
  if (!isPlainObject(value)) {
    errors.push(`${label}.smoke must be an object`);
    return;
  }
  for (const key of Object.keys(value)) {
    if (!SMOKE_KEYS.has(key)) errors.push(`${label}.smoke has unknown key "${key}"`);
  }
  if (!isStringArray(value.argv)) {
    errors.push(`${label}.smoke.argv is required and must be an array of strings`);
  }
  if (value.exit !== undefined && !isNumberArray(value.exit)) {
    errors.push(`${label}.smoke.exit must be an array of numbers`);
  }
  if (value.output_includes !== undefined && !isStringArray(value.output_includes)) {
    errors.push(`${label}.smoke.output_includes must be an array of strings`);
  }
}

function validateScript(label: string, value: unknown, errors: string[]): void {
  if (!isPlainObject(value)) {
    errors.push(`${label} must be an object`);
    return;
  }
  for (const key of Object.keys(value)) {
    if (!SCRIPT_KEYS.has(key)) errors.push(`${label} has unknown key "${key}"`);
  }
  if (value.compile !== undefined && typeof value.compile !== "boolean") {
    errors.push(`${label}.compile must be a boolean`);
  }
  if (value.smoke !== undefined) validateSmoke(label, value.smoke, errors);
  if (value.includes !== undefined && !isStringArray(value.includes)) {
    errors.push(`${label}.includes must be an array of strings`);
  }
  if (value.matches !== undefined && !isStringArray(value.matches)) {
    errors.push(`${label}.matches must be an array of strings`);
  }
}

function validateContracts(value: unknown, errors: string[]): void {
  if (!isPlainObject(value)) {
    errors.push("contracts is required and must be an object");
    return;
  }
  for (const key of Object.keys(value)) {
    if (!CONTRACT_KEYS.has(key)) errors.push(`contracts has unknown key "${key}"`);
  }
  for (const key of ["required_paths", "skill_md_includes", "skill_md_matches"] as const) {
    if (value[key] !== undefined && !isStringArray(value[key])) {
      errors.push(`contracts.${key} must be an array of strings`);
    }
  }
  let scriptCount = 0;
  if (value.scripts !== undefined) {
    if (!isPlainObject(value.scripts)) {
      errors.push("contracts.scripts must be an object keyed by script path");
    } else {
      const scripts = value.scripts;
      scriptCount = Object.keys(scripts).length;
      for (const [rel, contract] of Object.entries(scripts)) {
        validateScript(`contracts.scripts["${rel}"]`, contract, errors);
      }
    }
  }

  // A syntactically valid contracts block must still declare something real —
  // otherwise a typo silently disables all checking.
  const declared =
    (isStringArray(value.required_paths) && value.required_paths.length > 0) ||
    (isStringArray(value.skill_md_includes) && value.skill_md_includes.length > 0) ||
    (isStringArray(value.skill_md_matches) && value.skill_md_matches.length > 0) ||
    scriptCount > 0;
  if (!declared && errors.length === 0) {
    errors.push("contracts declares no non-empty checks");
  }
}

function validateEvals(value: unknown, errors: string[]): void {
  if (!Array.isArray(value)) {
    errors.push("evals must be an array");
    return;
  }
  value.forEach((entry, idx) => {
    const label = `evals[${idx}]`;
    if (!isPlainObject(entry)) {
      errors.push(`${label} must be an object`);
      return;
    }
    if (typeof entry.id !== "number") errors.push(`${label}.id must be a number`);
    if (typeof entry.prompt !== "string" || entry.prompt.trim() === "") {
      errors.push(`${label}.prompt must be a non-empty string`);
    }
    if (entry.expected_output !== undefined && typeof entry.expected_output !== "string") {
      errors.push(`${label}.expected_output must be a string`);
    }
    if (entry.files !== undefined && !isStringArray(entry.files)) {
      errors.push(`${label}.files must be an array of strings`);
    }
    if (!Array.isArray(entry.assertions)) {
      errors.push(`${label}.assertions must be an array`);
      return;
    }
    entry.assertions.forEach((assertion, aIdx) => {
      if (
        !isPlainObject(assertion) ||
        typeof assertion.name !== "string" ||
        typeof assertion.description !== "string"
      ) {
        errors.push(`${label}.assertions[${aIdx}] must have string name and description`);
      }
    });
  });
}

/** Validate a parsed evals.json value. Never throws. */
export function validateSpec(value: unknown): SpecValidation {
  const errors: string[] = [];

  if (!isPlainObject(value)) {
    return { valid: false, errors: ["spec root must be a JSON object"] };
  }
  if (typeof value.skill_name !== "string" || value.skill_name.trim() === "") {
    errors.push("skill_name must be a non-empty string");
  }
  validateContracts(value.contracts, errors);
  if (value.context_files !== undefined && !isStringArray(value.context_files)) {
    errors.push("context_files must be an array of strings");
  }
  if (value.evals !== undefined) validateEvals(value.evals, errors);

  return { valid: errors.length === 0, errors };
}

/** Read + parse + validate a skill's evals.json. Errors are prefixed. */
export function loadSpec(skillDir: string): { spec?: EvalSpec; errors: string[] } {
  const file = specPath(skillDir);
  if (!fs.existsSync(file)) {
    return { errors: [`eval spec not found: ${SPEC_RELATIVE}`] };
  }
  let raw: string;
  try {
    raw = fs.readFileSync(file, "utf8");
  } catch (err) {
    return { errors: [`evals.json unreadable: ${(err as Error).message}`] };
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    return { errors: [`evals.json is not valid JSON: ${(err as Error).message}`] };
  }
  const verdict = validateSpec(parsed);
  if (!verdict.valid) {
    return { errors: verdict.errors.map((e) => `evals.json: ${e}`) };
  }
  return { spec: parsed as EvalSpec, errors: [] };
}

// ---------------------------------------------------------------------------
// Python plumbing
// ---------------------------------------------------------------------------

/** Interpreter used for byte-compile and smoke runs: $PYTHON or python3. */
export function pythonInterpreter(): string {
  return process.env.PYTHON || "python3";
}

/** True when the configured interpreter can actually run. */
export function pythonAvailable(): boolean {
  const result = spawnSync(pythonInterpreter(), ["--version"], { stdio: "ignore" });
  return !result.error && result.status === 0;
}

function interpreterMissingError(interp: string): string {
  return `python interpreter "${interp}" is not runnable — set PYTHON or install Python 3`;
}

// ---------------------------------------------------------------------------
// Contract enforcement
// ---------------------------------------------------------------------------

function checkScript(skillDir: string, rel: string, contract: ScriptContract, errors: string[]): void {
  const file = path.join(skillDir, rel);
  if (!fs.existsSync(file)) {
    errors.push(`script missing: ${rel}`);
    return;
  }

  const interp = pythonInterpreter();

  if (contract.compile !== false) {
    const result = spawnSync(interp, ["-m", "py_compile", file], {
      encoding: "utf8",
      timeout: SMOKE_TIMEOUT_MS,
    });
    if (result.error && (result.error as NodeJS.ErrnoException).code === "ENOENT") {
      errors.push(interpreterMissingError(interp));
      return; // no interpreter — smoke would fail the same way
    }
    if (result.status !== 0) {
      const detail = (result.stderr ?? "").trim().slice(0, 300);
      errors.push(`${rel}: byte-compile failed${detail ? `: ${detail}` : ""}`);
    }
  }

  let source: string | undefined;
  try {
    source = fs.readFileSync(file, "utf8");
  } catch {
    source = undefined;
  }
  if (source !== undefined) {
    for (const needle of contract.includes ?? []) {
      if (!source.includes(needle)) errors.push(`${rel}: source does not include "${needle}"`);
    }
    for (const pattern of contract.matches ?? []) {
      try {
        if (!new RegExp(pattern, "i").test(source)) {
          errors.push(`${rel}: source does not match /${pattern}/i`);
        }
      } catch (err) {
        errors.push(`${rel}: invalid regex /${pattern}/: ${(err as Error).message}`);
      }
    }
  }

  if (contract.smoke) {
    // stdin is supplied closed and empty: scripts that read it see immediate
    // EOF and a non-tty, so usage-on-no-args CLIs exit deterministically
    // instead of hanging until the timeout.
    const result = spawnSync(interp, [file, ...contract.smoke.argv], {
      encoding: "utf8",
      timeout: SMOKE_TIMEOUT_MS,
      input: "",
    });
    if (result.error && (result.error as NodeJS.ErrnoException).code === "ENOENT") {
      errors.push(interpreterMissingError(interp));
      return;
    }
    if (result.signal) {
      errors.push(`${rel}: smoke run killed by ${result.signal} (timeout ${SMOKE_TIMEOUT_MS}ms?)`);
      return;
    }
    const allowed = contract.smoke.exit ?? [0];
    const code = result.status ?? -1;
    if (!allowed.includes(code)) {
      errors.push(`${rel}: smoke run exited ${code}, expected one of [${allowed.join(", ")}]`);
    }
    const combined = (result.stdout ?? "") + (result.stderr ?? "");
    for (const needle of contract.smoke.output_includes ?? []) {
      if (!combined.includes(needle)) {
        errors.push(`${rel}: smoke output does not include "${needle}"`);
      }
    }
  }
}

/** Enforce a validated contracts block against a skill directory. */
export function enforceContracts(skillDir: string, contracts: ContractBlock): string[] {
  const errors: string[] = [];

  for (const rel of contracts.required_paths ?? []) {
    if (!fs.existsSync(path.join(skillDir, rel))) {
      errors.push(`required path missing: ${rel}`);
    }
  }

  const skillMdPath = path.join(skillDir, "SKILL.md");
  let skillMd: string | undefined;
  try {
    skillMd = fs.readFileSync(skillMdPath, "utf8");
  } catch {
    skillMd = undefined; // absence already reported by the universal checks
  }
  if (skillMd !== undefined) {
    for (const needle of contracts.skill_md_includes ?? []) {
      if (!skillMd.includes(needle)) {
        errors.push(`SKILL.md does not include "${needle}"`);
      }
    }
    for (const pattern of contracts.skill_md_matches ?? []) {
      try {
        if (!new RegExp(pattern, "i").test(skillMd)) {
          errors.push(`SKILL.md does not match /${pattern}/i`);
        }
      } catch (err) {
        errors.push(`invalid regex /${pattern}/: ${(err as Error).message}`);
      }
    }
  }

  for (const [rel, contract] of Object.entries(contracts.scripts ?? {})) {
    checkScript(skillDir, rel, contract, errors);
  }

  return errors;
}

// ---------------------------------------------------------------------------
// Per-skill and repo-wide runs
// ---------------------------------------------------------------------------

/**
 * Full deterministic check of one skill: universal document checks, then the
 * spec (missing spec and schema failures stop before enforcement), then every
 * declared contract.
 */
export function checkSkill(skillDir: string): string[] {
  const errors = checkSkillDocument(skillDir);
  const { spec, errors: specErrors } = loadSpec(skillDir);
  if (!spec) {
    return [...errors, ...specErrors];
  }
  return [...errors, ...enforceContracts(skillDir, spec.contracts)];
}

/** Run every discovered skill under `root` and aggregate the outcome. */
export function evaluateRepo(root: string = skillsRoot()): RepoResult {
  const rows: SkillRow[] = discoverSkills(root).map((skillDir) => {
    const errs = checkSkill(skillDir);
    return {
      skillName: path.basename(skillDir),
      skillDir,
      status: errs.length === 0 ? "pass" : "fail",
      errors: errs,
    };
  });
  const errors = rows.flatMap((row) => row.errors.map((e) => `${row.skillName}: ${e}`));
  return { ok: errors.length === 0, rows, errors };
}

/**
 * Human-readable summary: a PASS/FAIL table (skill paths shown relative to
 * `root`), a bulleted violation list, and a one-line verdict.
 */
export function renderSummary(result: RepoResult, root: string): string {
  const lines: string[] = ["RESULT  SKILL"];
  for (const row of result.rows) {
    const rel = path.relative(root, row.skillDir) || ".";
    lines.push(`${row.status === "pass" ? "PASS " : "FAIL "}   ${rel}`);
  }
  if (result.errors.length > 0) {
    lines.push("");
    for (const err of result.errors) lines.push(`- ${err}`);
  }
  lines.push("");
  lines.push(
    result.ok
      ? "All skills satisfy their contracts."
      : `${result.errors.length} violation(s) found.`,
  );
  return lines.join("\n");
}
