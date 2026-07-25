# Calibration examples — S

Totals of 10–14. Understood work with a known shape, usually one or two
dimensions at 2 or 3 and the rest at 1.

Drop further S examples into this directory as separate files; nothing indexes
them.

---

## Example: Add a pre-push hook variant behind the existing hook runner

**Ticket:** PROJ-4204
**Sized:** S (12/36)
**Actually:** S — a day, including the test

| Dimension             | Label | Score | Evidence |
|-----------------------|-------|-------|----------|
| Component Scope       | S     | 2     | The hook templates plus the runner that dispatches them |
| Requirements Clarity  | S     | 2     | Behaviour agreed; the exit-code convention on a soft failure was still open |
| Technical Risk        | S     | 2     | Four hooks already follow this shape, so the pattern is settled |
| File Change Estimate  | S     | 2     | 1 template, 1 runner branch, 1 test — 3 files, 1 new |
| Dependencies          | XS    | 1     | Stdlib only, as the other hooks are |
| Affected Layers       | M     | 3     | Template rendering, the installed hook, and the test that imports it |
| **Total**             | S     | 12/36 | |

**Why this size:** An established pattern with one open question. The single
open question is what keeps Requirements Clarity off 1.

**Calibration note:** Hook work is easy to under-score because each file is
short. What sets the floor here is that a hook is *installed* — it runs on
someone's machine outside the test suite, so the failure path deserves the 2 on
Technical Risk even when the code is twenty lines.

---

## Example: Extend a preset with one additional agent slot

**Ticket:** PROJ-4211
**Sized:** S (11/36)
**Actually:** M — three days, because the registry table needed reworking

| Dimension             | Label | Score | Evidence |
|-----------------------|-------|-------|----------|
| Component Scope       | S     | 2     | One preset file plus the agent template it points at |
| Requirements Clarity  | S     | 2     | The slot's purpose was clear; its routing row wording was not |
| Technical Risk        | S     | 2     | Adding a slot is routine — six presets already do it |
| File Change Estimate  | S     | 2     | Estimated 3 files, 1 new |
| Dependencies          | XS    | 1     | None |
| Affected Layers       | S     | 2     | Preset plus generated registry |
| **Total**             | S     | 11/36 | |

**Why this size:** Every dimension looked like a routine addition, and the
change genuinely was — for the preset.

**Calibration note:** This one was sized wrong, and it is here for that reason.
The File Change Estimate was guessed, not measured: the generated routing table
had an append marker that had to move, which pulled in two more files and a test.
Had Grep been run over the marker before scoring, File Change Estimate would have
been 3 and the total 12 — still S, but the note in the plan would have flagged
the table. Measure the footprint; do not picture it.
