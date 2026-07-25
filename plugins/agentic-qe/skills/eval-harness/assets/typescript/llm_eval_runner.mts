/**
 * llm_eval_runner.mts — LLM-judge half of the skill eval harness.
 *
 * For every skill whose eval/evals.json carries a non-empty `evals` array:
 *   RUN    feed SKILL.md + reference context + the case prompt to a model and
 *          collect a candidate answer (REPEATS times, so flakiness becomes a
 *          pass-rate rather than a coin flip);
 *   GRADE  ask an LLM judge to verdict each assertion (PASS/FAIL + reason).
 *
 * Standalone ESM entrypoint — main() executes on import. Wire it to an npm
 * script, e.g.  "eval:llm": "tsx eval/llm_eval_runner.mts".
 *
 * Environment (all optional unless a provider needs it):
 *   EVAL_PROVIDER          portkey-gateway (default) | openai-compatible | anthropic
 *   PORTKEY_API_KEY / PORTKEY_BASE_URL / PORTKEY_MODEL        (gateway; /v1 auto-appended)
 *   OPENAI_COMPAT_API_KEY / OPENAI_COMPAT_BASE_URL / OPENAI_COMPAT_MODEL
 *   ANTHROPIC_API_KEY / ANTHROPIC_MODEL / ANTHROPIC_BASE_URL  (base URL optional)
 *   MAX_TOKENS=8192 (floor 256)   REPEATS=3 (min 1; odd default keeps the 0.5
 *   threshold unambiguous)        PASS_THRESHOLD=0.5 (clamped 0..1)
 *   BASELINE / BASELINE_BARE      A/B mode: rerun each case with empty skill
 *                                 instructions (bare also drops the context)
 *   DISCRIMINATION_MARGIN=0.25    ONLY_CASE=<id>   SKILL=<dir substring>
 *   CONCURRENCY=6 (global in-flight LLM-call cap)  SKILLS_ROOT
 *   REPORT=0|false disables persistence
 *   REPORT_DIR (default <repoRoot>/.cache/eval-reports)
 *
 * Exit codes: 0 every assertion meets PASS_THRESHOLD; 1 some fall below;
 * 2 configuration/usage errors (bad provider, missing env, no matching
 * skills) or an uncaught crash.
 *
 * Blast radius: R1 (writes report artifacts) + R3-adjacent LLM calls, which
 * is why the harness is meant to run behind an explicit npm script.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";

dotenv.config();

// ---------------------------------------------------------------------------
// Layout
// ---------------------------------------------------------------------------

const HERE = path.dirname(fileURLToPath(import.meta.url));
/** The harness lives at <repoRoot>/eval, so the repo root is one level up. */
const REPO_ROOT = path.resolve(HERE, "..");

const FILE_CLIP_CHARS = 16_000;
const DIR_EXCERPT_LINES = 45;

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

function envInt(name: string, fallback: number): number {
  const raw = process.env[name];
  if (raw === undefined || raw === "") return fallback;
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function envFloat(name: string, fallback: number): number {
  const raw = process.env[name];
  if (raw === undefined || raw === "") return fallback;
  const parsed = Number.parseFloat(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function envFlag(name: string): boolean {
  const raw = (process.env[name] ?? "").toLowerCase();
  return raw !== "" && raw !== "0" && raw !== "false";
}

function clamp(value: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, value));
}

const cfg = {
  provider: process.env.EVAL_PROVIDER ?? "portkey-gateway",
  maxTokens: Math.max(256, envInt("MAX_TOKENS", 8192)),
  repeats: Math.max(1, envInt("REPEATS", 3)),
  passThreshold: clamp(envFloat("PASS_THRESHOLD", 0.5), 0, 1),
  baselineBare: envFlag("BASELINE_BARE"),
  baseline: envFlag("BASELINE") || envFlag("BASELINE_BARE"), // bare implies baseline
  margin: envFloat("DISCRIMINATION_MARGIN", 0.25),
  onlyCase: process.env.ONLY_CASE ? Number.parseInt(process.env.ONLY_CASE, 10) : undefined,
  skillFilter: process.env.SKILL,
  concurrency: Math.max(1, envInt("CONCURRENCY", 6)),
  // REPORT unset -> enabled; REPORT=0|false -> disabled; anything else -> enabled.
  report: !["0", "false"].includes((process.env.REPORT ?? "").toLowerCase().trim()),
  reportDir: process.env.REPORT_DIR ?? path.join(REPO_ROOT, ".cache", "eval-reports"),
};

// ---------------------------------------------------------------------------
// Small utilities
// ---------------------------------------------------------------------------

function message(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function usageError(text: string): never {
  console.error(text);
  process.exit(2);
}

/** Global semaphore: bounds concurrent LLM calls across all skills/cases. */
class Gate {
  private active = 0;
  private readonly waiters: Array<() => void> = [];

  constructor(private readonly limit: number) {}

  async run<T>(task: () => Promise<T>): Promise<T> {
    if (this.active >= this.limit) {
      await new Promise<void>((resolve) => this.waiters.push(resolve));
    }
    this.active += 1;
    try {
      return await task();
    } finally {
      this.active -= 1;
      this.waiters.shift()?.();
    }
  }
}

const gate = new Gate(cfg.concurrency);

/**
 * Retry on transient failures: 5xx, 429, and errors with no HTTP status get
 * up to 4 retries with exponential backoff (1s/2s/4s/8s); other 4xx fail fast.
 */
async function withRetry(task: () => Promise<string>): Promise<string> {
  const delays = [1000, 2000, 4000, 8000];
  for (let attempt = 0; ; attempt++) {
    try {
      return await task();
    } catch (err) {
      const status = (err as { status?: number }).status;
      const transient = status === undefined || status === 429 || status >= 500;
      if (!transient || attempt >= delays.length) throw err;
      await sleep(delays[attempt]);
    }
  }
}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

type Role = "system" | "user";

interface Turn {
  role: Role;
  content: string;
}

type Caller = (turns: Turn[]) => Promise<string>;

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) usageError(`Missing required environment variable: ${name}`);
  return value;
}

function httpError(status: number, body: string): Error & { status: number } {
  const err = new Error(`HTTP ${status}: ${body.slice(0, 400)}`) as Error & { status: number };
  err.status = status;
  return err;
}

/**
 * Build the model caller for the configured provider. SDKs are imported
 * lazily (variable specifier) so only the provider in use must be installed.
 */
async function buildCaller(): Promise<{ call: Caller; model: string }> {
  switch (cfg.provider) {
    case "portkey-gateway": {
      const apiKey = requireEnv("PORTKEY_API_KEY");
      const model = requireEnv("PORTKEY_MODEL");
      let baseURL = requireEnv("PORTKEY_BASE_URL").replace(/\/+$/, "");
      if (!/\/v1$/.test(baseURL)) baseURL = `${baseURL}/v1`;
      const sdkName = "portkey-ai";
      const sdk = (await import(sdkName)) as { Portkey: new (opts: object) => any };
      const client = new sdk.Portkey({ apiKey, baseURL });
      const call: Caller = async (turns) => {
        const res = await client.chat.completions.create({
          model,
          temperature: 0,
          max_tokens: cfg.maxTokens,
          messages: turns.map((t) => ({ role: t.role, content: t.content })),
        });
        return String(res?.choices?.[0]?.message?.content ?? "");
      };
      return { call, model };
    }

    case "openai-compatible": {
      const apiKey = requireEnv("OPENAI_COMPAT_API_KEY");
      const model = requireEnv("OPENAI_COMPAT_MODEL");
      const baseURL = requireEnv("OPENAI_COMPAT_BASE_URL").replace(/\/+$/, "");
      const call: Caller = async (turns) => {
        const res = await fetch(`${baseURL}/v1/chat/completions`, {
          method: "POST",
          headers: {
            "content-type": "application/json",
            authorization: `Bearer ${apiKey}`,
          },
          body: JSON.stringify({
            model,
            temperature: 0,
            max_tokens: cfg.maxTokens,
            messages: turns.map((t) => ({ role: t.role, content: t.content })),
          }),
        });
        if (!res.ok) throw httpError(res.status, await res.text());
        const body = (await res.json()) as any;
        return String(body?.choices?.[0]?.message?.content ?? "");
      };
      return { call, model };
    }

    case "anthropic": {
      const apiKey = requireEnv("ANTHROPIC_API_KEY");
      const model = requireEnv("ANTHROPIC_MODEL");
      const baseURL = process.env.ANTHROPIC_BASE_URL;
      const sdkName = "@anthropic-ai/sdk";
      const sdk = (await import(sdkName)) as { default: new (opts: object) => any };
      const client = new sdk.default({ apiKey, ...(baseURL ? { baseURL } : {}) });
      const call: Caller = async (turns) => {
        // The messages API takes system content as a dedicated parameter, so
        // all system turns are concatenated into it.
        const system = turns
          .filter((t) => t.role === "system")
          .map((t) => t.content)
          .join("\n\n");
        const messages = turns
          .filter((t) => t.role !== "system")
          .map((t) => ({ role: "user" as const, content: t.content }));
        const res = await client.messages.create({
          model,
          temperature: 0,
          max_tokens: cfg.maxTokens,
          ...(system ? { system } : {}),
          messages,
        });
        return (res?.content ?? [])
          .filter((block: { type: string }) => block.type === "text")
          .map((block: { text: string }) => block.text)
          .join("");
      };
      return { call, model };
    }

    default:
      usageError(
        `Unknown EVAL_PROVIDER "${cfg.provider}" — expected portkey-gateway | openai-compatible | anthropic`,
      );
  }
}

// ---------------------------------------------------------------------------
// Skill discovery + spec reading (lenient — the deterministic layer owns
// strict schema validation)
// ---------------------------------------------------------------------------

interface JudgedAssertion {
  name: string;
  description: string;
}

interface LlmCase {
  id: number;
  prompt: string;
  expected_output?: string;
  files?: string[];
  assertions: JudgedAssertion[];
}

interface LlmSpec {
  skill_name?: string;
  context_files?: string[];
  evals?: LlmCase[];
}

function skillsRoot(): string {
  const custom = process.env.SKILLS_ROOT;
  return custom ? path.resolve(REPO_ROOT, custom) : path.join(REPO_ROOT, ".claude");
}

function discoverSkillDirs(root: string): string[] {
  const found: string[] = [];
  const walk = (dir: string): void => {
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    if (entries.some((e) => e.isFile() && e.name === "SKILL.md")) {
      found.push(dir);
      return;
    }
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      if (entry.name.startsWith(".")) continue;
      if (entry.name === "node_modules" || entry.name === "evals-workspace") continue;
      walk(path.join(dir, entry.name));
    }
  };
  walk(root);
  return found.sort();
}

function readSpec(skillDir: string): LlmSpec | undefined {
  try {
    const raw = fs.readFileSync(path.join(skillDir, "eval", "evals.json"), "utf8");
    const parsed = JSON.parse(raw);
    return typeof parsed === "object" && parsed !== null ? (parsed as LlmSpec) : undefined;
  } catch {
    return undefined;
  }
}

// ---------------------------------------------------------------------------
// Reference context assembly
// ---------------------------------------------------------------------------

function collectNestedMarkdown(dir: string): string[] {
  const out: string[] = [];
  const walk = (d: string): void => {
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(d, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      const abs = path.join(d, entry.name);
      if (entry.isDirectory()) walk(abs);
      else if (entry.isFile() && entry.name.endsWith(".md")) out.push(abs);
    }
  };
  walk(dir);
  return out.sort();
}

function resolveInput(skillDir: string, rel: string): string | undefined {
  for (const base of [skillDir, REPO_ROOT]) {
    const abs = path.resolve(base, rel);
    if (fs.existsSync(abs)) return abs;
  }
  return undefined;
}

function clip(text: string): string {
  return text.length > FILE_CLIP_CHARS
    ? `${text.slice(0, FILE_CLIP_CHARS)}\n[... truncated at ${FILE_CLIP_CHARS} chars ...]`
    : text;
}

/**
 * Inline every context path: files whole (clipped), directories as a catalog
 * of first-N-line excerpts of every nested .md, missing paths noted inline.
 */
function buildContext(skillDir: string, inputs: string[]): string {
  const chunks: string[] = [];
  for (const rel of inputs) {
    const abs = resolveInput(skillDir, rel);
    if (!abs) {
      chunks.push(`--- MISSING PATH: ${rel} ---`);
      continue;
    }
    let stat: fs.Stats;
    try {
      stat = fs.statSync(abs);
    } catch {
      chunks.push(`--- MISSING PATH: ${rel} ---`);
      continue;
    }
    if (stat.isDirectory()) {
      for (const md of collectNestedMarkdown(abs)) {
        let head: string;
        try {
          head = fs.readFileSync(md, "utf8").split(/\r?\n/).slice(0, DIR_EXCERPT_LINES).join("\n");
        } catch {
          continue;
        }
        const label = path.relative(REPO_ROOT, md) || md;
        chunks.push(`--- EXCERPT (first ${DIR_EXCERPT_LINES} lines): ${label} ---\n${head}`);
      }
    } else {
      let body: string;
      try {
        body = fs.readFileSync(abs, "utf8");
      } catch (err) {
        chunks.push(`--- UNREADABLE PATH: ${rel} (${message(err)}) ---`);
        continue;
      }
      chunks.push(`--- FILE: ${rel} ---\n${clip(body)}`);
    }
  }
  return chunks.join("\n\n");
}

// ---------------------------------------------------------------------------
// RUN prompt
// ---------------------------------------------------------------------------

const RUN_PREAMBLE = [
  "You are an AI coding agent. Execute the skill whose instructions appear below.",
  "This is a single-turn evaluation, so:",
  "- Do not stop at clarifying questions; pick sensible defaults and keep going.",
  "- Be concrete: name the file paths, structure, and content of every artifact you would produce.",
  "- Treat the reference context as the files actually present at runtime.",
  "- Never overwrite existing material silently; say what would change and why.",
  "- If an instruction cannot be followed exactly, take the fallback the skill documents.",
  "- Never fabricate tool or command output; state the exact commands you intend to run instead.",
  "- Finish the task within this single reply.",
].join("\n");

function systemTurns(skillMd: string, context: string): Turn[] {
  const turns: Turn[] = [{ role: "system", content: RUN_PREAMBLE }];
  if (context) {
    turns.push({
      role: "system",
      content: `REFERENCE CONTEXT (treat these as the runtime files):\n\n${context}`,
    });
  }
  if (skillMd) {
    turns.push({ role: "system", content: `SKILL INSTRUCTIONS:\n\n${skillMd}` });
  }
  return turns;
}

interface Candidate {
  ok: boolean;
  text: string;
}

async function generateCandidate(call: Caller, sys: Turn[], prompt: string): Promise<Candidate> {
  try {
    const text = await gate.run(() => withRetry(() => call([...sys, { role: "user", content: prompt }])));
    return { ok: true, text };
  } catch (err) {
    return { ok: false, text: `[candidate generation failed: ${message(err)}]` };
  }
}

// ---------------------------------------------------------------------------
// GRADE prompt + defensive verdict parsing
// ---------------------------------------------------------------------------

const JUDGE_SYSTEM = [
  "You grade ONE assertion about a candidate answer that an AI agent produced.",
  "Calibration rules:",
  "- Judge only the core behavior the assertion describes; ignore style, tone, length, and formatting.",
  "- Where the assertion permits planning, clearly stated intent counts as doing.",
  "- Accept synonyms and paraphrases; exact wording is required only when the assertion demands it.",
  "- The SOURCE MATERIAL block is ground truth for any verbatim or citation check.",
  "- A FAIL verdict must cite the specific missing or incorrect element.",
  'Reply with exactly one line of JSON: {"strengths": "...", "weaknesses": "...", "reason": "...", "verdict": "PASS" or "FAIL"}',
].join("\n");

const JUDGE_STRICT_ADDENDUM =
  "\n\nRespond with the single-line JSON object ONLY — no prose, no code fences, nothing else.";

interface ParsedVerdict {
  verdict: "PASS" | "FAIL";
  reason: string;
}

function deFence(reply: string): string {
  return reply
    .trim()
    .replace(/^```[a-z]*\s*/i, "")
    .replace(/\s*```$/, "")
    .trim();
}

/** Defensive verdict extraction; returns undefined only when nothing works. */
function parseVerdict(reply: string): ParsedVerdict | undefined {
  const text = deFence(reply);

  const fromJson = (candidate: string): ParsedVerdict | undefined => {
    try {
      const obj = JSON.parse(candidate) as Record<string, unknown>;
      if (obj && typeof obj === "object") {
        const verdict = String(obj.verdict ?? "").toUpperCase();
        if (verdict === "PASS" || verdict === "FAIL") {
          return { verdict, reason: String(obj.reason ?? "") };
        }
      }
    } catch {
      /* fall through */
    }
    return undefined;
  };

  // 1. Strict JSON of the de-fenced reply.
  const whole = fromJson(text);
  if (whole) return whole;

  // 2. First {...} substring.
  const braces = /\{[\s\S]*\}/.exec(text);
  if (braces) {
    const inner = fromJson(braces[0]);
    if (inner) return inner;
  }

  // 3. Regex on the verdict field.
  const field = /"?verdict"?\s*[:=]\s*"?(PASS|FAIL)"?/i.exec(text);
  if (field) {
    return { verdict: field[1].toUpperCase() as "PASS" | "FAIL", reason: text.slice(0, 300) };
  }

  // 4. Bare leading PASS/FAIL token.
  const bare = /^\s*(PASS|FAIL)\b/i.exec(text);
  if (bare) {
    return { verdict: bare[1].toUpperCase() as "PASS" | "FAIL", reason: text.slice(0, 300) };
  }

  return undefined;
}

interface VerdictRecord {
  name: string;
  verdict: "PASS" | "FAIL" | "RUN_ERROR";
  reason: string;
}

/** Grade one assertion. Never throws — call errors become FAIL verdicts. */
async function judge(
  call: Caller,
  sourcePrompt: string,
  assertion: JudgedAssertion,
  candidate: string,
): Promise<VerdictRecord> {
  const user = [
    "SOURCE MATERIAL (the original user prompt):",
    sourcePrompt,
    "",
    "ASSERTION TO GRADE:",
    assertion.description,
    "",
    "CANDIDATE ANSWER:",
    candidate,
  ].join("\n");

  try {
    let reply = await gate.run(() =>
      withRetry(() => call([{ role: "system", content: JUDGE_SYSTEM }, { role: "user", content: user }])),
    );
    let parsed = parseVerdict(reply);
    if (!parsed) {
      // One stricter re-ask before giving up.
      reply = await gate.run(() =>
        withRetry(() =>
          call([
            { role: "system", content: JUDGE_SYSTEM + JUDGE_STRICT_ADDENDUM },
            { role: "user", content: user },
          ]),
        ),
      );
      parsed = parseVerdict(reply);
    }
    if (!parsed) {
      return { name: assertion.name, verdict: "FAIL", reason: "judge reply unparseable" };
    }
    return { name: assertion.name, verdict: parsed.verdict, reason: parsed.reason };
  } catch (err) {
    return { name: assertion.name, verdict: "FAIL", reason: `judge call failed: ${message(err)}` };
  }
}

// ---------------------------------------------------------------------------
// Report shapes
// ---------------------------------------------------------------------------

interface RunEntry {
  run: number;
  candidate: string;
  verdicts: VerdictRecord[];
}

interface AssertionReport {
  name: string;
  description: string;
  passes: number;
  total: number;
  rate: number;
  mark: "PASS" | "FLAKY" | "FAIL";
  lastFailReason?: string;
  baselinePasses?: number;
  baselineTotal?: number;
  baselineRate?: number;
  delta?: number;
  nonDiscriminating?: boolean;
}

interface CaseReport {
  id: number;
  prompt: string;
  expected_output: string;
  assertions: AssertionReport[];
  runs: RunEntry[];
}

interface SkillReport {
  skill_name: string;
  skill_dir: string;
  cases: CaseReport[];
}

interface RunReport {
  generated_at: string;
  provider: string;
  model: string;
  repeats: number;
  pass_threshold: number;
  only_case: number | null;
  skill_filter: string | null;
  baseline: boolean;
  baseline_bare?: boolean;
  discrimination_margin?: number;
  non_discriminating?: string[];
  summary: {
    assertions_total: number;
    fully_passed: number;
    above_threshold: number;
    passed: boolean;
  };
  skills: SkillReport[];
}

// ---------------------------------------------------------------------------
// Case execution
// ---------------------------------------------------------------------------

async function executeRuns(
  call: Caller,
  sys: Turn[],
  evalCase: LlmCase,
): Promise<RunEntry[]> {
  const candidates = await Promise.all(
    Array.from({ length: cfg.repeats }, () => generateCandidate(call, sys, evalCase.prompt)),
  );
  return Promise.all(
    candidates.map(async (candidate, idx): Promise<RunEntry> => {
      let verdicts: VerdictRecord[];
      if (!candidate.ok) {
        verdicts = evalCase.assertions.map((a) => ({
          name: a.name,
          verdict: "RUN_ERROR" as const,
          reason: candidate.text,
        }));
      } else {
        verdicts = await Promise.all(
          evalCase.assertions.map((a) => judge(call, evalCase.prompt, a, candidate.text)),
        );
      }
      return { run: idx + 1, candidate: candidate.text, verdicts };
    }),
  );
}

function passCount(runs: RunEntry[], name: string): number {
  return runs.filter((r) => r.verdicts.find((v) => v.name === name)?.verdict === "PASS").length;
}

function lastFail(runs: RunEntry[], name: string): string | undefined {
  for (let i = runs.length - 1; i >= 0; i--) {
    const verdict = runs[i].verdicts.find((v) => v.name === name);
    if (verdict && verdict.verdict !== "PASS") return verdict.reason;
  }
  return undefined;
}

function summarizeAssertion(
  assertion: JudgedAssertion,
  runs: RunEntry[],
  baselineRuns?: RunEntry[],
): AssertionReport {
  const passes = passCount(runs, assertion.name);
  const total = runs.length;
  const rate = total > 0 ? passes / total : 0;
  const mark: AssertionReport["mark"] =
    passes === total ? "PASS" : rate >= cfg.passThreshold ? "FLAKY" : "FAIL";

  const report: AssertionReport = {
    name: assertion.name,
    description: assertion.description,
    passes,
    total,
    rate,
    mark,
  };
  const failReason = lastFail(runs, assertion.name);
  if (failReason !== undefined) report.lastFailReason = failReason;

  if (baselineRuns) {
    const bPasses = passCount(baselineRuns, assertion.name);
    const bTotal = baselineRuns.length;
    const bRate = bTotal > 0 ? bPasses / bTotal : 0;
    report.baselinePasses = bPasses;
    report.baselineTotal = bTotal;
    report.baselineRate = bRate;
    report.delta = rate - bRate;
    // Diagnostic only: an assertion the baseline already clears, without a
    // clear improvement from the skill, does not discriminate. Never gates.
    report.nonDiscriminating = bRate >= cfg.passThreshold && report.delta < cfg.margin;
  }

  return report;
}

async function runCase(
  call: Caller,
  skillDir: string,
  skillMd: string,
  spec: LlmSpec,
  evalCase: LlmCase,
): Promise<CaseReport> {
  const context = buildContext(skillDir, [...(spec.context_files ?? []), ...(evalCase.files ?? [])]);
  const runs = await executeRuns(call, systemTurns(skillMd, context), evalCase);

  let baselineRuns: RunEntry[] | undefined;
  if (cfg.baseline) {
    // Plain baseline keeps the reference context; bare drops that too.
    const baselineSys = systemTurns("", cfg.baselineBare ? "" : context);
    baselineRuns = await executeRuns(call, baselineSys, evalCase);
  }

  const assertions = evalCase.assertions.map((a) => summarizeAssertion(a, runs, baselineRuns));

  return {
    id: evalCase.id,
    prompt: evalCase.prompt,
    expected_output: evalCase.expected_output ?? "",
    assertions,
    runs,
  };
}

// ---------------------------------------------------------------------------
// Console output
// ---------------------------------------------------------------------------

function pct(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

function printCase(skillName: string, report: CaseReport): void {
  console.log(`\n== ${skillName} :: case ${report.id} ==`);
  for (const run of report.runs) {
    const passed = run.verdicts.filter((v) => v.verdict === "PASS").length;
    console.log(`  run ${run.run}: ${passed}/${run.verdicts.length} assertions passed`);
  }
  for (const a of report.assertions) {
    let tail = "";
    if (a.mark !== "PASS" && a.lastFailReason) {
      tail += ` — last fail: ${a.lastFailReason.slice(0, 160)}`;
    }
    if (a.baselineRate !== undefined && a.delta !== undefined) {
      tail += ` [baseline ${pct(a.baselineRate)}, delta ${a.delta >= 0 ? "+" : ""}${pct(a.delta)}${
        a.nonDiscriminating ? ", NON-DISCRIMINATING" : ""
      }]`;
    }
    console.log(`  [${a.mark}] ${a.name}: ${a.passes}/${a.total} (${pct(a.rate)})${tail}`);
  }
}

// ---------------------------------------------------------------------------
// Report persistence
// ---------------------------------------------------------------------------

function renderMarkdown(report: RunReport): string {
  const lines: string[] = [];
  lines.push("# Skill eval report");
  lines.push("");
  lines.push(`- Generated: ${report.generated_at}`);
  lines.push(`- Provider: ${report.provider} (${report.model})`);
  lines.push(`- Repeats: ${report.repeats}, pass threshold: ${report.pass_threshold}`);
  if (report.only_case !== null) lines.push(`- Case filter: ${report.only_case}`);
  if (report.skill_filter !== null) lines.push(`- Skill filter: ${report.skill_filter}`);
  if (report.baseline) {
    lines.push(
      `- Baseline A/B: on${report.baseline_bare ? " (bare)" : ""}, margin ${report.discrimination_margin}`,
    );
  }
  lines.push("");
  lines.push("## Summary");
  lines.push("");
  lines.push(`- Assertions: ${report.summary.assertions_total}`);
  lines.push(`- Fully passed: ${report.summary.fully_passed}`);
  lines.push(`- At/above threshold: ${report.summary.above_threshold}`);
  lines.push(`- Overall: ${report.summary.passed ? "PASS" : "FAIL"}`);
  lines.push("");

  if (report.non_discriminating && report.non_discriminating.length > 0) {
    lines.push("## Non-discriminating assertions");
    lines.push("");
    lines.push("> The baseline already clears these and the skill adds less than the margin —");
    lines.push("> tighten the assertion or the case. Diagnostic only; never gates the run.");
    lines.push("");
    for (const id of report.non_discriminating) lines.push(`- ${id}`);
    lines.push("");
  }

  for (const skill of report.skills) {
    lines.push(`## ${skill.skill_name}`);
    lines.push("");
    for (const c of skill.cases) {
      lines.push(`### Case ${c.id}`);
      lines.push("");
      lines.push(`**Prompt:** ${c.prompt}`);
      lines.push("");
      if (c.expected_output) {
        lines.push(`**Expected (prose, not graded):** ${c.expected_output}`);
        lines.push("");
      }
      const baselineCols = c.assertions.some((a) => a.baselineRate !== undefined);
      if (baselineCols) {
        lines.push("| Assertion | Mark | Passes | Rate | Baseline | Delta |");
        lines.push("|---|---|---|---|---|---|");
        for (const a of c.assertions) {
          lines.push(
            `| ${a.name} | ${a.mark} | ${a.passes}/${a.total} | ${pct(a.rate)} | ${pct(
              a.baselineRate ?? 0,
            )} | ${(a.delta ?? 0) >= 0 ? "+" : ""}${pct(a.delta ?? 0)}${a.nonDiscriminating ? " ⚠" : ""} |`,
          );
        }
      } else {
        lines.push("| Assertion | Mark | Passes | Rate |");
        lines.push("|---|---|---|---|");
        for (const a of c.assertions) {
          lines.push(`| ${a.name} | ${a.mark} | ${a.passes}/${a.total} | ${pct(a.rate)} |`);
        }
      }
      lines.push("");
      for (const run of c.runs) {
        const passed = run.verdicts.filter((v) => v.verdict === "PASS").length;
        lines.push("<details>");
        lines.push(`<summary>Run ${run.run} — ${passed}/${run.verdicts.length} passed</summary>`);
        lines.push("");
        for (const v of run.verdicts) {
          lines.push(`- **${v.name}**: ${v.verdict}${v.reason ? ` — ${v.reason}` : ""}`);
        }
        lines.push("");
        lines.push("````text");
        lines.push(run.candidate);
        lines.push("````");
        lines.push("");
        lines.push("</details>");
        lines.push("");
      }
    }
  }
  return lines.join("\n");
}

function writeReports(report: RunReport): void {
  try {
    fs.mkdirSync(cfg.reportDir, { recursive: true });
    const stamp = report.generated_at.replace(/[:.]/g, "-");
    const json = JSON.stringify(report, null, 2);
    const md = renderMarkdown(report);
    fs.writeFileSync(path.join(cfg.reportDir, `${stamp}.json`), json);
    fs.writeFileSync(path.join(cfg.reportDir, `${stamp}.md`), md);
    fs.writeFileSync(path.join(cfg.reportDir, "latest.json"), json);
    fs.writeFileSync(path.join(cfg.reportDir, "latest.md"), md);
    console.log(`\nReport written to ${cfg.reportDir}`);
  } catch (err) {
    // Persistence is best-effort; the console output and exit code stand.
    console.error(`Report write failed (non-fatal): ${message(err)}`);
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<number> {
  const root = skillsRoot();

  // Target discovery happens before any credential check so a credential-less
  // invocation still tells you what WOULD run.
  interface Target {
    skillDir: string;
    spec: LlmSpec;
    cases: LlmCase[];
  }

  const targets: Target[] = [];
  for (const skillDir of discoverSkillDirs(root)) {
    if (cfg.skillFilter && !skillDir.includes(cfg.skillFilter)) continue;
    const spec = readSpec(skillDir);
    if (!spec || !Array.isArray(spec.evals) || spec.evals.length === 0) continue;
    const cases = spec.evals.filter(
      (c) => cfg.onlyCase === undefined || Number.isNaN(cfg.onlyCase) || c.id === cfg.onlyCase,
    );
    if (cases.length === 0) continue;
    targets.push({ skillDir, spec, cases });
  }

  if (targets.length === 0) {
    console.error(
      `No skills with LLM eval cases found under ${root}` +
        (cfg.skillFilter ? ` (SKILL filter: "${cfg.skillFilter}")` : "") +
        (cfg.onlyCase !== undefined ? ` (ONLY_CASE: ${cfg.onlyCase})` : ""),
    );
    return 2;
  }

  console.log(
    `LLM eval run — provider=${cfg.provider}, repeats=${cfg.repeats}, ` +
      `threshold=${cfg.passThreshold}, concurrency=${cfg.concurrency}` +
      (cfg.baseline ? `, baseline=${cfg.baselineBare ? "bare" : "plain"}` : ""),
  );
  console.log("Targets:");
  for (const t of targets) {
    console.log(`  - ${path.relative(REPO_ROOT, t.skillDir)} (${t.cases.length} case(s))`);
  }

  const { call, model } = await buildCaller();

  const skillReports: SkillReport[] = [];
  for (const target of targets) {
    const skillMd = fs.readFileSync(path.join(target.skillDir, "SKILL.md"), "utf8");
    const skillName = target.spec.skill_name ?? path.basename(target.skillDir);
    const caseReports: CaseReport[] = [];
    for (const evalCase of target.cases) {
      const report = await runCase(call, target.skillDir, skillMd, target.spec, evalCase);
      printCase(skillName, report);
      caseReports.push(report);
    }
    skillReports.push({
      skill_name: skillName,
      skill_dir: path.relative(REPO_ROOT, target.skillDir),
      cases: caseReports,
    });
  }

  const allAssertions = skillReports.flatMap((s) =>
    s.cases.flatMap((c) => c.assertions.map((a) => ({ skill: s.skill_name, caseId: c.id, a }))),
  );
  const aboveThreshold = allAssertions.filter(({ a }) => a.rate >= cfg.passThreshold);
  const passed = aboveThreshold.length === allAssertions.length;

  const nonDiscriminating = allAssertions
    .filter(({ a }) => a.nonDiscriminating)
    .map(({ skill, caseId, a }) => `${skill}#${caseId}:${a.name}`);

  const report: RunReport = {
    generated_at: new Date().toISOString(),
    provider: cfg.provider,
    model,
    repeats: cfg.repeats,
    pass_threshold: cfg.passThreshold,
    only_case: cfg.onlyCase !== undefined && !Number.isNaN(cfg.onlyCase) ? cfg.onlyCase : null,
    skill_filter: cfg.skillFilter ?? null,
    baseline: cfg.baseline,
    ...(cfg.baseline
      ? {
          baseline_bare: cfg.baselineBare,
          discrimination_margin: cfg.margin,
          non_discriminating: nonDiscriminating,
        }
      : {}),
    summary: {
      assertions_total: allAssertions.length,
      fully_passed: allAssertions.filter(({ a }) => a.mark === "PASS").length,
      above_threshold: aboveThreshold.length,
      passed,
    },
    skills: skillReports,
  };

  console.log(
    `\nOverall: ${passed ? "PASS" : "FAIL"} — ${aboveThreshold.length}/${allAssertions.length} ` +
      `assertion(s) at/above threshold ${cfg.passThreshold}`,
  );

  if (cfg.report) writeReports(report);

  return passed ? 0 : 1;
}

main().then(
  (code) => process.exit(code),
  (err) => {
    console.error(`Uncaught error: ${message(err)}`);
    process.exit(2);
  },
);
