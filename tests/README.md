# Tests

Run everything:

```bash
bash tests/t0/run.sh                 # hook units (rendered templates, exit-code contracts)
bash tests/t0/run-output-contract.sh # output-contract parser (subagent_gate)
bash tests/run-matrix.sh             # T1–T8 acceptance matrix
bash tests/cursor/run-cursor-e2e.sh  # Cursor packaging + fresh-install smoke (see tests/cursor/README.md)
cd mcp && npm ci && npm run check:drift && npm run build && npm test  # MCP server
```

`run-matrix.sh` re-runs the **output-contract** suite as T7, but not the hook
unit suite — so it is not a single green/red gate on its own. CI runs all three
commands above, plus two marketplace-wide checks that run standalone (they
cover both plugins, so they live outside the agentic-os-scoped matrix):

```bash
python3 tests/lib/check-manifests.py       # manifests parse, per-plugin version sync, canonical author/owner
python3 tests/lib/check-skill-contract.py  # every skill ships SKILL.md + README.md + evals/evals.json in shape
python3 tests/lib/check-neutrality.py      # no PII / org names ship (hashed denylist + shape patterns)
python3 tests/lib/check-provenance.py      # originality policy: no tracked file substantially overlaps an external corpus
```

## Originality check

`check-provenance.py` enforces the repo's originality policy: no tracked file may
substantially overlap an external text corpus the maintainer checks against. It
measures each tracked file's line/shingle *containment* plus exact-copy detection,
failing above `gate_threshold` and warning in the `[author_target, gate_threshold)`
band (the bar for freshly authored content).

It is a **local maintainer tool**: the fingerprint store it reads
(`tests/lib/provenance-fingerprints.json`) holds only salted one-way hashes, is
built locally from corpus directories, and is **git-ignored — never committed**.
Where no store is present (CI runners, fresh clones) the tree scan skips with an
ok note; `--self-test` always runs and needs no store.

```bash
python3 tests/lib/check-provenance.py --build <corpus dirs...>   # build the local store
python3 tests/lib/check-provenance.py --self-test                # detectors fire on synthetic data
python3 tests/lib/check-provenance.py --file <paths...>          # strict per-file check for new content
```

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
| T1 fresh | hooks `py_compile` **and import cleanly** (a badly-rendered scalar compiles but raises on load — asserted here, on the pristine scaffold, because T5 mutates `$FRESH`); settings valid + Stop/SubagentStop/PreToolUse/secret-deny wiring; git hook installed + `agentic-os:` marker; zero unresolved `{{ }}`; scorecard has an entry for every canonical contract + pointer + governance file (the fleet is spawnable out of the box); `agent-registry.md`'s routing table is intact — the `<!-- generated-agent-rows -->` marker is a real table row inside the table block, with no orphaned rows after it (`check-registry.py`, the deterministic half of doctor Check 8: a bare-comment marker terminates the GFM table, so Phase 5's appended rows would render as paragraph text and the orchestrator would see no generated agents); unreviewed `git commit` blocked by the native hook; `quality-gates.md` is rendered from the detected `GATE_COMMANDS` (a real gate per command, no unrendered placeholder, no shipped stub example); `ai-policy.md` carries the Screen-3 autonomy-override block (the per-capability answers land there instead of being discarded; `--defaults` renders the "no overrides" note); `PATTERNS.md` indexes no guide it did not install (the qa-only rows are conditional on the preset) and its `<!-- generated-guide-rows -->` append point is a real table row inside a valid GFM block (`check-patterns.py`, sharing `gfm.py` with `check-registry.py` — a bare-comment marker would terminate the table and Phase 5's generated-guide rows would render as paragraph text); scaffold tree matches `tests/golden/fresh-developer-manifest.txt` |
| T2 mature | `CLAUDE.md` changes only between markers (house rules survive); pre-existing settings hook preserved; colliding `.agentic/agents/security-reviewer.md` NOT overwritten (skip default); foreign `pre-commit` chained to `pre-commit.local`, not replaced |
| T3 role matrix | every preset template ID resolves to a real file via the VARIABLES.md mapping; no duplicate IDs; qa preset = strict HITL + dispatcher + `test-failure-triage` + `work-item-creator`; the Tier-1 marker-prior's ordered profile list (SKILL.md Phase 1 step 4) matches the real files under `generators/stack-profiles/` |
| T4 idempotency | a `--reinstall` leaves every scaffolded file byte-identical (journal excluded) |
| T5 upgrade | Phase-2 three-way classification: unmodified managed → overwrite, user-edited managed → prompt, `CLAUDE.md` → managed-block wholesale, user-owned → skip |
| T6 deps | pinned non-optional sources produce `extraKnownMarketplaces`+`enabledPlugins` entries; an `OWNER/` placeholder source is skipped and journaled `pending-source-pin` |
| T7 parser | the `t0` output-contract suite (`run-output-contract.sh`), re-run as one matrix check |
| T8 rendering (3 checks) | **T8a** (`check-render-escaping.py`): `esc()` round-trips hostile and astral input through a Python literal *and* a JSON string; a **tokeniser** pass proves no `.py.tmpl` places a placeholder in a single-quoted string or outside a string entirely (bar the one sanctioned numeric); plain substitution still reproduces the silent bug class; and every `.py.tmpl`/`.json.tmpl` rendered with quote-bearing answers (`alembic … -m "<message>"`, `test -n "$DATABASE_URL"`, `sh -c "npm run dev"`) compiles, imports, parses, and round-trips. **T8b**: a second scaffold rendered from the *same* answers (`REFINSTALL_ADVERSARIAL=1`, sharing `render_rule.py` with T8a) yields hooks whose constants still equal the answers, a `config.json` whose values do too, and `.md` prose free of escaping artifacts |

Three properties, three reasons. `py_compile` is not enough: plain substitution
yields `X = "a "b""`, which Python reads as a chained comparison — it compiles,
exits 0, and raises `NameError` only when the module loads (`check_silent_class()`
pins that this is still reachable). **Importing/parsing** is not enough: an escape
that merely strips `"` and `\` also imports and parses, while silently disarming
`guarded_write_paths` and `human_gated_commands` (both `PreToolUse` block hooks) and
rewriting `sh -c "npm run dev"` into a different command — so every constant is
compared against its answer, on the Python *and* JSON side. And the **default** scalar
answers carry no quotes, so they render identically with or without `esc()`: T8b's
separate adversarial scaffold is what actually goes red if the rule is dropped.

Mutations that fail T8, all verified: `esc()` absent, lossy, double-applied, or
`ensure_ascii=True`; an installer that stops escaping, escapes only `.py`, or
over-escapes `.md.tmpl` (through *either* render call site); a template that
single-quotes a placeholder, even non-adjacently (`ROOT / 'a/{{VAR}}'`); a template
that adds a second bare code position; a dropped `__main__` guard; and an answer set
that stops reaching the silent class. Verify with a one-line edit to
`tests/lib/render_rule.py`, `tests/lib/refinstall.py`, or any `.py.tmpl`.

Hooks are **imported, never executed** (`main()` may `git fetch`/merge, or run
`ENV_CHECK_COMMANDS` through a shell). Both checks refuse to import a hook lacking an
`if __name__ == "__main__":` guard, and catch `BaseException`: `SystemExit` is not an
`Exception`, so a bare `except Exception` would let a hook that exits at import pass
while truncating the scan. `check-hooks-import.py` additionally scopes itself to
journal entries with `owner: "managed"` — a team's own hook needs no guard (Claude
Code runs it as a script) and is not ours to import, even when it collides with one
of our paths. `check-render-escaping.py` reads templates, not a scaffold, so it has
no journal to consult.

`refinstall.py` is the *reference* executor, not the shipped installer — the real
`/agentic-init` is a model following `SKILL.md`. T8b proves the rule is applied by
something that follows the spec; nothing in CI can prove the model does.

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
