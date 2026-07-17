# Review a PR for performance risk

Turn every pull-request diff into a line-anchored performance assessment — a four-level verdict plus prioritized fixes — so regressions get caught at review time instead of surfacing as production incidents or expensive load-test findings.

## When to use this

- **Reach for it when** you run a JVM-language (Java/Kotlin) backend where performance defects slip past reviewers who focus on logic and style; the repo documents its hot paths and non-functional targets so severity can be judged in context; the team wants automatic pre-merge feedback on every change at low average cost; and the project is mature enough (settled architecture, PR workflow, merged history) to pattern-match against.
- **Skip it when** the project is greenfield with no performance context yet — write down hot paths and target latencies first, run the agent loosely on early PRs to accumulate suppression rules, then adopt the full pipeline. Also skip diffs with no JVM-language source changes (the detection rules target that stack), and skip it entirely if you need measured runtime numbers — this is static heuristic review, not load testing or profiling.
- **Outcome** — each qualifying PR gets an automated report grading the change *improvement / neutral / risk / regression*, with per-line findings across seven performance concern areas and remediation advice specific to your codebase, posted before anyone clicks merge.

> Scope is deliberately narrow: performance only (not logic, style, or security), changed lines plus a small hotspot set (not the whole codebase), advisory output only (it never edits source, approves, blocks, or merges).

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Read access to the git hosting platform (token or MCP connector for PR metadata and file diffs) | The pipeline starts by pulling the change set; nothing runs without it | Platform admin issues a token scoped to repository read |
| Python 3.10+ with standard library only | The first analysis pass is a deterministic regex engine running locally at zero model cost | Local machine or CI runner |
| Performance context document committed to the repo (hot paths, latency/throughput targets, known bottlenecks) | Lets the model tell a database call in a cold admin path (harmless) from the same call in a high-throughput consumer (risky); without it every finding collapses to generic severity | Team authors and maintains it in the repository |
| Writable report output directory; optional chat webhook and knowledge-base write access | Reports persist per run and can be broadcast to the team | Repo/CI configuration |

## Agent design

The pipeline is two-phase by design: a free deterministic scan filters every diff first, and a model pass runs only when that scan (or hot-path proximity) says the PR is worth reading. An orchestrator sequences the run and a publisher handles all external writes.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Orchestrator | Validates preconditions, fetches the change set, invokes the scanner, decides whether the model pass is warranted, hands results to the publisher; interactive sessions can redirect it, unattended runs pin the exact sequence | standard | PR metadata, unified diff, precondition state | Saved diff fixture, run-state artifacts | R1 |
| Pattern scanner (first pass) | No model at all — a regex engine over added diff lines in JVM-stack files, covering three high-confidence groups: heavy operations (data-store calls, IO creation), memory footprint (uncapacitied collections, large allocations), inefficient constructs (loop string building, sleeps, synchronization, serialization). Limited to context-independent patterns to keep false positives low; finishes in seconds, catches roughly two-thirds of common anti-patterns | economy | Added diff lines only | Structured findings: file, line, severity (high/medium/low), category, recommendation, excerpt | R1 |
| Deep analyst (second pass) | Model-driven enrichment over first-pass findings, the top ~10 hotspot files, and the performance context doc: cross-file reasoning (N+1 spanning service and repository layers), architecture impact, business-context prioritization, and the four-level verdict via a fixed decision matrix. Runs once per PR, not per line; escalate to premium when finding counts are large | standard | First-pass findings, hotspot file contents, performance context doc | Enriched findings, verdict, before/after category table, prioritized recommendations | R1 |
| Report publisher | Renders a fixed seven-section HTML report (impact assessment, change summary, findings, positive patterns, per-file impact, recommendations, proactive engineering), writes it to the report directory, posts a fresh PR comment with an explicit AI-generated label, applies a review label where supported, optionally pings team chat on risk verdicts | economy | Analyst output | Local HTML file, new PR/MR comment, platform label, optional chat message | R3 |

> The split makes spend proportional to risk: mechanical scanning and rendering sit on economy, cross-file judgment sits on standard with a premium escape hatch, and clean diffs never touch a model at all.

## Flow

1. **Trigger** — PR opened or updated against mainline/release branches, or manual invocation with a PR identifier.
2. **Preconditions** — confirm the diff touches JVM-language sources, the performance context doc exists, and platform access works; otherwise stop.
3. **Fetch** — pull PR metadata and the unified diff; persist the combined diff locally so every run is reproducible.
4. **First pass** — deterministic scan of added lines emits structured findings in ~10–25 seconds at zero model cost.
5. **Cost gate** — if there are no findings and no hot-path files were touched, publish a neutral-verdict comment and stop; the model is never invoked.
6. **Second pass** — the analyst reads findings, hotspot files, and the performance doc; produces cross-file insights, architecture impact, prioritized recommendations, and the overall verdict.
7. **Publish** — write the HTML report, post a labeled PR comment (always a new one, never an edit), and alert team chat only on risk/regression verdicts.
8. **Human review gate** — developers weigh the report inside their normal PR review and, before merging, decide per recommendation: fix it, defer it with a tracked note, or dismiss it with rationale. The agent never blocks or approves the merge; the merge decision is entirely human.
9. **Feedback loop** — track adoption and acceptance; add suppression rules for noisy patterns or reduce trigger friction accordingly.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| fetch-change-set | Git hosting platform (both major cloud offerings) | Read | Official MCP connector; fall back to the official CLI diff command, then REST wrapped in a skill. Token needs repository-read scope only |
| run-static-scan | Local Python runtime | Read | Invoke the stdlib-only scanner module against the saved patch file; no network, no external packages |
| post-review-comment | PR/MR comment thread | Write | MCP connector with comment-create permission; always creates a new comment rather than editing prior ones |
| write-report | Local filesystem report directory | Write | Plain file write; embed PR number and date in the filename so runs can be compared over time |
| notify-team | Team chat and knowledge base (both optional) | Write | Chat MCP or incoming webhook posting verdict, finding count, and report link; fires only on risk/regression verdicts |

> Wiring preference, in order: official MCP connector → official CLI → REST wrapped in a skill → custom integration.

## Guardrails

- **Injection defense** — diff contents, code comments, and PR descriptions are untrusted data, never instructions. The first pass is a pure regex engine and cannot be steered by embedded text; the model pass must treat code text strictly as material to analyze. Trigger scoping doubles as loop protection: fire only on PR open/synchronize events, never on comment events, so the agent's own comment cannot re-trigger a run.
- **Writable-field allowlist** — permitted writes only: new report files in the designated output directory, one fresh PR comment per run (prior comments are never edited), an optional platform label, and optional chat/knowledge-base posts. Never repository source files; never approve, merge, block, or transition anything.
- **Human gate** — there is no pre-publish approval step; the gate sits at merge time. Reviewers check each finding against the actual change and record an explicit disposition — fix, tracked deferral, or dismissal with rationale — before merging.
- **Grounding** — every finding must anchor to a concrete file and line in the diff and carry a code-specific (not generic) recommendation. The model pass reads only first-pass output, a bounded hotspot set, and the repo's performance context doc — never the whole codebase. Verdicts follow a fixed decision matrix. The deterministic pass covers only patterns that are problematic regardless of context; anything context-dependent is deferred to the model. Never invent behaviors, targets, or hot paths absent from those inputs.

## Automation

Pin this into an unattended workflow once the interactive version is stable: fixed steps, pinned models, prompts, and tools per step — no on-the-fly tool selection.

Trigger → flow: *PR opened or commits pushed to mainline/release (webhook or CI hook carrying repo and PR number)* → fetch diff → deterministic scan → conditional model pass (only if findings exist or hot-path files were touched) → publish report + PR comment → chat alert only on risk/regression.

Two-phase gating keeps average spend to a small fraction of running a full model pass on every diff — typically well under a dollar or two per PR, and clean PRs cost nothing. Scope the trigger strictly to open/synchronize events so the bot's own comments never re-trigger it. Keep the merge-time human gate permanently — the agent is advisory by design; adoption and acceptance metrics tune trigger scope and suppression rules, not the gate itself.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption rate — share of merged PRs that received the automated review | Count PR comments bearing the agent's label/prefix versus total PRs merged per sprint |
| Turnaround gain — minutes from PR open to posted review versus manual baseline | Diff the PR-opened timestamp against the agent comment timestamp; compare with the team's estimate for a dedicated manual performance review (typically 30–60 minutes) |
| Acceptance rate — how often developers act on recommendations | Track follow-up fix commits, tracked deferrals, explicit dismissals with rationale, and comment reactions |
| Qualitative team feedback | Sprint retrospectives probing false-positive rate, recommendation specificity, verdict accuracy, and production escapes prevented |
| Tuning rule combining the two rates | High adoption + low acceptance → static patterns are noisy: add project-specific suppression rules (e.g., mute capacity warnings in test code). High acceptance + low adoption → trigger friction: make the workflow fire on every PR without manual invocation |
