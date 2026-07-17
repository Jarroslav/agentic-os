# QA authoring shared reference — intake & environment gate

Loaded on demand by `qa-case-generator` and `qa-e2e-generator` before either
authors anything. This gate does gating, validation, and routing only — no test
content is produced here. Everything downstream (coverage math, planning,
generation, review, sync) assumes this gate has passed.

> Blast radius: the preflight scan and every doc read are R0. The only writes are
> the backup copy and the fresh-version directory under `docs/superpowers/`,
> which are R1 run-artifact writes. This gate never *calls* an adapter (no R3) —
> it confirms one is declared; the actual ticket fetch and any test-management
> sync happen in later phases behind their own handling.

> Grounding: resolve conventions and adapter settings only from what the docs
> state. If a required marker is absent, halt — do not infer a default and do not
> guess a backend.

## Gate sequence

Run these in order; the first failing check halts (or, for a matched prior run,
prompts) before the next runs.

1. Ticket reference + duplicate detection
2. QA knowledge presence
3. Convention parsing
4. Adapter resolution
5. Emit the pass banner and hand off state

---

## 1. Ticket reference + duplicate detection

You are invoked with a work-item reference, `$TICKET_ID`. Before doing any work,
look for a prior generation keyed by that id:

- Scan target: `docs/superpowers/qa-tasks/*/manual/meta.json`
- Match key: `"ticket_id": "$TICKET_ID"`

No match → proceed to step 2. A match means test cases already exist for this
ticket; you must not silently overwrite them. Present the three options through
`AskUserQuestion`:

| Choice | Effect | State set |
| --- | --- | --- |
| Regenerate | Reuse the matched directory. The overwrite is deferred to the write phase; before writing, the prior contents are copied to `<existing_dir>.backup-<timestamp>`. | `regeneration_mode` on, `existing_dir` = matched path |
| New version | Author into a fresh date/slug directory alongside the old one; leave the prior run untouched. | `regeneration_mode` off |
| Cancel | Stop immediately. Print `Operation cancelled by user` and exit gracefully. | — |

> The backup is why Regenerate is safe: nothing is destroyed until the write
> phase, and the previous version is always preserved under the
> `.backup-<timestamp>` suffix.

---

## 2. QA knowledge presence

Two documents are mandatory. Both live under `.agentic/guides/testing/`:

| Document | Path |
| --- | --- |
| QA strategy | `.agentic/guides/testing/qa-strategy.md` |
| QA health | `.agentic/guides/testing/qa-health.md` |

Either one missing → halt and direct the user to run `qa-foundation`, which
builds these files. Do not attempt to synthesize them.

---

## 3. Convention parsing

Read the test-format conventions out of `.agentic/guides/testing/qa-strategy.md`.
Look under a `## Conventions` heading (or `## Test Style`). If that section is
absent or empty, halt: the user must add a `## Conventions` section covering test
format, manual-test template sections, API-test template sections, and
placeholder format.

Map the section's wording into `qa_conventions`:

**test_format** — match on keyword:

| Signal in the doc | `test_format` |
| --- | --- |
| `Gherkin` or `Given/When/Then` | `gherkin` |
| `structured steps` or `numbered steps` | `structured_steps` |
| neither | `custom` |

**placeholder_format** — match on the sample style:

| Sample | `placeholder_format` |
| --- | --- |
| `<value>` (angle brackets) | `angle_brackets` |
| `{value}` (curly braces) | `curly_braces` |
| neither | `custom` |

**naming_pattern** — capture the documented pattern verbatim, or `null` if none
is stated.

Resulting shape:

```
qa_conventions = {
  test_format: "gherkin | structured_steps | custom",
  naming_pattern: string|null,
  placeholder_format: "angle_brackets | curly_braces | custom",
  manual_test_sections: ["preconditions","steps","expected_result","notes"],
  api_test_sections: ["endpoint","headers","request_body","expected_response","notes"]
}
```

---

## 4. Adapter resolution

Adapters are declared in `.agentic/guides/project.md`; no ticket or
test-management backend is hardcoded.

### Work-item (ticket) adapter — mandatory

Parse the `## Ticket Adapter` section and its fields:

| Field | Meaning |
| --- | --- |
| `**Status**` | `configured` or `not_configured` |
| `**Adapter**` | how tickets are reached (an MCP name, `gh`, `glab`, or a skill name) |
| `**Lookup**` | the command/call used to fetch a ticket |

Section missing, or `**Status**: not_configured` → halt. The user either adds the
section or runs `/repo-guides` to auto-detect it. On success:

```
work_item_adapter = { adapter_name: string, lookup_command: string }
```

> This is the "ticket reference is valid" check: `$TICKET_ID` is only actionable
> if there is a declared way to resolve it. Confirm the adapter here — the fetch
> itself is a later phase.

### Test-management adapter — optional

Parse the `## Test Management Adapter` section and its fields:

| Field | Meaning |
| --- | --- |
| `**Status**` | configured or not |
| `**System**` | e.g. TestRail, Jira, Zephyr, ADO Test Plans |
| `**Adapter**` | how the system is reached |
| `**Sync Command**` | the call used to push cases |

Missing or not configured is **non-fatal**. Set `test_mgmt_adapter = null` and let
the later sync step be skipped. When present:

```
test_mgmt_adapter = { system: string, adapter_name: string, sync_command: string }
```

---

## Halt conditions (consolidated)

| Condition | Outcome | How the user clears it |
| --- | --- | --- |
| Prior run matches `$TICKET_ID`, user picks Cancel | exit | prints `Operation cancelled by user` |
| `.agentic/guides/testing/qa-strategy.md` absent | halt | run `qa-foundation` |
| `.agentic/guides/testing/qa-health.md` absent | halt | run `qa-foundation` |
| `## Conventions` / `## Test Style` absent or empty in qa-strategy.md | halt | add a `## Conventions` section (test format, manual-test sections, API-test sections, placeholder format) |
| `## Ticket Adapter` missing or `**Status**: not_configured` | halt | add the section, or run `/repo-guides` |
| `## Test Management Adapter` missing or not configured | continue | none — `test_mgmt_adapter = null`, sync skipped downstream |

> Recovery is always "fix the cause, re-run from here." Missing docs → run
> `qa-foundation`. Missing convention section or adapter → edit the guide files.
> The gate is idempotent: re-running after a fix re-validates from the top.

---

## Pass output + handoff

On success, print the environment-validation confirmation:

```
✅ Phase 1: Environment Validation
   - QA documentation: found
   - Test format: <gherkin|structured_steps|custom>
   - Work-item adapter: <adapter_name>
   - Test management adapter: <system or "not configured">
```

State carried forward to the next phase:

| Variable | Set when |
| --- | --- |
| `regeneration_mode`, `existing_dir` | a prior run matched and Regenerate was chosen |
| `qa_conventions` | conventions parsed in step 3 |
| `work_item_adapter` | ticket adapter resolved in step 4 |
| `test_mgmt_adapter` | test-management adapter present, else `null` |
