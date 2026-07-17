#!/usr/bin/env python3
"""T8a: the templates tolerate the escaping rule, in every position.

Renders every `.py.tmpl` and `.json.tmpl` with adversarial interview answers —
values carrying `"`, `'`, `\\`, and newlines, all of which real answers do carry
(`alembic revision --autogenerate -m "<message>"`, `test -n "$DATABASE_URL"`,
`sh -c "npm run dev"`) — and asserts the output compiles, imports, parses, and
**round-trips**: each rendered constant must still equal the answer it came from.

Compiling is not enough (a chained comparison compiles), and importing is not
enough either (a lossy escape that strips `"` and `\\` imports cleanly while
disarming the two PreToolUse block hooks). Both halves are needed.

Scope: this proves the rule is sound against the current template shapes. That the
*installer* applies it is T8b's job — `check-hooks-import.py --round-trip`, run
against a scaffold rendered from these same answers by `refinstall.py`.

Sixteen placeholder occurrences (13 distinct variables) sit inside Python/JSON
string literals across the placeholder-bearing templates. Plain substitution breaks
them two ways, one of them silent:

  MIGRATION_DIFF_COMMAND = "alembic revision --autogenerate -m "<message>""
    -> py_compile EXIT 0. Python reads the chained comparison
       `"..." < message > ""`. Raises NameError when the module loads.

  ENV_CHECK_COMMANDS = \"\"\"test -f .env
  test -n "$DATABASE_URL"\"\"\"
    -> SyntaxError, but only when the quote-terminated command is last in the list.
       Reorder the two commands and it compiles.

`check_silent_class()` pins the first of those: it renders `migration_notice.py.tmpl`
with plain substitution and requires the output to compile *and* raise on import.
Without it, "py_compile is not enough" would be an assertion rather than a test —
and it would silently stop holding the moment an answer on an earlier line grew a
quote of its own.

Usage: check-render-escaping.py <PLUGIN_ROOT>
"""
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import tokenize
import traceback
from pathlib import Path

from render_rule import (ANSWERS, CODE_POSITION_VARS, ESCALATE_ON, JSON_ROUND_TRIP,
                         LIST_ANSWERS, MAIN_GUARD, ROUND_TRIP, esc)

TPL = Path(sys.argv[1]) / "templates"


def render(text: str) -> str:
    # `{{ESCALATE_ON}}` is the one exemption: JSON array elements, quotes included.
    text = text.replace("{{ESCALATE_ON}}", ",".join(json.dumps(i) for i in ESCALATE_ON))
    for var, items in LIST_ANSWERS.items():
        text = text.replace("{{%s}}" % var, esc("\n".join(items)))
    for var, value in ANSWERS.items():
        text = text.replace("{{%s}}" % var, esc(value))
    return text


def dig(obj, dotted):
    for part in dotted.split("."):
        obj = obj[part]
    return obj


def fail(rel, msg):
    print("  %s: %s" % (rel, msg))


def check_rule():
    """`esc` must round-trip through a Python literal AND a JSON string.

    Directed, because no template answer plausibly carries an astral character, so
    the template sweep below cannot reach it: `json.dumps` with the default
    `ensure_ascii=True` emits a surrogate pair, which JSON readers recombine and
    Python string literals do not.
    """
    probes = ['a"b\\c\nd', "it's", "\U0001f600 astral", "é中", "\t\r\x00"]
    problems = []
    for v in probes:
        ns = {}
        try:
            exec('X = "%s"' % esc(v), ns)  # noqa: S102 — the unit under test
        except Exception as e:
            problems.append("python literal %r: %s" % (v, e))
            continue
        if ns["X"] != v:
            problems.append("python literal %r -> %r" % (v, ns["X"]))
        if json.loads('{"k": "%s"}' % esc(v))["k"] != v:
            problems.append("json literal %r did not round-trip" % v)
    for p in problems:
        print("  render_rule.esc: " + p)
    return len(problems)


PLACEHOLDER = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def check_template_shapes(targets):
    """Every `.py.tmpl` placeholder must sit in a double-quoted string (or a comment).

    Tokenised, not grepped. A regex for `'{{VAR}}'` only sees quotes adjacent to the
    braces — `ROOT / 'x/{{AGENTS_CANONICAL_DIR}}'` slips straight past it. The
    tokeniser sees the enclosing STRING token whatever its shape, and equally sees
    the placeholders that are in *no* string token at all: those are code positions,
    where the escape rule is powerless and any value that parses as Python executes.
    Exactly one is sanctioned (`SCORE_THRESHOLD`, a bare numeric); a second would be
    an injection sink.
    """
    problems = 0
    for tpl in targets:
        if not tpl.name.endswith(".py.tmpl"):
            continue  # JSON has no single-quoted strings and no code positions
        rel = tpl.relative_to(TPL)
        src = tpl.read_text(encoding="utf-8")

        # One unique sentinel per *occurrence*, not per variable: two uses of the
        # same variable can sit in different positions (one in a string, one bare),
        # and a per-variable check would exempt the bare one because the other is
        # stringed. `occ` maps each sentinel back to its variable name.
        occ = {}
        def _sub(m, occ=occ):
            sent = "AGENTICOS%dZ" % len(occ)   # a bare NAME token on its own
            occ[sent] = m.group(1)
            return sent
        src = PLACEHOLDER.sub(_sub, src)

        placed = set()  # sentinels seen inside a string or comment token
        # f-strings tokenise as START (`f'` / `f"`) · MIDDLE (the literal text, no
        # quote) · END. Track the opening quote so a sentinel in a MIDDLE token is
        # judged against its f-string's quote style, not skipped for lack of one.
        fstring_quote = []
        try:
            for tok in tokenize.generate_tokens(io.StringIO(src).readline):
                if tok.type == tokenize.FSTRING_START:
                    fstring_quote.append(tok.string.lstrip("rbfuRBFU")[:1])
                    continue
                if tok.type == tokenize.FSTRING_END:
                    quote = fstring_quote.pop() if fstring_quote else '"'
                elif tok.type == tokenize.FSTRING_MIDDLE:
                    quote = fstring_quote[-1] if fstring_quote else '"'
                elif tok.type == tokenize.STRING:
                    quote = tok.string.lstrip("rbfuRBFU")[:1]
                elif tok.type == tokenize.COMMENT:
                    quote = "#"
                else:
                    continue
                for sent, name in occ.items():
                    if sent not in tok.string:
                        continue
                    placed.add(sent)
                    if quote == "'":
                        fail(rel, "{{%s}} sits in a SINGLE-quoted literal (%s) — "
                             "the rule does not escape `'`; use \" quotes"
                             % (name, tok.string.strip()[:48]))
                        problems += 1
        except tokenize.TokenError as e:
            fail(rel, "template is not tokenisable: %s" % e)
            problems += 1
            continue

        for sent, name in occ.items():
            if sent in placed or name in CODE_POSITION_VARS:
                continue
            fail(rel, "{{%s}} has an occurrence in a CODE position, outside any string "
                      "literal. Escaping cannot protect it: any value that parses as "
                      "Python executes. Quote it, or add it to "
                      "render_rule.CODE_POSITION_VARS and validate the answer at intake."
                      % name)
            problems += 1
    return problems


def check_silent_class():
    """The premise of Check 2b: `py_compile` passes what `import` catches.

    Renders `migration_notice.py.tmpl` with *plain* substitution and requires the
    result to (a) compile and (b) raise on import. If a future answer set turns this
    into a `SyntaxError` instead, `py_compile` would suffice, and the import step in
    this file and in `/agentic-doctor` Check 2b would be justified only by assertion.
    """
    tpl = TPL / "hooks/claude/migration_notice.py.tmpl"
    out = tpl.read_text(encoding="utf-8")
    for var, value in ANSWERS.items():
        out = out.replace("{{%s}}" % var, value)  # deliberately unescaped
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "silent_probe.py"
        p.write_text(out, encoding="utf-8")
        if subprocess.run([sys.executable, "-m", "py_compile", str(p)],
                          capture_output=True).returncode != 0:
            print("  check_silent_class: plain substitution now yields a SyntaxError, "
                  "so py_compile alone would catch it. The silent class is no longer "
                  "exercised — see render_rule.ANSWERS['MIGRATIONS_DIR'].")
            return 1
        spec = importlib.util.spec_from_file_location("silent_probe", p)
        try:
            spec.loader.exec_module(importlib.util.module_from_spec(spec))
        except KeyboardInterrupt:
            raise
        except BaseException:
            return 0  # compiles, raises on import: exactly the class under test
        print("  check_silent_class: plain substitution produced a module that both "
              "compiles AND imports cleanly — the bug this suite guards is not "
              "reproduced by the current answers.")
        return 1


targets = sorted(list(TPL.rglob("*.py.tmpl")) + list(TPL.rglob("*.json.tmpl")))
if not targets:
    print("  no .py.tmpl/.json.tmpl found under %s" % TPL)
    sys.exit(1)

seen_py, seen_json = set(), set()
broken = check_rule() + check_template_shapes(targets) + check_silent_class()
for tpl in targets:
    rel = tpl.relative_to(TPL)
    out = render(tpl.read_text(encoding="utf-8"))

    # `{{VAR}}` grammar per VARIABLES.md; matches agentic-doctor Check 2c's intent.
    if left := sorted(set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", out))):
        fail(rel, "unsubstituted %s — add it to render_rule.ANSWERS" % left)
        broken += 1
        continue

    if tpl.name.endswith(".json.tmpl"):
        try:
            doc = json.loads(out)
        except json.JSONDecodeError as e:
            fail(rel, "rendered output is not valid JSON: %s" % e)
            broken += 1
            continue
        # Parsing proves the render did not *break* the file. An escape that strips
        # `"` also parses, turning `sh -c "npm run dev"` into a different command.
        for dotted, expected in JSON_ROUND_TRIP.items():
            try:
                actual = dig(doc, dotted)
            except (KeyError, TypeError):
                continue  # this key lives in a different .json.tmpl
            seen_json.add(dotted)
            if actual != expected:
                fail(rel, "%s round-tripped lossily\n      expected %r\n      got      %r"
                     % (dotted, expected, actual))
                broken += 1
        continue

    # Never import a hook that would run main() on load — the same precondition
    # agentic-doctor Check 2b states, and check-hooks-import.py enforces.
    if not MAIN_GUARD.search(out):
        fail(rel, "rendered hook has no __main__ guard — importing it would run "
                  "its side effects")
        broken += 1
        continue

    with tempfile.TemporaryDirectory() as d:
        rendered = Path(d) / tpl.name.replace(".py.tmpl", ".py")
        rendered.write_text(out, encoding="utf-8")

        r = subprocess.run([sys.executable, "-m", "py_compile", str(rendered)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            detail = (r.stderr.strip().splitlines() or ["exit %d" % r.returncode])[-1]
            fail(rel, "rendered output does not compile: %s" % detail)
            broken += 1
            continue

        # py_compile is not enough: `"a "b""` compiles as a chained comparison and
        # only raises when the module loads. Import — never execute.
        spec = importlib.util.spec_from_file_location("render_probe_" + rendered.stem,
                                                      rendered)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except KeyboardInterrupt:
            raise
        except BaseException:
            # BaseException: a module calling sys.exit() at import raises SystemExit,
            # which `except Exception` lets through — this script would then inherit
            # the exit code, skip every later template, and report green.
            fail(rel, "rendered hook raises on import: %s"
                 % traceback.format_exc().strip().splitlines()[-1])
            broken += 1
            continue

        for name, expected in ROUND_TRIP.items():
            if not hasattr(module, name):
                continue
            seen_py.add(name)
            if getattr(module, name) != expected:
                fail(rel, "%s round-tripped lossily\n      expected %r\n      got      %r"
                     % (name, expected, getattr(module, name)))
                broken += 1

# A renamed or deleted constant must fail loudly, not quietly shrink coverage.
for label, expected, seen in (("ROUND_TRIP", ROUND_TRIP, seen_py),
                              ("JSON_ROUND_TRIP", JSON_ROUND_TRIP, seen_json)):
    if missing := sorted(set(expected) - seen):
        print("  no rendered template defines %s — %s is stale" % (missing, label))
        broken += 1

sys.exit(1 if broken else 0)
