#!/usr/bin/env python3
"""LLM-judge half of the skill eval harness.

For every skill whose <skill>/eval/evals.json declares a non-empty
"evals" array this CLI:

  RUN    — asks a candidate model to execute the skill for each case
           (system = execution directive + optional inlined reference
           context + SKILL.md; user = the case prompt);
  GRADE  — asks a judge model for a PASS/FAIL JSON verdict per assertion;
  REPEAT — runs each case REPEATS times; an assertion clears the gate
           when its pass-rate is at or above PASS_THRESHOLD.

The deterministic structural checks live in runner.py; both halves read
the same spec file. Dependencies: stdlib, plus python-dotenv if
installed, plus the SDK of the selected provider only (the generic
openai-compatible provider needs no SDK at all).

Environment:
  EVAL_PROVIDER          anthropic-portkey (default) | openai-compatible
                         | anthropic-native
  MAX_TOKENS             completion budget       (default 8192, floor 256)
  REPEATS                runs per case           (default 3, floor 1)
  PASS_THRESHOLD         gate pass-rate          (default 0.5, clamped 0..1)
  BASELINE / BASELINE_BARE   "1"/"true" enables A/B diagnostics
  DISCRIMINATION_MARGIN  baseline delta floor    (default 0.25, clamped 0..1)
  ONLY_CASE              run a single case id
  SKILL                  substring filter on the skill directory path
  CONCURRENCY            in-flight run units     (default 6, floor 1)
  SKILLS_ROOT            skills dir relative to repo root (default .claude)
  REPORT                 "0"/"false" disables report files
  REPORT_DIR             default <repoRoot>/.cache/eval-reports

Exit codes: 0 gate passed, 1 gate failed, 2 configuration error
(nothing to evaluate, unknown provider, missing credentials or SDK).
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:  # optional: load .env when python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------

def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_flag(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true")


def _env_only_case():
    raw = (os.environ.get("ONLY_CASE") or "").strip()
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return None


PROVIDER_NAME = (os.environ.get("EVAL_PROVIDER") or "anthropic-portkey").strip()
MAX_TOKENS = max(256, _env_int("MAX_TOKENS", 8192))
REPEATS = max(1, _env_int("REPEATS", 3))
PASS_THRESHOLD = _clamp(_env_float("PASS_THRESHOLD", 0.5), 0.0, 1.0)
BASELINE_BARE = _env_flag("BASELINE_BARE")
BASELINE = _env_flag("BASELINE") or BASELINE_BARE  # bare implies baseline
DISCRIMINATION_MARGIN = _clamp(_env_float("DISCRIMINATION_MARGIN", 0.25), 0.0, 1.0)
ONLY_CASE = _env_only_case()
SKILL_FILTER = (os.environ.get("SKILL") or "").strip()
CONCURRENCY = max(1, _env_int("CONCURRENCY", 6))
REPORT_ENABLED = (os.environ.get("REPORT") or "1").strip().lower() not in ("0", "false")
REPORT_DIR = Path(os.environ.get("REPORT_DIR") or (REPO_ROOT / ".cache" / "eval-reports"))

# Internal caps.
CONTEXT_FILE_CLIP = 16000        # chars per inlined context file
DIR_EXCERPT_LINES = 45           # lines per *.md file when a context path is a dir
MAX_RETRIES = 4                  # retryable model-call attempts after the first


# ---------------------------------------------------------------------------
# Providers — SDKs imported lazily, only for the provider actually chosen
# ---------------------------------------------------------------------------

def _ensure_v1_suffix(url: str) -> str:
    url = url.rstrip("/")
    if not url.endswith("/v1"):
        url += "/v1"
    return url


class GatewayChatProvider:
    """`anthropic-portkey`: model traffic mediated by an API gateway that
    speaks the chat-completions dialect."""

    REQUIRED_ENV = ("GATEWAY_API_KEY", "GATEWAY_BASE_URL", "GATEWAY_MODEL")

    def __init__(self):
        from openai import OpenAI  # lazy

        self.model = os.environ["GATEWAY_MODEL"]
        self._client = OpenAI(
            api_key=os.environ["GATEWAY_API_KEY"],
            base_url=_ensure_v1_suffix(os.environ["GATEWAY_BASE_URL"]),
        )

    def complete(self, messages) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
            max_tokens=MAX_TOKENS,
        )
        return response.choices[0].message.content or ""


class HttpChatProvider:
    """`openai-compatible`: any chat-completions endpoint, plain stdlib
    urllib — no SDK required."""

    REQUIRED_ENV = ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL")

    def __init__(self):
        base = os.environ["OPENAI_BASE_URL"].rstrip("/")
        if base.endswith("/chat/completions"):
            self.url = base
        elif base.endswith("/v1"):
            self.url = base + "/chat/completions"
        else:
            self.url = base + "/v1/chat/completions"
        self.model = os.environ["OPENAI_MODEL"]
        self._key = os.environ["OPENAI_API_KEY"]

    def complete(self, messages) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "temperature": 0,
                "max_tokens": MAX_TOKENS,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._key}",
            },
        )
        with urllib.request.urlopen(request, timeout=300) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"] or ""


class NativeMessagesProvider:
    """`anthropic-native`: the native messages API. System messages are
    merged into the `system` parameter."""

    REQUIRED_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL")

    def __init__(self):
        import anthropic  # lazy

        kwargs = {"api_key": os.environ["ANTHROPIC_API_KEY"]}
        base = os.environ.get("ANTHROPIC_BASE_URL")
        if base:
            kwargs["base_url"] = base
        self._client = anthropic.Anthropic(**kwargs)
        self.model = os.environ["ANTHROPIC_MODEL"]

    def complete(self, messages) -> str:
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        chat = [m for m in messages if m["role"] != "system"]
        kwargs = {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "temperature": 0,
            "messages": chat,
        }
        if system_parts:
            kwargs["system"] = "\n\n".join(system_parts)
        response = self._client.messages.create(**kwargs)
        return "".join(
            block.text
            for block in response.content
            if getattr(block, "type", "") == "text"
        )


PROVIDERS = {
    "anthropic-portkey": GatewayChatProvider,
    "openai-compatible": HttpChatProvider,
    "anthropic-native": NativeMessagesProvider,
}


def build_provider():
    """Instantiate the selected provider; config problems exit 2."""
    cls = PROVIDERS.get(PROVIDER_NAME)
    if cls is None:
        print(
            f"unknown EVAL_PROVIDER {PROVIDER_NAME!r}; expected one of {sorted(PROVIDERS)}",
            file=sys.stderr,
        )
        sys.exit(2)
    missing = [name for name in cls.REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        print(
            f"provider {PROVIDER_NAME!r} needs environment: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(2)
    try:
        return cls()
    except ImportError as exc:
        print(f"provider {PROVIDER_NAME!r} SDK not installed: {exc}", file=sys.stderr)
        sys.exit(2)


# ---------------------------------------------------------------------------
# Retry wrapper: 429/5xx/network are retryable, other HTTP errors fail fast
# ---------------------------------------------------------------------------

def _http_status(exc) -> int:
    for attr in ("status_code", "status", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    if response is not None:
        value = getattr(response, "status_code", None)
        if isinstance(value, int):
            return value
    return -1


def _retryable(exc) -> bool:
    status = _http_status(exc)
    if status >= 0:
        return status == 429 or 500 <= status <= 599
    return True  # no status: treat as a network-level failure


def call_model(provider, messages) -> str:
    """Provider call with exponential backoff (1s * 2^attempt)."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            return provider.complete(messages)
        except Exception as exc:
            if not _retryable(exc) or attempt == MAX_RETRIES:
                raise
            time.sleep(1.0 * (2 ** attempt))
    raise RuntimeError("unreachable")


# ---------------------------------------------------------------------------
# Discovery — same SKILL.md walk as runner.py, plus evals-workspace skip
# ---------------------------------------------------------------------------

SKIP_DIR_NAMES = {"node_modules", "evals-workspace"}


def skills_root() -> Path:
    override = os.environ.get("SKILLS_ROOT")
    if override:
        return (REPO_ROOT / override).resolve()
    return REPO_ROOT / ".claude"


def discover_skill_dirs(root: Path) -> list:
    found = []

    def walk(directory: Path) -> None:
        if (directory / "SKILL.md").is_file():
            found.append(directory)
            return
        try:
            children = sorted(directory.iterdir())
        except OSError:
            return
        for child in children:
            if not child.is_dir():
                continue
            if child.name.startswith(".") or child.name in SKIP_DIR_NAMES:
                continue
            walk(child)

    if root.is_dir():
        walk(root)
    return sorted(found)


def load_targets() -> list:
    """(skill_dir, spec) pairs for skills with a non-empty evals list."""
    targets = []
    for skill_dir in discover_skill_dirs(skills_root()):
        spec_path = skill_dir / "eval" / "evals.json"
        if not spec_path.is_file():
            continue
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        evals = spec.get("evals") if isinstance(spec, dict) else None
        if not isinstance(evals, list) or not evals:
            continue
        if SKILL_FILTER and SKILL_FILTER not in str(skill_dir):
            continue
        targets.append((skill_dir, spec))
    return targets


# ---------------------------------------------------------------------------
# Context loading
# ---------------------------------------------------------------------------

def _directory_excerpts(directory: Path) -> str:
    parts = []
    for md_file in sorted(directory.rglob("*.md")):
        try:
            head = md_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        excerpt = "\n".join(head[:DIR_EXCERPT_LINES])
        parts.append(
            f"### {md_file.relative_to(directory)} (first {DIR_EXCERPT_LINES} lines)\n{excerpt}"
        )
    return "\n\n".join(parts)


def load_context(skill_dir: Path, rel_paths) -> str:
    """Inline every context path: files clipped, directories excerpted,
    missing paths replaced by a placeholder block."""
    blocks = []
    for rel in rel_paths:
        target = skill_dir / rel
        if target.is_dir():
            body = _directory_excerpts(target)
        elif target.is_file():
            body = target.read_text(encoding="utf-8", errors="replace")
            if len(body) > CONTEXT_FILE_CLIP:
                body = body[:CONTEXT_FILE_CLIP] + "\n[... clipped ...]"
        else:
            body = "[reference not found on disk]"
        blocks.append(f"===== reference: {rel} =====\n{body}")
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

RUN_DIRECTIVE = """\
You are executing an agent skill in a single turn. Ground rules:
- Do not end on a clarifying question. When details are ambiguous, adopt the
  choices already supplied in the prompt and reference material, note the
  assumption in one line, and carry on to a finished answer.
- Produce the concrete artifact or structure the skill calls for; spell out
  its exact shape and content instead of a vague plan.
- Treat the reference material below as the live files of the runtime
  environment.
- Before overwriting anything, state that you would inspect its current
  content first and what you would check for.
- When nothing documented fits the request, apply the fallback the skill
  documentation prescribes and say that you are doing so.
- Never fabricate tool or command output. State the exact commands you would
  run and what you expect them to show."""

JUDGE_SYSTEM = """\
You evaluate ONE assertion about a candidate answer. Rules:
- Grade only the core behavior the assertion describes; ignore unrelated flaws.
- Synonyms and paraphrases count; exact wording is not required.
- For action assertions, a clearly stated intent to perform the action counts
  as satisfying it (the candidate cannot execute tools here).
- For citation assertions, check that the quoted text actually appears in the
  supplied source material.
- Return FAIL only when you can name a concrete, specific shortfall; vague
  doubt is not a FAIL.
Reply with a single compact JSON object and nothing else:
{"strengths": ["..."], "weaknesses": ["..."], "reason": "...", "verdict": "PASS" or "FAIL"}"""


def build_run_messages(skill_text: str, context_block: str, prompt: str,
                       baseline: bool, bare: bool) -> list:
    parts = [RUN_DIRECTIVE]
    if context_block and not bare:
        parts.append("REFERENCE MATERIAL:\n" + context_block)
    parts.append("SKILL INSTRUCTIONS:\n" + ("(none)" if baseline else skill_text))
    return [
        {"role": "system", "content": "\n\n".join(parts)},
        {"role": "user", "content": prompt},
    ]


# ---------------------------------------------------------------------------
# Verdict parsing — lenient; a parse miss must not silently become a FAIL
# ---------------------------------------------------------------------------

def _try_json(text: str):
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def parse_verdict(reply):
    """Extract {"verdict","reason"} from a judge reply, or None.

    Fallback ladder: strip code fences -> strict JSON -> first {...}
    substring -> regex on the verdict field -> bare leading PASS/FAIL.
    """
    text = (reply or "").strip()
    fenced = re.match(r"^```[A-Za-z]*\s*(.*?)\s*```\s*$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    parsed = _try_json(text)
    if parsed is None:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        if brace:
            parsed = _try_json(brace.group(0))
    if isinstance(parsed, dict):
        verdict = str(parsed.get("verdict", "")).strip().upper()
        if verdict in ("PASS", "FAIL"):
            return {"verdict": verdict, "reason": str(parsed.get("reason", ""))}
    field = re.search(r'"?verdict"?\s*[:=]\s*"?(PASS|FAIL)"?', text, re.IGNORECASE)
    if field:
        return {"verdict": field.group(1).upper(), "reason": text[:400]}
    bare = re.match(r"^(PASS|FAIL)\b", text, re.IGNORECASE)
    if bare:
        return {"verdict": bare.group(1).upper(), "reason": text[:400]}
    return None


def judge_once(provider, assertion: dict, candidate: str, source_material: str) -> dict:
    """One graded assertion. Never raises: judge-call exceptions and
    unparseable replies degrade to explicit FAIL verdicts."""
    user = (
        f"ASSERTION `{assertion.get('name', '?')}`:\n{assertion.get('description', '')}\n\n"
        f"SOURCE MATERIAL:\n{source_material}\n\n"
        f"CANDIDATE ANSWER:\n{candidate}"
    )
    try:
        reply = call_model(
            provider,
            [{"role": "system", "content": JUDGE_SYSTEM},
             {"role": "user", "content": user}],
        )
        parsed = parse_verdict(reply)
        if parsed is None:
            # One stricter retry before giving up on the reply format.
            reply = call_model(
                provider,
                [{"role": "system",
                  "content": JUDGE_SYSTEM + "\nReturn ONLY the JSON object. No prose, no code fences."},
                 {"role": "user", "content": user}],
            )
            parsed = parse_verdict(reply)
        if parsed is None:
            return {"verdict": "FAIL", "reason": "unparseable judge reply"}
        return parsed
    except Exception as exc:  # suite must never abort on a judge error
        return {"verdict": "FAIL", "reason": f"judge call failed: {exc}"}


# ---------------------------------------------------------------------------
# Execution units — (skill, case, repeat, variant) run + grade
# ---------------------------------------------------------------------------

def execute_unit(provider, unit: dict) -> dict:
    """RUN then GRADE one unit. A RUN failure marks every assertion of
    the case as a run-error (counts as a fail)."""
    try:
        candidate = call_model(
            provider,
            build_run_messages(
                unit["skill_text"],
                unit["context"],
                unit["prompt"],
                baseline=unit["variant"] != "skill",
                bare=unit["variant"] == "baseline-bare",
            ),
        )
    except Exception as exc:
        return {
            "candidate": "",
            "run_error": str(exc),
            "verdicts": [
                {"name": a.get("name", "?"), "verdict": "FAIL",
                 "reason": f"run step failed: {exc}"}
                for a in unit["assertions"]
            ],
        }
    verdicts = [
        {"name": a.get("name", "?"), **judge_once(provider, a, candidate, unit["source"])}
        for a in unit["assertions"]
    ]
    return {"candidate": candidate, "run_error": None, "verdicts": verdicts}


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

MARK_ICON = {"PASS": "✅", "FLAKY": "⚠️", "FAIL": "❌"}


def render_markdown(report: dict) -> str:
    lines = [
        f"# Skill eval report — {report['generated_at']}",
        "",
        f"- provider: `{report['provider']}`  model: `{report['model']}`",
        f"- repeats: {report['repeats']}  pass threshold: {report['pass_threshold']}",
        f"- gate: {'✅ PASS' if report['summary']['passed'] else '❌ FAIL'}"
        f" ({report['summary']['above_threshold']}/{report['summary']['assertions_total']}"
        f" assertions at/above threshold, {report['summary']['fully_passed']} fully passed)",
        "",
    ]
    for skill in report["skills"]:
        lines += [f"## {skill['skill_name']}", ""]
        for case in skill["cases"]:
            lines += [f"### Case {case['id']}: {case['prompt'][:80]}", ""]
            header = "| assertion | rate | mark |"
            divider = "| --- | --- | --- |"
            if report["baseline"]:
                header += " baseline | delta |"
                divider += " --- | --- |"
            lines += [header, divider]
            for assertion in case["assertions"]:
                row = (
                    f"| {assertion['name']} "
                    f"| {assertion['passes']}/{assertion['total']} ({assertion['rate']:.2f}) "
                    f"| {MARK_ICON[assertion['mark']]} {assertion['mark']} |"
                )
                if report["baseline"]:
                    row += (
                        f" {assertion.get('baseline_rate', 0.0):.2f} "
                        f"| {assertion.get('delta', 0.0):+.2f} |"
                    )
                lines.append(row)
            lines.append("")
            for run in case["runs"]:
                lines += [
                    f"<details><summary>run {run['run']} candidate output</summary>",
                    "",
                    "```text",
                    (run["candidate"] or "").replace("```", "` ` `"),
                    "```",
                    "",
                    "</details>",
                    "",
                ]
    if report["non_discriminating"]:
        lines += ["## Non-discriminating assertions", ""]
        lines += [f"- {item}" for item in report["non_discriminating"]]
        lines.append("")
    return "\n".join(lines)


def write_reports(report: dict) -> None:
    """Persist <UTC-stamp>.{json,md} and latest.{json,md}; failures are
    reported but never fatal."""
    if not REPORT_ENABLED:
        return
    try:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        as_json = json.dumps(report, indent=2)
        as_md = render_markdown(report)
        for name, payload in (
            (f"{stamp}.json", as_json),
            (f"{stamp}.md", as_md),
            ("latest.json", as_json),
            ("latest.md", as_md),
        ):
            (REPORT_DIR / name).write_text(payload, encoding="utf-8")
        print(f"\nreport: {REPORT_DIR / (stamp + '.md')}")
    except OSError as exc:
        print(f"report write failed (non-fatal): {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def main() -> int:
    targets = load_targets()
    if not targets:
        print(
            "nothing to evaluate: no skill matched with a non-empty 'evals' array",
            file=sys.stderr,
        )
        return 2

    # List the targets before touching credentials so a credential-less
    # invocation still shows what would run.
    print("evaluation targets:")
    for skill_dir, spec in targets:
        print(f"  - {spec.get('skill_name') or skill_dir.name}  ({skill_dir})")
    sys.stdout.flush()  # keep ordering sane when stdout is piped

    provider = build_provider()

    baseline_variant = "baseline-bare" if BASELINE_BARE else "baseline-ctx"

    # Assemble every (skill, case, repeat, variant) unit up front so one
    # shared pool bounds in-flight work across all skills.
    units = []
    skill_states = []
    for skill_index, (skill_dir, spec) in enumerate(targets):
        skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        cases = [
            case
            for case in spec.get("evals", [])
            if ONLY_CASE is None or case.get("id") == ONLY_CASE
        ]
        if not cases:
            continue
        state = {
            "skill_name": spec.get("skill_name") or skill_dir.name,
            "skill_dir": str(skill_dir),
            "index": skill_index,
            "cases": cases,
        }
        skill_states.append(state)
        shared_context = list(spec.get("context_files") or [])
        for case_index, case in enumerate(cases):
            context = load_context(
                skill_dir, shared_context + list(case.get("files") or [])
            )
            source = context + "\n\n" + skill_text
            variants = ["skill"] + ([baseline_variant] if BASELINE else [])
            for variant in variants:
                for repeat in range(REPEATS):
                    units.append(
                        {
                            "skill": skill_index,
                            "case": case_index,
                            "variant": variant,
                            "repeat": repeat,
                            "skill_text": skill_text,
                            "context": context,
                            "source": source,
                            "prompt": str(case.get("prompt", "")),
                            "assertions": list(case.get("assertions") or []),
                        }
                    )
    if not units:
        print("nothing to evaluate after ONLY_CASE filtering", file=sys.stderr)
        return 2

    results = {}
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = {pool.submit(execute_unit, provider, unit): unit for unit in units}
        for future in as_completed(futures):
            unit = futures[future]
            results[(unit["skill"], unit["case"], unit["variant"], unit["repeat"])] = (
                future.result()
            )

    # Aggregate, print, and build the report structure.
    report_skills = []
    all_assertion_rows = []
    non_discriminating = []
    for state in skill_states:
        print(
            f"\n== {state['skill_name']}  "
            f"[provider={PROVIDER_NAME} repeats={REPEATS} cases={len(state['cases'])}]"
        )
        report_cases = []
        for case_index, case in enumerate(state["cases"]):
            case_id = case.get("id")
            assertions = list(case.get("assertions") or [])
            runs = []
            for repeat in range(REPEATS):
                outcome = results[(state["index"], case_index, "skill", repeat)]
                n_pass = sum(1 for v in outcome["verdicts"] if v["verdict"] == "PASS")
                note = f" (run error: {outcome['run_error']})" if outcome["run_error"] else ""
                print(
                    f"  case {case_id} run {repeat + 1}: "
                    f"{n_pass}/{len(outcome['verdicts'])} assertions pass{note}"
                )
                runs.append(
                    {
                        "run": repeat + 1,
                        "candidate": outcome["candidate"],
                        "verdicts": outcome["verdicts"],
                    }
                )
            assertion_rows = []
            for a_index, assertion in enumerate(assertions):
                passes = sum(
                    1 for run in runs if run["verdicts"][a_index]["verdict"] == "PASS"
                )
                total = len(runs)
                rate = passes / total if total else 0.0
                mark = (
                    "PASS"
                    if passes == total
                    else ("FLAKY" if rate >= PASS_THRESHOLD else "FAIL")
                )
                last_fail = next(
                    (
                        run["verdicts"][a_index]["reason"]
                        for run in reversed(runs)
                        if run["verdicts"][a_index]["verdict"] == "FAIL"
                    ),
                    None,
                )
                row = {
                    "name": assertion.get("name", "?"),
                    "description": assertion.get("description", ""),
                    "passes": passes,
                    "total": total,
                    "rate": rate,
                    "mark": mark,
                    "last_fail": last_fail,
                }
                line = f"  {row['name']}: {passes}/{total} (rate {rate:.2f}) {mark}"
                if last_fail:
                    line += f" — last fail: {last_fail[:160]}"
                if BASELINE:
                    b_passes = sum(
                        1
                        for repeat in range(REPEATS)
                        if results[(state["index"], case_index, baseline_variant, repeat)]
                        ["verdicts"][a_index]["verdict"] == "PASS"
                    )
                    b_rate = b_passes / REPEATS
                    delta = rate - b_rate
                    row.update(
                        {
                            "baseline_passes": b_passes,
                            "baseline_total": REPEATS,
                            "baseline_rate": b_rate,
                            "delta": delta,
                        }
                    )
                    if b_rate >= PASS_THRESHOLD and delta < DISCRIMINATION_MARGIN:
                        non_discriminating.append(
                            f"{state['skill_name']} / case {case_id} / {row['name']}"
                        )
                    line += f"  [baseline {b_rate:.2f} delta {delta:+.2f}]"
                print(line)
                assertion_rows.append(row)
                all_assertion_rows.append(row)
            report_cases.append(
                {
                    "id": case_id,
                    "prompt": str(case.get("prompt", "")),
                    "expected_output": str(case.get("expected_output", "")),
                    "assertions": assertion_rows,
                    "runs": runs,
                }
            )
        report_skills.append(
            {
                "skill_name": state["skill_name"],
                "skill_dir": state["skill_dir"],
                "cases": report_cases,
            }
        )

    total_assertions = len(all_assertion_rows)
    fully_passed = sum(1 for row in all_assertion_rows if row["mark"] == "PASS")
    above_threshold = sum(
        1 for row in all_assertion_rows if row["rate"] >= PASS_THRESHOLD
    )
    passed = above_threshold == total_assertions
    print(
        f"\ntotals: {above_threshold}/{total_assertions} assertions at/above "
        f"threshold {PASS_THRESHOLD} ({fully_passed} fully passed) — "
        f"gate {'PASS' if passed else 'FAIL'}"
    )
    if BASELINE:
        print("\nbaseline diagnostic (informational only, never gates):")
        if non_discriminating:
            for item in non_discriminating:
                print(f"  non-discriminating: {item}")
        else:
            print("  every assertion discriminates against the baseline")

    report = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "provider": PROVIDER_NAME,
        "model": getattr(provider, "model", ""),
        "repeats": REPEATS,
        "pass_threshold": PASS_THRESHOLD,
        "only_case": ONLY_CASE,
        "skill_filter": SKILL_FILTER,
        "baseline": BASELINE,
        "baseline_bare": BASELINE_BARE,
        "discrimination_margin": DISCRIMINATION_MARGIN,
        "non_discriminating": non_discriminating,
        "summary": {
            "assertions_total": total_assertions,
            "fully_passed": fully_passed,
            "above_threshold": above_threshold,
            "passed": passed,
        },
        "skills": report_skills,
    }
    write_reports(report)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
