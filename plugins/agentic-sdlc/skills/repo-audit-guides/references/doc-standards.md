# Documentation Standards the Audit Checks Against

A working checklist for the pre-planting documentation survey. Run it before any
"knowledge planting" to decide whether a repository's existing docs are trustworthy
enough to seed agent-facing foundation material from.

> Assessment only. This reference tells you how to judge docs — it does not rewrite
> them, generate replacements, or prescribe a house writing style. Treat it as a
> living checklist that grows as you meet new repositories, not a fixed rubric.

## How to use this

For each document you survey, score it against the two signal sets below, then answer
the probing questions. A doc lands in one of three buckets: healthy planting source,
stale, or gap. The signals decide the first two; the questions decide what to do about
the third.

## Strong signals — docs worth planting from

| # | Signal |
|---|--------|
| 1 | The `README.md` at the repository root states what the project is for, how to stand up a working environment, the everyday workflows, and where to go for deeper docs. |
| 2 | Developer-facing docs spell out the exact commands to install, test, lint, type-check, build, review, and release. |
| 3 | Architecture material describes module boundaries, the main data flows, dependencies on external systems, and the tradeoffs behind key design choices. |
| 4 | A decision log (ADR-style) records the non-obvious calls and the constraints the project currently lives under. |
| 5 | Citations resolve: the paths, package names, commands, CI jobs, and ownership markers named in the docs actually exist in the repository. |
| 6 | Where the project ships or runs something, ops docs cover failure modes, migrations, secrets and config handling, deployment, and rollback. |

## Weak signals — docs you cannot trust as-is

| # | Signal |
|---|--------|
| 1 | The content is generic — drop it into any repository unchanged and it would still read as true. |
| 2 | Commands are missing, out of date, or contradict what the manifests and CI config actually run. |
| 3 | The architecture description no longer matches the source tree. |
| 4 | Setup leans on context or credentials that are stated nowhere. |
| 5 | The real standards live only in chat threads and people's heads, never written down. |

## Decision rules

Apply these while scoring. They convert observation into a verdict.

- **Command cross-check.** Match every documented command against the manifests and CI
  definitions. Any mismatch downgrades the doc to weak.
- **Architecture-vs-tree check.** Hold each architecture claim up to the current source
  layout. Divergence is a weak signal.
- **Citation resolution.** A doc earns a strong rating only when its citations — paths,
  packages, CI jobs, owners — resolve against the live repository.
- **Genericness test.** If the text would apply to any repository, it fails.

> A doc can be well written and still be weak. Prose quality is not the bar here —
> correspondence to the actual repository is. Verify against the tree, not against how
> confident the writing sounds.

## Questions the auditor must answer

Do not close the survey until each of these has a concrete answer, per document.

1. **Do the commands still run?** Point to evidence — a manifest entry, a CI job, a
   recorded run — not an assumption that the doc is current.
2. **Source or stale?** Label the doc: a future planting source, or stale material to
   set aside.
3. **Where do the gaps sit?** For each gap, decide whether it can be inferred from
   repository evidence or must be asked of the user.
4. **Explicit enough to follow?** Test whether the documented standards are precise
   enough for an agent to act on without guessing.

## Gap triage

Every gap resolves one of two ways, and you decide which per gap:

- **Repo-inferable** — a later foundation step can reconstruct the answer from evidence
  already in the repository.
- **Ask the user** — the answer is not recoverable from the tree and must be escalated
  as a question.

> Do not let a gap sit unclassified. An uncategorized gap silently becomes a guess at
> planting time, which is exactly the failure this survey exists to prevent.

## Scope boundaries

- Not a documentation style guide or a product-doc template.
- Does not fix docs or write new ones — it assesses what is already there.
- Not a frozen rubric. Extend these signals and questions as new repository shapes
  teach you what else to look for.
