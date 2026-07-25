# Run AI static code analysis

Turn every opened or updated change request in a test-automation repo into a grounded, multi-lens pre-review — a top-level verdict plus anchored inline findings — so the human reviewer starts from triage, not from a raw diff.

## When to use this

- **Reach for it when** change requests pile up waiting for a human first pass and review latency is the bottleneck; AI-assisted test generation has made review the slowest step; you want each change checked against the linked story's acceptance criteria and the manual test case it implements; or human first-pass reviews vary by reviewer and keep missing the same repetitive defects (skipped assertions, brittle selectors, duplicated steps).
- **Skip it when** the repo is greenfield with no conventions or reference tests to anchor on (land 5-10 real tests first, extract the emergent patterns, document them, then enable); no stable convention resolves a story/test-case ID from the change request; a single-agent pilot run yields only generic advice detached from the repo, story, or test case (fix context before scaling); or you cannot get a service account with comment rights and an event source firing on open/update.
- **Outcome** — every change request arrives pre-reviewed with a severity-tiered verdict and precise, fix-suggesting inline comments. Humans keep the merge decision and spend attention on test-design judgment instead of mechanical checks; time-to-first-review drops.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Bot/service account + event source on change-request open/update, with diff-read and comment-create/update rights | Unattended runs and result publication; approve/block voting stays optional and off by default | Git hosting admin; event source = native webhook, a low-code flow on the platform connector, or a CI step on change-request builds |
| Read access to the test management system and work-item tracker | The intent lens needs the test case's steps/expected results and the story's description and acceptance criteria | Test-management / tracker administrators |
| In-repo conventions: root agent-instructions file (nested where useful), 2-3 reference tests, lint/format configs, style and contributing docs | Grounds the conventions lens in enforceable rules; without visible patterns the reviewer invents standards and posts noise | Repo maintainers, in whatever instruction format the agent tool reads |
| Deterministic link from change request to story and test case (branch prefix, title pattern, or required template field) | No extractable ID means no intent context — the intent lens goes blind | Team branching/template policy |
| Written agreement on scope (test code only vs broader) and advisory-only posture | Prevents scope creep and the failure mode where engineers mute a noisy bot | Team working agreement / retro decision |

## Agent design

Split the review into a planner, three parallel single-lens reviewers, a synthesiser that owns the per-finding quality bar, a slim run-level gate, and a publisher that touches the outside world. Judgment about *what to review* and the final merge call sit on premium; lens expansion and pruning are mechanical enough for standard; the gate and the poster are pure plumbing on economy.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Planner (triage) | Sizes the diff, picks applicable lenses (intent/conventions/quality always candidates; security/performance on demand), assigns per-lens files, repo search targets, and a comment budget; shortcuts trivial diffs to a quality-only pass; never comments itself | premium | Diff, changed files, story AC, test-case steps, repo layout | Internal per-lens plan object | R1 |
| Intent lens | Verifies every test-case step/expected result and each acceptance criterion is covered; flags missing assertions, skipped steps, scope drift | standard | Assigned diff slice, test-case steps, story AC | Candidate findings with file:line anchors | R1 |
| Conventions lens | Checks naming, placement, locator preference order, reuse of step definitions / page objects / fixtures, lint and template adherence; cites the specific rule or file behind each finding; searches the repo before claiming anything is absent | standard | Diff slice, instructions file, configs, reference tests, repo at head | Anchored findings with rule citations | R1 |
| Quality lens | Flags bugs, duplication, dead code, brittle selectors, hardcoded waits, anti-patterns; search-verifies duplication claims against the repo first | standard | Diff slice, repo checkout | Anchored candidate findings | R1 |
| Synthesiser (noise control) | Merges lens outputs, dedupes same-location findings, ranks by severity, drops anything unanchored, unverified, or lacking a one-line fix, skips linter-covered items, trims to budget (~8 inline + 1 summary; overflow to a further-observations list) | standard | All candidate findings | Ranked, budgeted review payload + drop statistics | R1 |
| Run gate (safety) | One check: if drops exceed the threshold (default 50%), suppress the entire review and emit telemetry — silence beats confident error. Does not re-apply per-finding rules | economy | Synthesiser drop statistics | One-line run record (posted-N vs suppressed-M-of-K), never shown on the change request | R1 |
| Publisher | Posts one summary (verdict first line, findings grouped by lens, must-fix / should-fix / nice-to-have markers) plus inline threads; idempotent on update — edits the prior summary in place, resolves threads whose lines vanished, never re-posts human-resolved items; marks comments machine-generated, applies a tracking label, links story and test-case URLs | economy | Final payload, stored comment IDs from prior runs | Summary comment, inline threads, tracking label | R3 |
| Human reviewer | Reads bot output alongside the diff, acts on or dismisses findings, holds sole approve/merge authority | premium | Bot review, diff, intent links | Merge decision, thread resolutions | R3 |

> The split exists to keep each lens narrow and verifiable while concentrating the quality bar in one place (the synthesiser) and the kill switch in another (the run gate). A monolithic reviewer blends lenses, skips verification, and cannot be suppressed piecewise.

## Flow

1. Event fires on change-request open/update; debounce with a ~30s quiet window so rapid pushes coalesce into one run.
2. Precondition check: story/test-case ID resolvable, conventions discoverable, changed files include test-automation code — otherwise stay silent or defer to another reviewer.
3. Retrieve: diff + changed files, change-request metadata, linked story (description, AC, attachments), linked test case (steps, expected results), repo checkout at head for searching, conventions files, latest CI status as advisory context only.
4. Planner triages: lens selection, per-lens file and search-target assignment, comment budget; trivial diffs shortcut to a single quality pass.
5. Intent, conventions, and quality lenses run in parallel; each anchors every finding to file:line and search-verifies any missing/duplicated claim against the repo before emitting it.
6. Synthesiser merges, dedupes, ranks, drops unanchored/unverified/fix-less findings, skips linter-covered issues, trims to budget.
7. Run gate: if more than the threshold share (default 50%) was dropped, suppress the whole review, emit telemetry, and wait for the next push — no in-run retry.
8. Publisher posts or in-place-edits the summary and inline threads, resolving stale threads and skipping human-dismissed ones; every comment carries a machine-generated marker and the change request gets a tracking label. (Bounded R3: comment surfaces only — see the writable-field allowlist.)
9. **Human review gate** — before the merge, the only irreversible action: the assigned reviewer reads the posted review, acts on or dismisses each finding, and alone approves/merges. The gate sits after publication because the artifact is only useful once posted; findings become blocking only after sustained adoption, one finding type at a time.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Fetch diff, changed files, title/description, branch, CI status | Git hosting platform (any major provider) | Read | Official MCP connector → official CLI → REST/SDK in a skill; needs diff-read scope |
| Fetch linked test case (ID, title, steps, expected results) | Test management system | Read | MCP or CLI where official; REST otherwise; ID from branch prefix / title / template field |
| Fetch linked story (description, AC, attachments) | Work-item tracker | Read | MCP or CLI; link followed from the change request or the test case |
| Repo as searchable context (step definitions, page objects, fixtures, conventions) | The automation repo itself | Read | Local checkout at the change request's head commit, managed by the agent runner |
| Post/edit summary + inline threads, apply tracking label | Git hosting platform | Write | Same connector family as the read side; comment-create/update rights, optional label rights; stored comment IDs enable idempotent edits |

> Wiring preference, in order: official MCP connector → official CLI → REST-in-a-skill → custom integration. Drop down a level only when the one above does not exist or lacks the needed scope.

## Guardrails

- **Injection defense** — fetched diff, ticket, and story text are review *data*, never instructions. Prevent self-trigger loops structurally: scope the webhook to open/update events (never the bot's own comment events), and scope any test-management trigger to status changes so an optional write-back cannot re-fire this or a sibling agent.
- **Writable-field allowlist** — the only R3 writes are: one top-level summary comment (edited in place, never duplicated), inline threads at file:line, and a tracking label. No merge, no approval vote by default, no repo writes. Test-management write-back exists but ships disabled.
- **Human gate** — the reviewer checks whether each finding is real, worth fixing, or dismissible, then makes the merge call; the bot is a first reviewer, never a gate. Promote a finding type to merge-blocking only after its acceptance rate stays consistently high, one type at a time.
- **Grounding** — every finding needs a file:line anchor and a concrete one-line fix; missing/duplicated claims must be search-verified against repo head; convention findings must cite their rule or source file; uncertainty must be labeled, not guessed; linter-enforced issues are excluded; and when too many findings fail these bars, suppress the whole run — a confidently wrong review must never reach the change request.

## Automation

Pin this as an unattended workflow once the manual pilot produces grounded output: trigger on change-request opened/updated via whatever event source the org already runs — native webhook, a low-code flow subscribed to the platform's pull-request trigger forwarding payloads to the agent endpoint (useful where webhook creation is restricted), or a CI step on change-request builds. Debounce to one run per push (~30s coalescing).

Trigger → flow: `CR opened/updated → retrieve diff + story + test case + repo context → planner picks lenses/targets/budget → lens reviewers in parallel → synthesiser merges and prunes → run gate (suppress or pass) → publisher posts/edits idempotently → human reads and merges.`

The unattended variant pins models, prompts, and tools per step — no on-the-fly tool selection — trading flexibility for predictability. A semi-automated variant triggers on an on-demand slash-style comment on the change request; use it during onboarding or where webhooks are locked down. Start advisory (comment-only) and keep the human gate until adoption metrics justify escalating specific finding types.

## Signals it's working

| Signal | How to measure |
|---|---|
| Time to first review | Platform API: CR-opened timestamp vs first review-comment timestamp, split bot vs human author; gain = ((manual − automated) / manual) × 100 |
| Finding adoption rate | Findings acted on (code change or explicit accept) ÷ findings posted; filter by bot author + tracking label, cross-reference thread resolutions and follow-up commits at the same file:line |
| Noise score | Sample ~10 bot-reviewed CRs per sprint; classify findings acted-on / accepted-no-action / dismissed / wrong. Targets: <20% wrong, <30% dismissed — above that, raise the verification bar or cut the comment budget before rewriting prompts |
| Team sentiment | Ask in retros: real catches? duplicated effort? right volume? Engineers asking whether the bot still runs = too quiet, raise the budget. Low adoption with low noise = correct-but-irrelevant, narrow the lens set. Scope expansion is earned — one lens at a time |
