# Tests

Run everything:

```bash
bash tests/t0/run.sh                 # hook units (rendered templates, exit-code contracts)
bash tests/t0/run-output-contract.sh # output-contract parser (subagent_gate)
bash tests/run-matrix.sh             # T1–T7 acceptance matrix
```

`run-matrix.sh` re-runs the **output-contract** suite as T7, but not the hook
unit suite — so it is not a single green/red gate on its own. CI runs all three
commands above (plus JSON manifest/preset validation); run all three locally
too.

## What is automated vs manual

The install flow has deterministic parts (render templates, merge settings,
install git hooks, seed the scorecard, mature-repo non-destructive rules) and
model-driven parts (the six interview screens, per-slot agent **generation**,
live `AskUserQuestion` escalation). Only the deterministic parts are asserted
here — and they are exercised by actually executing them, not by mocking.

`tests/lib/refinstall.py` is a **reference executor**: it follows
`plugins/agentic-os/skills/agentic-init/SKILL.md` Phase 4 literally for the
`developer` preset with `--defaults` answers (nextjs-supabase profile),
skipping Phase 5 generation and Phase 3's out-of-target side effects. It doubles
as the skill-executability test: if a Phase-4 step could not be derived from the
spec, `refinstall.py` could not implement it. Two spec-faithfulness fixes were
made while building it — both are notes for the real installer, not product
bugs: (1) `CLAUDE.md` managed-block replacement must be idempotent for a
block-only file (no leading-whitespace drift on re-run); (2) the install journal
updates every run and is therefore excluded from the idempotency snapshot.

| Test | Asserts |
|---|---|
| T1 fresh | hooks `py_compile`; settings valid + Stop/SubagentStop/PreToolUse/secret-deny wiring; git hook installed + `agentic-os:` marker; zero unresolved `{{ }}`; scorecard has an entry for every canonical contract + pointer + governance file (the fleet is spawnable out of the box); `agent-registry.md`'s routing table is intact — the `<!-- generated-agent-rows -->` marker is a real table row inside the table block, with no orphaned rows after it (`check-registry.py`, the deterministic half of doctor Check 8: a bare-comment marker terminates the GFM table, so Phase 5's appended rows would render as paragraph text and the orchestrator would see no generated agents); unreviewed `git commit` blocked by the native hook; scaffold tree matches `tests/golden/fresh-developer-manifest.txt` |
| T2 mature | `CLAUDE.md` changes only between markers (house rules survive); pre-existing settings hook preserved; colliding `.agentic/agents/security-reviewer.md` NOT overwritten (skip default); foreign `pre-commit` chained to `pre-commit.local`, not replaced |
| T3 role matrix | every preset template ID resolves to a real file via the VARIABLES.md mapping; no duplicate IDs; qa preset = strict HITL + dispatcher + `test-failure-triage` + `work-item-creator`; the Tier-1 marker-prior's ordered profile list (SKILL.md Phase 1 step 4) matches the real files under `generators/stack-profiles/` |
| T4 idempotency | a `--reinstall` leaves every scaffolded file byte-identical (journal excluded) |
| T5 upgrade | Phase-2 three-way classification: unmodified managed → overwrite, user-edited managed → prompt, `CLAUDE.md` → managed-block wholesale, user-owned → skip |
| T6 deps | pinned non-optional sources produce `extraKnownMarketplaces`+`enabledPlugins` entries; an `OWNER/` placeholder source is skipped and journaled `pending-source-pin` |
| T7 parser | the `t0` output-contract suite (`run-output-contract.sh`), re-run as one matrix check |

## Known limitations

- The **live `AskUserQuestion` escalation path** (agent emits `## Escalate to
  human` → parent must prompt) is proven mechanically by the output-contract
  parser exiting 2 with the `AskUserQuestion` instruction on stderr (T7), and by
  `agentic-doctor`'s HITL smoke at install time. It is not driven through a real
  interactive prompt in this offline matrix.
- **Generation quality** (Phase 5 stack agents) and **stack discovery**
  (Phase 1 step 4's Tier-2 subagent) both depend on live subagent runs and
  can't be scripted here — see `tests/universal/README.md` for the manual,
  model-driven verification procedure and its recorded results.
- Fixtures are built by `tests/fixtures/make-{fresh,mature}.sh` into a temp dir;
  nothing is committed as a full fixture repo.
