# Evidence Integrity — Anti-Fabrication Standards

Blocking standards for every agent-authored artifact: reports, contracts, guides,
review verdicts, requirement docs, generated code comments. The failure mode these
rules exist to kill: **a rule satisfied on paper while the substance is silently
invented** — the output looks compliant, but a reference, tag, quote, or list entry
was manufactured to make it so.

The instruction-quality rubric
([`instruction-quality-rubric.md`](instruction-quality-rubric.md)) verifies claims
after the fact; this guide governs how claims are produced in the first place.
A rule that violates this guide is UNVERIFIED regardless of how plausible it reads.

## Citations & references

### MUST NOT self-cite
An agent never mints an identifier — a file path, ticket ID, section heading,
token name, config key — and then cites it as if it pre-existed. A reference is
citable only if it existed before the current run, or is explicitly labeled as
created in this change ("added in this PR"). Citing your own output as external
authority is fabrication even when the content is correct.

### MUST verify quotes verbatim before presenting them
Before presenting text as a quote from a file, re-read the file and match the
text exactly. If it does not match exactly, it is a paraphrase — label it as one
and drop the quotation marks. This applies to quoting your own instructions and
guides, not just third-party sources.

### Cross-document claims keep their evidence tag
A claim carried from one document into another keeps its `sourced: <path>` or
`unverified` marking. The tag never silently upgrades in transit — copying an
unverified claim into a summary does not make it sourced. Dropping the tag is
the same violation as inventing the claim.

## Classifications & approvals

### MUST NOT author classification tags
Severity levels, data classifications, compliance labels, and approval states
belong to their owners. Such a tag is only usable when it pre-exists in a durable
artifact authored by the owning human (a file, a ticket, a signed-off doc).
Relaying "the owner approved this verbally" as a recorded tag is prohibited:
ask the owner to record it, then cite the record. When no record exists, the
artifact says so — e.g. `severity: proposed — owner confirmation pending`.

## Counts & lists

### MUST NOT pad a list to hit a required count
When a template demands N entries (hypotheses, examples, test cases, risks) and
fewer than N are evidence-backed, do not invent fillers. State the shortfall
("2 of 3 slots evidence-backed") and label each unsupported entry with the
literal marker `speculative — no direct evidence`. A padded list is worse than
a short one: it hides exactly the gap the count was meant to expose.

### Verification criteria are counted, never impressionistic
A pass/fail signal is valid only if a reader can recompute it: "count of
acceptance criteria without a threshold = 0", "all 5 sections present in
order", "row count of silver = bronze − nulls − duplicates, checked by query".
"Looks complete" and "reasonably covered" are not verification results.

## Self-check before finishing any artifact

Close out by recomputing, not recalling:

- Count of quotes not re-read against their source file = 0.
- Count of cited references that did not exist before this run and are not
  labeled as created here = 0.
- Count of classification/approval tags without a durable owner-authored
  record (or an explicit `pending` marker) = 0.
- Count of list entries added only to reach a required length and not labeled
  `speculative — no direct evidence` = 0.
- Count of claims whose sourced/unverified tag was dropped or upgraded while
  being copied between documents = 0.

A non-zero count is fixed before the artifact ships — never explained away.

## How to propose a change

Same protocol as the other standards: add the rule here, quote the incident it
came from, PR title `docs(standards): <rule short title>`. Only the owner can
approve removing or weakening a rule.
