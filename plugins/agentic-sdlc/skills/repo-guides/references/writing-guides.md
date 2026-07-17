# Writing Guides Agents Can Act On

The shared writing standard for every project guide produced by the `repo-guides` and `guide-sync` skills. Load this file before you generate or edit any guide text. It governs how discovered facts get written up — pattern shape, document structure, placeholder semantics, evidence, size ceilings, and the sign-off checks. It does not decide *which* guides exist (templates do) or *how* facts are discovered (the scan does).

> A guide is an instruction surface for another agent, not prose for a human reader. Every line must earn its place by changing what the reading agent does. If a line would not alter a decision, cut it.

## Pattern entries

A pattern is the atomic unit of a guide. Write each one in exactly three parts, in this order:

1. **Rule** — the practice, stated in one or two sentences. No preamble.
2. **Contrast** — poor vs. recommended, as a two-row table or a paired set of bullets. Show the wrong shape next to the right one.
3. **Evidence** — one or more `file:line` pointers to where the pattern actually lives in the repo.

Prefer a pointer over pasted code. Inline snippets are the exception, not the default:

| Constraint | Limit |
|---|---|
| Snippet length | ~5 lines maximum |
| Snippets per pattern | at most one |
| Default | a `file:line` pointer instead of a snippet |

Only inline `[code_example]` when the rule cannot be expressed without the code. If a pointer carries the same information, drop the snippet.

**Contrast example** — a log-sanitization rule that names the helper and both call sites:

| Avoid | Prefer |
|---|---|
| Interpolating raw request fields straight into log calls | Route values through `sanitizeLogArgs()` before logging |

> Evidence: `src/utils/errors.ts:12`, `src/utils/security.ts:45`

## Document structure

Every guide uses one heading spine:

- **One `#` (H1)** — the guide title. Exactly one per file.
- **`##` per pattern category** — one section per family of patterns.
- **`###` per pattern** — individual patterns nest under their category.

Which `##` sections are mandatory for a given guide type comes from the template, not from this file. Read the matching template under `references/templates/guides/` before you lay out headings, and honor the sections it requires.

## Placeholders

Guides are rendered from templates seeded with placeholder tokens. Two forms, one rule each:

| Syntax | Meaning | Action |
|---|---|---|
| `[NAME]` | required | must receive a real discovered value |
| `[NAME?]` | optional | if no real value exists, delete the whole row or section — never leave `(none)` or `N/A` |

Never ship a `[NAME]` or `[NAME?]` token in a finished guide. A required token with no value is a discovery failure to fix, not a blank to paper over. An optional token with no value means the content does not apply — remove it.

`[code_example]` follows the same optional discipline: fill it only when the rule cannot stand without code; otherwise drop it via the `?` mechanism.

### Standard tokens and where their values come from

| Token | Discovered from |
|---|---|
| `[PROJECT_NAME]` | `package.json` name / `pyproject.toml` name / `pom.xml` artifactId / root folder name |
| `[LANGUAGE]` | manifest language field |
| `[FRAMEWORK]` | primary framework dependency |
| `[VERSION]` | dependency version |
| `[TEST_FRAMEWORK]` | test runner from devDependencies |
| `[BUILD_COMMAND]` | manifest build script |
| `[LINT_COMMAND]` | manifest lint script |
| `[TEST_COMMAND]` | manifest test script |
| `[file:lines]` | an evidence pointer in `file:line` form |
| `[code_example]` | an inline snippet, only when unavoidable |

## Evidence

Evidence is what separates a guide from a guess.

- Every category carries **at least one** `file:line` reference. A category with zero evidence is dropped at planning time — never generate it and backfill a citation later.
- Every claim describes **observed code behavior**, not intent or aspiration. Write what the code does, traceable to a file or an observable pattern.
- The pointer format is `file:line`. A pointer must resolve: the file exists and the line number is within the file's length.

> Grounding rule: if a fact is not present in the scanned inputs, it does not go in the guide. Do not infer, extrapolate, or import knowledge from outside the repo.

## Size caps

Hard ceilings, enforced at **Phase 5 / Step 7** of the parent workflow:

| Artifact | Guidance | Hard max |
|---|---|---|
| Each guide | concise, evidence-backed, as short as useful | **400 lines** |
| Entrypoint file | compact reference surface, no minimum | **300 lines** |

There is no minimum length. Padding a guide to reach some target range is itself a validation failure. A guide over 400 lines is condensed and re-rendered before completion — turn prose into tables, cut redundant examples, and swap inline code for `file:line` refs until it fits.

## No padding

Length is never a goal. These are banned outright:

- Synthetic reminder lines — the review, operating, and foundation variants.
- Near-duplicate lines that restate a rule already made.
- Placeholder rows left as stubs.
- Generic evidence-index padding when the rules already carry concrete `file:line` refs.

The padding scan searches for these literal strings; do not emit them:

```
Review reminder
Foundation reminder
Operating reminder
```

## Content routing

Put each kind of fact in its one correct home:

| Content | Destination guide |
|---|---|
| Git conventions (branch/commit rules) | `git-workflow` |
| Exact commands to run | `quality-gates` |
| Routing / where-to-look pointers | entrypoint |

When drift is detected, route the fix to the same targets: git conventions to `git-workflow`, commands to `quality-gates`, navigation to the entrypoint. Do not duplicate a fact across guides.

## `project.md` schema

`project.md` carries exactly these five sections, in this order, and no others:

1. **Project Identity**
2. **Work Item Tracker**
3. **Ticket Adapter**
4. **Source Control And Review**
5. **MR Adapter**

> The tracker and source-control integrations are adapter-driven. The ticket and MR adapters name how the pipeline talks to whatever backend the project uses — no platform is hardcoded here.

## Managed regions

Content the skills own is fenced by paired `start` / `end` markers. Never write only one half of a pair, and never nest or cross them — every `start` needs its matching `end`, verified by grep. Edit only inside the markers; leave surrounding hand-authored text untouched.

## Validation checklist

Run these before you call a guide done. Each check has a mechanical method.

| Check | Method |
|---|---|
| Guide paths in the entrypoint table resolve | read each path |
| `file:line` refs resolve | read file; line number ≤ file length |
| No `[PLACEHOLDER]` / `[PLACEHOLDER?]` tokens remain | grep the generated files |
| Guide ≤ 400 lines | `wc -l` |
| Entrypoint ≤ 300 lines, reference-only | `wc -l` |
| No reminder or filler padding | search the three reminder strings, near-duplicate lines, stub rows |
| `project.md` matches the 5-section schema | section-presence check |
| Drift routed to the right guide | `git-workflow` vs. `quality-gates` vs. entrypoint |
| Commands match the manifests | re-read `package.json` / `Makefile` / etc. |
| Managed regions balanced | grep `start` / `end` pairs |

> Tooling stays deliberately light: grep and `wc -l` are the whole toolbox. No CI hook, no bespoke linter — the checks above are run by hand before completion.
