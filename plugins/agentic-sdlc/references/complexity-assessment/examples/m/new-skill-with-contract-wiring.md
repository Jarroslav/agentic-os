# Calibration examples — M

Totals of 15–20. Two or three dimensions at 3, the shape is recognisable, and
something is still undecided when scoring happens.

Drop further M examples into this directory as separate files; nothing indexes
them.

---

## Example: Add a skill and wire it into the contract check

**Ticket:** PROJ-4230
**Sized:** M (17/36)
**Actually:** M — three days

| Dimension             | Label | Score | Evidence |
|-----------------------|-------|-------|----------|
| Component Scope       | M     | 3     | New skill directory, the plugin manifest, and the contract check that enumerates skills |
| Requirements Clarity  | M     | 3     | The skill's job was agreed; which phase invokes it was still being argued |
| Technical Risk        | S     | 2     | Eleven skills already follow the SKILL/README/evals shape |
| File Change Estimate  | M     | 3     | 3 new (SKILL.md, README.md, evals.json), 2 modified — counted against a sibling skill |
| Dependencies          | XS    | 1     | None |
| Affected Layers       | M     | 3     | Skill, manifest, contract check, and the content index that ships it |
| **Total**             | M     | 17/36 | |

**Why this size:** Three components and an open routing question. Nothing here
is novel, but it lands in four places and one of them is a gate.

**Calibration note:** The Affected Layers 3 surprises people — a "new skill"
sounds self-contained. It is not: anything under `plugins/**` also has to reach
the served content index, so the change has a build step attached whether the
ticket mentions one or not.

---

## Example: Add a tool to the MCP server, end to end

**Ticket:** PROJ-4247
**Sized:** M (19/36)
**Actually:** M — four days, at the top of the band

| Dimension             | Label | Score | Evidence |
|-----------------------|-------|-------|----------|
| Component Scope       | M     | 3     | Tool module, the server's tool registry, and the contract tests |
| Requirements Clarity  | M     | 3     | Inputs settled; the shape of the error response for a missing target was not |
| Technical Risk        | M     | 3     | Read-only by design, but a path argument reaching the filesystem needs containment checks |
| File Change Estimate  | M     | 3     | 2 new, 4 modified — measured across the existing seven tools |
| Dependencies          | XS    | 1     | Nothing new; the SDK is already present |
| Affected Layers       | L     | 4     | Tool, registry, transport contract, tests, and the published package surface |
| **Total**             | M     | 19/36 | |

**Why this size:** Affected Layers is the dimension doing the work. Five tiers
including a published interface is what pushes a routine addition to the top of
M rather than the middle.

**Calibration note:** 19 sits one point from the L boundary, and the boundary
rule matters here: Technical Risk is 3, not 5, and the codebase demonstrates the
pattern seven times over — so it rounds down and stays M. Had the tool been
anything other than read-only, that same total should have gone to L.
