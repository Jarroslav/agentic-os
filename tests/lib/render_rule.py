"""The template rendering rule, and the adversarial answers that exercise it.

One definition, imported by `refinstall.py` (which applies it), by
`check-render-escaping.py` (T8a, which renders the templates with it), and by
`check-hooks-import.py` (T8b, which reads the values back out of the scaffold).
Keeping `esc()` in one place means a mutation to the rule fails every check that
depends on it, rather than only the copy that was edited.

Spec: `plugins/agentic-os/templates/VARIABLES.md § Rendering convention`.
"""
import json
import re

# A hook may be written with either quote style. Anchored to the start of a line
# (`re.M`) so a guard commented out (`# if __name__ …`) does not count — the "safe
# to import because it's guarded" invariant needs a real guard statement. This does
# not exclude a line inside a triple-quoted string that happens to start with the
# guard text; no template does that, and the definitive check is that importing the
# module (which runs top-level code but not `main()`) raises nothing.
MAIN_GUARD = re.compile(r"""^\s*if\s+__name__\s*==\s*['"]__main__['"]\s*:""", re.M)


def esc(value: str) -> str:
    r"""The JSON-escaped *body* of `value`: no surrounding quotes.

    The template supplies the quotes. `"`, `\`, and control characters (newlines
    included) are escaped; everything else is passed through verbatim. JSON's escape
    syntax is a subset of Python's for these, so one encoding serves `.py.tmpl` and
    `.json.tmpl` alike.

    `ensure_ascii=False` is load-bearing, not cosmetic. With the default, an astral
    character such as U+1F600 is emitted as the surrogate pair `\ud83d\ude00`; JSON
    readers recombine it, but a **Python** string literal does not — the constant
    becomes two lone surrogates that compare unequal to the answer and raise
    `UnicodeEncodeError` when printed. Templates are written as UTF-8, so the
    character can simply stay itself.

    Two corners are out of scope, both unreachable from an interview answer typed at
    a terminal: a *lone* surrogate passes through and raises `UnicodeEncodeError`
    when the rendered file is written; and U+2028/U+2029/U+0085 pass through raw —
    they round-trip correctly through both literal kinds, but `str.splitlines()`
    treats them as line breaks, so a newline-list item containing one would split.
    """
    return json.dumps(value, ensure_ascii=False)[1:-1]


# --- Adversarial interview answers -------------------------------------------
# Every value below is one a real interview could produce, and together they carry
# the three characters that break plain substitution: `"`, `\`, and newline.
#
# `MIGRATIONS_DIR` is deliberately quote-free. It renders on the line *above*
# `MIGRATION_DIFF_COMMAND` in `migration_notice.py.tmpl`; a quote in it turns that
# file into a plain `SyntaxError` under plain substitution, which `py_compile`
# catches — masking the silent class (compiles, raises on import) that is the whole
# reason Check 2b and `check-hooks-import.py` exist. `check_silent_class()` in
# `check-render-escaping.py` fails if this regresses.
#
# The apostrophe that used to live here pinned "templates quote with `"`, never
# `'`". That is now enforced structurally, on every placeholder rather than one:
# `check-render-escaping.py` rejects any template matching `'{{VAR}}'`.
ANSWERS = {
    "MIGRATION_DIFF_COMMAND": 'alembic revision --autogenerate -m "<message>"',
    "APP_START_COMMAND": 'sh -c "npm run dev"',
    "MIGRATIONS_DIR": "supabase/migrations/",
    "TICKET_ADAPTER": 'Jira ("cloud")',
    "LINT_FIX_COMMAND": 'eslint --fix --rule "quotes: [2, \\"double\\"]"',
    "LINT_CHECK_COMMAND": 'sh -c "npx eslint"',
    "BASE_URL": "http://localhost:3000",
    "DEFAULT_BRANCH": "main",
    "SCORECARD_PATH": "docs/audits/instruction-scorecard.json",
    "AGENTS_CANONICAL_DIR": ".agentic/agents/",
    "OUTPUT_CONTRACT_SECTIONS": "Summary,Why,Blocking",
    "MR_ADAPTER": "gh",
    # The one placeholder outside any string literal (`SCORE_THRESHOLD = {{...}}`).
    # Escaping is a no-op here and could not protect it: any value that is a valid
    # Python statement executes. Kept numeric deliberately — the control is intake
    # validation, not this rule. See VARIABLES.md.
    "SCORE_THRESHOLD": "95",
}

# Newline-joined scalars. `GUARDED_WRITE_PATHS` and `HUMAN_GATED_COMMANDS` are
# PreToolUse *block* controls: if escaping mangles them the hook silently stops
# guarding what the interview named, which is why ROUND_TRIP checks their values.
#
# The Windows path uses `\n` and `\t` — *valid* Python escapes. `C:\windows\path`
# would not do: `\w` and `\p` are invalid escapes that survive an absent `esc()`
# verbatim (with only a SyntaxWarning), so the probe would pass unescaped input.
LIST_ANSWERS = {
    "ENV_CHECK_COMMANDS": ["test -f .env", 'test -n "$DATABASE_URL"'],
    "GUARDED_WRITE_PATHS": ['src/"quoted"/**', "C:\\new\\table\\**"],
    "HUMAN_GATED_COMMANDS": ["terraform apply", 'gh release create "$TAG"'],
    # Lands only in `.md.tmpl` fenced blocks, where escaping is *wrong*. Carried here
    # so `md_over_escape_probes()` has something to look for in the rendered prose.
    "GATE_COMMANDS": ["npx tsc --noEmit", 'pytest -k "not slow"'],
}

# The one rendering exemption: a list rendered as JSON array elements inside `[...]`.
# Single source of truth — `check-render-escaping.py` used to keep a divergent copy.
ESCALATE_ON = ["security", "breaking-change", "migration", "spend"]

# `.py.tmpl` placeholders allowed to sit outside a string literal. Exactly one: a
# bare numeric. Anything else added here is an arbitrary-code-injection sink — see
# VARIABLES.md. `check_template_shapes()` fails on any other code-position use.
CODE_POSITION_VARS = {"SCORE_THRESHOLD"}

# Hook module attribute -> the answer it must still equal after a round trip.
# Compiling and importing only proves the render did not *break* the file; a lossy
# escape (strip `"` and `\`) also compiles, imports, and parses — and disarms the
# two block hooks above. These assertions are what close that gap.
#
# Every `.py.tmpl` in-literal placeholder assigned to a same-named module constant is
# listed. `{{OUTPUT_CONTRACT_SECTIONS}}` is the one exclusion: `subagent_gate.py.tmpl`
# renames it and splits it into a list (`CONTRACT_SECTIONS`), so it has no verbatim
# constant to compare — `tests/t0/run-output-contract.sh` covers its parsing instead.
ROUND_TRIP = {
    "MIGRATION_DIFF_COMMAND": ANSWERS["MIGRATION_DIFF_COMMAND"],
    "LINT_FIX_COMMAND": ANSWERS["LINT_FIX_COMMAND"],
    "LINT_CHECK_COMMAND": ANSWERS["LINT_CHECK_COMMAND"],
    "MIGRATIONS_DIR": ANSWERS["MIGRATIONS_DIR"],
    "DEFAULT_BRANCH": ANSWERS["DEFAULT_BRANCH"],
    "SCORECARD_PATH": ANSWERS["SCORECARD_PATH"],
    "AGENTS_CANONICAL_DIR": ANSWERS["AGENTS_CANONICAL_DIR"],
    "ENV_CHECK_COMMANDS": "\n".join(LIST_ANSWERS["ENV_CHECK_COMMANDS"]),
    "GUARDED_WRITE_PATHS": "\n".join(LIST_ANSWERS["GUARDED_WRITE_PATHS"]),
    "HUMAN_GATED_COMMANDS": "\n".join(LIST_ANSWERS["HUMAN_GATED_COMMANDS"]),
}

# Dotted path in the rendered `sdlc/config.json` -> the answer it must equal.
# `json.loads` succeeding proves only that the render did not *break* the file. An
# escape that strips `"` also parses — `"sh -c "npm run dev""` becomes
# `"sh -c npm run dev"`, a different command, silently.
JSON_ROUND_TRIP = {
    "feature_verification.app_start_command": ANSWERS["APP_START_COMMAND"],
    "feature_verification.base_url": ANSWERS["BASE_URL"],
    "integrations.github.command": ANSWERS["MR_ADAPTER"],
}


def md_over_escape_probes():
    """Escaped forms of answers that must appear *unescaped* in rendered markdown.

    `.md.tmpl` prose takes the plain value. An installer that escaped it too would
    leave these strings in the guides — `\\n` where a fenced list needs real line
    breaks, `\\"` inside a quoted command. Only probes that differ from the answer
    are useful; the rest cannot discriminate.
    """
    values = dict(ANSWERS)
    values.update({k: "\n".join(v) for k, v in LIST_ANSWERS.items()})
    return sorted({esc(v) for v in values.values() if esc(v) != v})
