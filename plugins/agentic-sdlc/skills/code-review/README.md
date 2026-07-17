# code-review

On-demand, multi-lens review of a diff or PR — standalone, outside any managed pipeline run. Read-only: it reviews and reports, never edits code or applies fixes.

> This is the thin wrapper. It does not judge code itself — it builds the review context, invokes the shared engine (`code-review-orchestrator`) at gate `code-review.final`, reads back the verdict, and renders it. The engine runs three lenses (an adversarial blind reader, an exhaustive edge-case tracer, a spec-acceptance auditor) plus standards/security adjudication and triage, collapsing everything into one verdict. By design the engine expects a pre-assembled context bundle and never prints to the user; this skill supplies the missing I/O layer — context in, verdict out, rendered for you.

## Use It For

- A pre-PR or pre-commit review without launching a full managed run.
- Scoped reviews of exactly what you changed. Supported scopes:

  | Scope | What it reviews |
  |---|---|
  | branch vs base | current branch against its base |
  | staged | staged changes only |
  | working tree | uncommitted edits |
  | commit range | an explicit range you name |
  | paths | specific files you name |

- Getting the plugin's review quality — severity-grouped findings, business/standards review rows, risk flags — on demand.

Not for: editing or fixing code, auto-committing, or reviewing by PR/MR number — all out of scope in this version. For a review inside a managed flow, use `sdlc-start`, `sdlc-autonomous`, or `sdlc-task` (they route the review gate through `decision-router`) instead of this standalone skill.

## How To Ask

- Name a scope. "Review my staged changes." "Review the branch against main." "Review `src/auth/` and `src/api/`." "Review commits `abc123..def456`."
- If you name no scope, the skill asks which to review first — with a one-line preview per option — and does nothing else until you answer.
- Optionally pass a spec via the `spec` parameter to turn on the acceptance audit, e.g. `spec: docs/stories/login.md`.

> No spec → the acceptance lens is skipped and the verdict's confidence is forced to **low** by design. That reflects the missing spec, not a problem in your code.

What you get back:

- **Decision + confidence + rationale.**
- **Findings**, grouped by severity — each row: `id`, `file:line`, `problem`, `impact`, `fix`.
- **Business / standards review** rows and **risk flags**.
- If the engine could not run, a plain "review could not run" message — never a misleading empty rejection.

## What It Needs

- A git repo and read access. No external services, no credentials.
- Diff materialization writes the chosen scope to `code-review.diff` (excluding `package-lock.json`) using the package's canonical recipe; the verdict then lands in `code-review-final.json`. Both artifacts go under a run directory in `docs/superpowers/reviews/`. Nothing is committed — keep or discard them.
- Optional context, when present, is passed to the acceptance and standards/security checks so they use real rules:
  - a spec/story document (via `spec`);
  - project guides under `.agentic/guides/**`.
- `code-review-orchestrator` must be resolvable in the same package.

**See also**

- `SKILL.md` — the exact step-by-step flow of this skill.
- `../../references/diff-materialization.md` — the canonical diff recipe.
- `../code-review-orchestrator/references/verdict-schema.md` — the verdict schema this skill renders.
