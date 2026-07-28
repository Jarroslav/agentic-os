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
python3 tests/lib/check-html-refs.py       # every source path a shipped HTML page cites resolves
python3 tests/lib/check-provenance.py --verify-attestation  # originality policy: the tree still matches its recorded measurements
python3 tests/lib/check-changelog.py --self-test  # plugin content may not change without a changelog entry (CI adds --base <PR base>)
```

## Originality check

`check-provenance.py` enforces the repo's originality policy: no tracked file may
substantially overlap an external text corpus the maintainer checks against.
Three measures per file:

| Measure | Catches | Fails at |
|---|---|---|
| exact-copy | byte-identical file | always |
| containment (line, shingle) | diffuse reuse across a file | `gate_threshold` (warns from `author_target`) |
| max_run | the longest verbatim passage | `max_run_gate` (warns from `max_run_target`) |

`max_run` exists because containment is a whole-file average: a long lifted
passage inside an otherwise original file averages away to nothing. A file can
sit at 16% containment and still carry a wholly copied template.

Two files are out of scope by design, because overlap in them means nothing:
`LICENSE` (the Apache-2.0 text is *supposed* to match everyone else's) and
`package-lock.json` (two lockfiles resolving the same packages are supposed to
agree). Corpus-side, `--build` skips vendored dependency trees for the same
reason — a project that vendors the same library is not a copy of the corpus.

### The store, the salt, and the attestation

The fingerprint store (`tests/lib/provenance-fingerprints.json`) holds only
salted one-way hashes, is built locally from corpus directories, and is
**git-ignored — never committed**. The salt is not in it: it lives in
`PROVENANCE_SALT` or a git-ignored `tests/lib/.provenance-salt`, generated on
first `--build`. Keep it — a store read under the wrong salt would match nothing,
so the check refuses to run rather than report a comfortable 0%.

Because both are git-ignored they exist only in the working copy that last ran
`--build`, which leaves every other clone and worktree unable to re-attest.
Point at them instead of copying them around:

```bash
PROVENANCE_STORE=/path/to/provenance-fingerprints.json \
PROVENANCE_SALT="$(cat /path/to/.provenance-salt)" \
  python3 tests/lib/check-provenance.py --attest
```

That leaves CI unable to repeat the scan, since it has neither corpus nor store.
So the maintainer records the result and CI holds the tree to it —
`tests/lib/originality-attestation.json`, the same shape as
`mcp/content-index.json`: a committed claim plus a cheap check that it still
holds. `--attest` writes it and **refuses on a tree that is not clean**;
`--verify-attestation` needs no store and fails if any tracked file changed,
went missing from the record, or was attested at or above a threshold. Changing
any tracked text file therefore means re-running the scan locally or turning CI
red.

```bash
python3 tests/lib/check-provenance.py --build <corpus dirs...>  # build the local store (all dirs in ONE invocation)
python3 tests/lib/check-provenance.py --self-test               # detectors fire on synthetic data
python3 tests/lib/check-provenance.py --report-only             # full scan, never blocking
python3 tests/lib/check-provenance.py --file <paths...>         # strict per-file check for new content
python3 tests/lib/check-provenance.py --require-store           # scan, but fail rather than skip with no store
python3 tests/lib/check-provenance.py --attest                  # record a clean tree (pre-release)
python3 tests/lib/check-provenance.py --verify-attestation      # what CI runs; needs no store
```

Pass every corpus directory in one `--build`: a rebuild replaces the store, so
building from a subset would quietly weaken every later scan. The check refuses
to shrink the corpus without `--force`.

`--attest` guards the same hazard one layer up. Re-attesting against a weaker or
unrelated store would produce a green record that means nothing, and the diff
would look routine because only hashes move — so `--attest` refuses when the
store's `salt_id` differs from the current record's, or when the corpus has
fewer files than when it was last attested. A grown corpus is allowed and
reported. `--force` re-baselines deliberately. Each run also prints which
entries were added, changed, or removed: confirm that list is exactly the files
you touched.

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
| T3 role matrix | every preset template ID resolves to a real file via the VARIABLES.md mapping; no duplicate IDs; qa preset = strict HITL + dispatcher + `test-failure-triage` + `work-item-creator`; devops preset ships the incident-triage pair (`agents/incident-triage` + `guides/incident-triage`, contract readonly with the no-padding literal, installed pair + eval fixture checked by `check-incident-triage.py`, isolated from a developer-only install); security preset ships the threat-modeling pair (`agents/threat-modeler` writer scoped to `docs/security/**` + `guides/threat-modeling`, strict HITL, proposed-severity literal, checked by `check-threat-modeling.py`, isolated from a developer-only install); the Tier-1 marker-prior's ordered profile list (SKILL.md Phase 1 step 4) matches the real files under `generators/stack-profiles/` |
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
