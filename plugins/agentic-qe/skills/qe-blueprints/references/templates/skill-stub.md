# Template: skill stub for a scaffolded QE framework

File-shape contract for the skill-scaffolding sub-step (5a) of the main blueprint
workflow. The parent skill doc loads this template when it generates stub files for
custom skills; it is not meant to be read on its own. Blast radius of applying it:
R2 (writes repo files under the assistant's config directory).

## When to emit a stub

Generate one stub file per skill that the parent workflow's discovery step flagged
as **custom** — a capability the project needs but no existing skill provides.

| Skill classification (from discovery) | Action |
| --- | --- |
| Custom (needed, does not exist yet) | Write a stub using this template |
| Built-in to the assistant platform | Skip — nothing to scaffold |
| Already present in the repo | Skip — do not overwrite |

> Rationale: stubs exist to reserve a slot and a contract for later implementation.
> Duplicating built-ins or clobbering existing skills adds noise without value.

## Where to write it

Path pattern: `<config-root>/skills/<skill-name>.md` — one file per skill, filename
identical to the skill's name plus the `.md` extension.

Pick `<config-root>` from whichever assistant platform the host repo is set up for:

| Platform | Config root |
| --- | --- |
| Claude Code | `.claude/` |
| Cursor | `.cursor/` |
| GitHub Copilot | `.github/` |

## Required file shape

Each stub is a markdown file with YAML frontmatter. Frontmatter carries exactly two
keys — no more:

| Key | Content |
| --- | --- |
| `name` | The skill's name (matches the filename without extension) |
| `description` | One line covering both what the skill does and what should trigger its invocation |

The body has exactly two parts, in order:

1. **Purpose paragraph** — states what process the skill automates and which
   connector or integration it wraps. Ground this in facts gathered during
   discovery; do not invent integrations the project does not have.
2. **Instructions placeholder** — an HTML comment marking where implementation
   steps will go, with a pointer to the public agent-skills format specification
   at agentskills.io.

## Template

```markdown
---
name: <skill-name>
description: <one line: what this skill does and when the assistant should invoke it>
---

<Purpose: name the process this skill automates and the connector or
integration it wraps.>

<!--
Implementation steps not yet written. Fill this section in a later pass.
Format spec: https://agentskills.io
-->
```

## Deliberately incomplete

The stub ships without implementation steps by design. Writing the actual skill
logic is deferred to a human author or a later implementation pass; the scaffolding
step must leave the placeholder comment intact rather than attempt to fill it.

> Rationale: at scaffold time the workflow knows *that* a skill is needed and
> *what* it wraps, but not yet *how* it should behave. Committing a guess would be
> worse than committing a clearly-marked gap.

## Related material

- Main `qa-sdlc-blueprint` skill document — invokes this template at its
  skill-scaffolding sub-step (5a).
- Sibling templates in this directory — same pattern for the other artifact types
  the blueprint scaffolds.
- agentskills.io — external specification for the full skill file format.

## Out of scope

This template defines file shape only. It does not cover writing skill logic,
selecting connectors, validating finished skills, or any QA methodology.
