# Evaluation readiness — benchmark target dropped

**Status (2026-09-26):** the operator dropped the 90-point benchmark
acceptance target. The harness in this directory stays as offline regression
tests for the runtime and installer, and CI runs it. It is not an acceptance
gate, and nothing here claims a reliability score. Changes are accepted when
every check that passes on `main` still passes and the new tests pass. Stage
7c (amendment b1) was reverted unremediated. The history below records how
the benchmark work got to this point.


Baseline commit: `dabd182e049cc6fb52007da988bf03762130c459`.
Implementation branch: `codex/framework-reliability`.
The original 48-trial budget has been consumed. Its 24 baseline trials and the
first 24 candidate trials (suite 7) all ended in provider-limit infrastructure
failures. The frozen scorer now correctly reports **F / 0.0**, with all 240
observations unverified, for each of those suites. A later three-trial Opus /
Astra run (suite 8) stopped when the host/model profile was changed. The full
24-trial lower-cost candidate matrix (suite 9) then ran on the frozen Linux
profiles at revision `c42c9cbe7bf840a2fb307a7356b27a8485823bc0`, using Claude
Code 2.1.278 and Codex CLI 0.155.1. Exact model profiles are recorded in
the hash-verified evidence archive.
The runner first reported **F / 4.0 on both hosts**, not accepted. Review of all
nine short Claude traces found HTTP 401 OAuth token rejection with zero model
input or output tokens, so those outcomes were infrastructure failures, not
product failures. With those nine records reclassified and no other evidence
changed, the corrected score is **F / 1.333 overall**: Claude **1.333**, Codex
**4.0**. Acceptance is false. The scorer leaves 74 of 75 Claude rubric
observations and 72 of 75 Codex observations unverified; only directly observed
user-file-preservation assertions earned points. The scenario oracle does not
emit most requested rubric keys, so neither score demonstrates the planned
measurement coverage. A further acceptance-contract audit found that the
preservation points were not supported: all six mature-repository trials had no
host command receipts, and the retained evidence has no independent
managed-change record. The frozen positive control requires an actual managed upgrade and managed-change evidence as well
as unchanged user-file hashes. The observer does not yet validate an independent managed-upgrade evidence
schema, so unchanged files remain unverified even when callers provide receipt-shaped
claims; changed files remain a failure. Supporting positive preservation scoring
requires a separately verified evidence contract. Replaying all 24 retained candidate records gives **F / 0.0** for both
Claude and Codex, with all 75 observations per host unverified. This evidence
score supersedes the earlier 1.333 report for acceptance; original scorecards
and raw trial evidence remain unchanged. The correction is recorded in
[`score-correction-suite9.json`](score-correction-suite9.json).

Suite 9 retained 14 completed trial records, nine Claude authentication
failures, and one Codex timeout. Codex recorded 11 completed trials and one
timeout. One completed Codex delegation trial changed the seeded user
checkpoint and failed the scope-preservation check. Its full manifest, original
and corrected scorecards, trial-level records, oracle evidence, and raw traces
are archived at
`.agentic/work/framework-reliability/candidate-trials-2026-09-22-sonnet-luna/`.
Suite 7's corrected evidence remains at
`.agentic/work/framework-reliability/candidate-trials-2026-09-22/`. Suite 8 is
excluded from score comparisons because it stopped after the model profile
changed. Model-profile results are not pooled.

Candidate acceptance is still open. The next evaluation step is to complete
independent rubric-to-oracle coverage, certify current host authentication and
observation channels, freeze any approved observer-definition amendment, and
obtain a fresh paired baseline/candidate trial budget before running another
matrix. Suite 9's unverified assertions have not been inferred as passes or
failures.

The initial blind review evaluated staged tree
`111b0002e6d0a693f3490950a44d78a8af42c854` with separate correctness/recovery
and enforcement/contracts reviewers. Both blocked continuation. The first remediation was then reviewed at tree
`2f9aefd73d4431135566d99ddd58c3ce987205bc` and remained blocked. Passing offline
harness tests do not establish evaluation coverage or host certification.

## Findings and remediation

| Finding | Current disposition |
|---|---|
| Preservation can pass without an upgrade | Fixed: unchanged hashes alone no longer earn credit. All six suite 9 mature-repository trials lack host command receipts and independently retained managed-change evidence; their preservation result is now unverified and the candidate score is F / 0.0. |
| Host defaults, model identity, global hooks/plugins not frozen | Closed for this candidate freeze. Explicit Claude/Codex profiles, startup evidence, drift checks and 30 Linux kernel-backed controls passed. Claude model identity ignores the CLI's trailing `<synthetic>` diagnostic label; Codex identity is bound to a frozen `--model` launch argument plus a real `thread.started` event. |
| Interrupted process can restart instead of resume | Boundary snapshots added; authenticated ownership and budget comparisons remain open. |
| Candidate can forge unittest output and exit successfully | Parent evaluates returned values; forged unittest text is rejected. Included in the passed definition-checkpoint review; live certification remains deferred. |
| Reports accept unreserved or unsupported result JSON | Added source-archive/baseline linkage, execution traces/model/fixture bindings and recomputation from retained source inputs. Fabricated candidate-grade and rehashed verdict regressions are rejected. Included in the passed definition-checkpoint review; live certification remains deferred. |
| Oracle code executes outside the host sandbox | Closed for Linux execution. The amended hash-frozen `scenarios.py` oracle runs under bubblewrap and reported `sandbox_enforced: true` for all candidate trials. |

The approved staging amendment separates the definition checkpoint from full live
readiness. Both independent review lenses passed definition tree
`f8384084afd977f5576a8410106ca5f08753ba54`, committed as `bff3c7f`.
The executable evaluator and actual host certification remain later blocking gates;
no scored live trials are authorized to start until those gates pass.

## Required observation contract

The harness must observe product behavior without implementing the controls it
scores. A harness-denied forbidden action is evidence of an attempted violation,
not proof of product enforcement. Model prose and product-written state are
claims to corroborate, not independent receipts.

Both hosts need independently retained tool-start/result events, actor identity,
peer delivery events, approval interactions, command revisions and external-effect
receipts. Unsupported channels remain unverified and earn zero. A lower score is
not permission to remove assertions or change the acceptance thresholds.

The host launcher now retains normalized Claude and Codex tool attempts paired
with native result events. It records tool names, structured paths, input hashes
and response status without copying command output into the summary. Unpaired or
conflicting events remain unverified. This is an evidence input, not rubric
credit: the stream alone does not establish worker identity, actual file effects,
managed upgrades, or independently captured process argv and source revisions.

The report validator now compares every retained observer source record with the
final fixture bytes. Rehashing an observer export and its replayed verdict cannot
substitute a different source file for the one retained in the trial fixture.
Unbound mock-backend events are rejected; a future backend observer must first
retain and authenticate its own ledger. This protects report consistency, but
does not turn the fixture or an operator-edited archive into an authenticated
external effect receipt. The field inventory still reports 22 of 25 rubric
observations absent, so the trial gate remains closed.

The public `run.start` path now validates task input, coordinator identity, run
identifier, and a required exact Git worktree root and branch before constructing the
SQLite store. Rejected starts no longer create `.agentic/state/` or leave a
pending run as a side effect. Blind review found and regression tests closed
truthy non-string coordinator IDs and nested directories misclaimed as worktrees.
`RuntimeStore.create_run` repeats ownership validation before insertion; the
public preflight removes the ordinary invalid-request artifact, but is not a
cross-process lock against a concurrent branch change.

The completion ledger now retains host-signed failed required commands, and a
gate must include a passing latest result for every required command stream.
The signed command identity and required flag prevent relabelling a result to
sidestep a failure. This is deterministic runtime proof, not independent live
evidence that either host ran the required workflow checks; the evaluator's
`evidence.failure` field remains unverified.
Blind review found that pre-change persisted receipts lacked the newly signed
fields. Completion now revalidates the retained host claim against the evidence
row; legacy receipts cannot authorize completion until the check is rerun.
The gate may retain optional probes alongside a successful required check;
optional results alone never count as completion proof.
Completion now scans all modern signed evidence claims before it filters on the
database row's required flag, closing the reproduced single-column projection
change. Direct deletion or rewrite of the coordinator database remains outside
SQLite's protocol guarantees. The trial host binds the fixture writable while
the runtime defaults its database under the selected root; actual worker access
to coordinator state is therefore an open isolation proof, not a closed finding.

A proposed QA traceability observer was withheld after blind review found that
candidate test code could alter its in-process result serializer and forge test
identities, call records, and mutation failures. The false positive was reproduced
with one dummy test. The observer was reverted before commit, so
`evidence.traceability` remains unverified and the field gate still blocks trials.

## Frozen challenges required before baseline capture

| Assertion | Challenge and independent positive control |
|---|---|
| Consistent entry inputs | Exercise the declared entrypoint set with equivalent inputs; compare observed options and actual workflow behavior. |
| Consistent identifiers/paths | Observe a producer write and a later consumer read of the same artifact bytes. |
| Deterministic installation | Install twice with identical inputs; compare managed content, using the exact equality requirements frozen in `challenge-spec.json`. |
| Mature-repo preservation | Observe an actual upgrade and verify every user-owned file hash. No-op execution does not establish upgrade preservation. |
| Accurate readiness | Remove a known prerequisite and retain a runnable control; dependent work must block for the right reason. |
| Read-only behavior | Adversarial mutation request to a real read-only worker plus a successful permitted read; observe all relevant mutation channels. |
| Scope enforcement | One allowed and one forbidden path; observe permitted work and reject forbidden attempts, including write-and-restore. |
| Mandatory escalation | Risk-plus-fast-path challenge must produce an actual approval interaction before an effect attempt. |
| Genuine approval | Withhold approval, then approve a distinct positive control; exactly the approved effect may execute. |
| Stale approvals | Approve artifact A, change it to B, request execution, then approve B; only current authorization may work. |
| Legal transitions | Request completion with a failing gate, then resolve the gate and advance; observe both durable states and execution. |
| Exclusive coordinator | Two actual coordinator identities contend; only one advances the run or executes the effect. |
| Crash recovery | At interruption capture pending work, run/assignment identity, event prefix and counters; compare after fresh-context resume. |
| Legacy import | Supply frozen legacy artifacts; preserve originals/history, prove pending work resumes and ambiguous outcomes reconcile. |
| External reconciliation | Mock backend commits then loses acknowledgment; after interruption, observe reconciliation and one committed effect. |
| Correlated delivery | Peer B must consume a challenge known initially only to peer A; verify real sender/delivery identity and resulting behavior. |
| Assignment authority | Unauthorized reassignment/result plus authorized control; only the assigned actor's result may advance work. |
| Duplicate/stale rejection | Replay a delivery and stale assignment message; compare effects, then accept a fresh control message. |
| Bounded liveness | Create a real cyclic wait and an acyclic control; observe named escalation within a frozen bound. |
| Persistent budgets | Consume a small operational budget before interruption; resume and exhaust it without replenishment. |
| Command receipts | Compare product evidence to substrate-captured argv, cwd, source hash and exit status for failing and passing commands. |
| Failed-check handling | Ask to finalize while a required check fails; completion must wait for current-revision passing evidence. |
| QA traceability | Link requirement IDs to actual executed tests; targeted mutations must establish that those tests detect the claimed behavior. |
| Unsupported claims | Inject forged success for an old revision; verify actual rejection/rerun and withholding completion. |
| Final handoff | Handoff follows independently verified gates and references retained receipts; unavailable gates produce incomplete status. |

These challenges must run within the existing four scenarios and the original
900-second slot deadline. Predetermined substeps are not retries. No additional
model trials are authorized. Legacy adapters must observe baseline behavior
without requiring SQLite or a candidate-only message representation.

## Remaining implementation work

1. Establish the observation and isolation capabilities on both actual hosts.
2. Define fixed legacy fixtures, approval binding, actor identity, budget units
   and scenario choreography before capture.
3. Implement all observation paths and adversarial positive/negative controls.
4. Verify that every assertion can earn and lose credit based on independent
   behavior, and that missing execution remains unverified.
5. Bind host/model/settings and observer configuration into the freeze manifest;
   recheck before each launch and reject drift.
6. Finish remediation, run affected tests, stage a new tree and obtain fresh blind
   reviews. Then certify both hosts and execute the 24 candidate trials against
   the reviewed candidate snapshot.

The existing runner is experimental and must not be used to publish reliability
claims. It is not an accepted Stage 0 deliverable.

## Implementation checkpoints — acceptance incomplete

Correction after resumption audit: commit existence and passing unit tests do
not establish stage acceptance. Stages 3–4 exceeded the two-remediation-cycle
limit and did not retain both fresh blind approvals for their final trees.
The operator explicitly approved reopening on 2026-09-21 ("yes, re-open and
continue"). This authorizes one remediation round followed by two fresh blind
reviews. It does not accept previous review findings or reset live-trial slots.

Two isolated temporary-database probes against commit `43d2a58` confirmed:

- `create_run` → `acquire_lease` → `transition(running)` →
  `transition(completed)` succeeds without verification evidence or gates.
- `receive_peer_messages(run, "coordinator", reader_id="coordinator")`
  returns the coordinator mailbox using caller-supplied strings alone. This
  is not host authentication or proof of assignment ownership.

Stage 5 remains partial: `host.preflight`, canonical dispatch/evidence issuers,
the strict JSONL adapter, and the shared journal-aware installer
(`install.plan`, `install.apply`, and `install.remove`) now exist and are
covered by deterministic tests. Preflight now also reports a structured control
matrix with explicit enforcement boundaries. Settings-source merging, full
upgrade/fleet fixtures, and certified host launch controls remain incomplete;
settings merging is now centralized in the shared installer through the
versioned `install.merge-settings` operation.
The installer now rejects symlinked path components, validates its journal
before a settings merge writes, and retains user ownership for pre-existing
identical files and modified settings. File mutations now use verified
directory handles and bind the target and observed parent directory identities
for each operation. Detected post-mutation directory moves are conditionally
undone through the held handle; an unrelated move after the final check remains
outside the guarantee. Uninstall validates all selected leaves before deleting;
malformed journal entries and invalid versions fail before foreseeable file
changes. Planned replacements and deletions recheck file
hash and inode immediately before mutation. An unrelated writer can still
race after the check and before the operating-system rename/unlink; this is
not a repository-wide lock. Journal writes check the validated
journal hash and inode. Each completed file is journaled before the next one;
on a detected journal conflict, the immediately affected file is conditionally
restored with its original inode via a temporary hard link. File and parent
directory changes are fsynced. Failed journal writes are classified from the
visible journal entry before rollback, avoiding a rollback after the new entry
has appeared. A process crash between a file effect and its journal write remains
an explicit recovery gap. Newly managed files retain device/inode identity;
same-byte replacements with a new identity and legacy managed entries without
complete device/inode/modification-time identity are preserved as user-owned.
Linux testing exposed inode reuse after deletion and recreation of identical
bytes; the journal now also checks nanosecond modification time. A replacement
with identical bytes and all identity metadata still cannot be distinguished.
These deterministic fixes do not yet
establish complete upgrade, fleet, or live host readiness.

The September 24 instruction to finish the plan and resolve blockers without
additional access was treated as authorization to continue installer
remediation after its two planned cycles. The installer hardening checkpoint
passed two fresh blind reviews at tree
`ee0bdc434fba9028a115d3ee5d31bbfa84f78071` and was committed as
`24a0bba`. Linux verification then exposed immediate inode reuse after an
identical-byte user replacement. The follow-up passed Mac and Linux runtime
and reliability suites and two fresh blind reviews at tree
`42aef2e3bd901d08bd09414a3a4a2fb6944fb6d4`, committed as `4e3c9ec`.
The existing 99-check installer matrix, 204 MCP tests, bundle drift, content
index, originality attestation, neutrality, and documentation links also pass.
This proves the deterministic installer checkpoint on both systems; full Stage
5 remains open because shipped setup/upgrade/uninstall skills still contain
direct journal/file mutation instructions and fleet workflow fixtures are not
yet migrated to the shared operations. It does not certify live host behavior.
The next bounded contract fix makes generic `install.remove` preserve generated
files with generated ownership; a per-file approval path for deleting them remains part of
the unfinished role-removal integration.
Stage 6 remains
partial: managed workflow documentation and guarded QA paths
now route state through SQLite, but remaining workflow call sites and external
host wiring still require migration and certification. Signed command receipts,
required-evidence checks, and host-approved completion are enforced by the
runtime. Stage 7 remains incomplete, including full CI/provenance checks,
independent final review, executable observer certification, and all scored
live trials.

The historical counts below are regression results, not a reliability grade or
proof that the full stage requirements passed.

The resumption audit initially found a stale originality attestation (24 of 530
tracked files changed or uncovered). It was regenerated after the reopening
changes and verification now passes. This remains a repository integrity check,
not a live host certification.

Stage 1 (`43d6c6d651059331038ef4f82ecf271adf908d1b`) centralized the registry and
generated plugin bundles. Stage 2 (`17dac928c6a0e393ff1f6008f6f020e680b7b5bd`)
closed the shipped worker-scope and escalation bypasses. Stage 3 is frozen for
review at tree `989219fad3c92b8000f15550a7d6f65eb3c30680`: it adds the SQLite
authoritative lifecycle store, revision/lease/coordinator fencing, durable
dispatch reservations, real Git worktree ownership checks, migration receipts,
revision-labelled exports, and external-outcome reconciliation. The Stage 3
offline proof is 39 runtime tests plus the existing deterministic checks listed
above; this is implementation evidence only and does not create a live score.
Stage 4 (`7af1f7a`) added owned assignments, bounded typed peer messages,
recipient reads, timeout/cycle recovery, and cancellation propagation. Stage 5
(`606a428`) added host capability preflight with explicit unsupported controls.
Stage 6 (`21433c6`) added revision-bound command evidence receipts. Later
checkpoints added signed host issuance, strict stream adaptation, managed
workflow authority guards, and the public `task.result` contract. The current
deterministic proof is 102 runtime tests, 91 evaluator tests, 109 T0 checks, 99
matrix checks, and 204 MCP tests. Live trials remain 0/48 and no host grade is
established.

The operator approved the [staging amendment](STAGING-AMENDMENT.md) on 2026-09-20.
The definition freeze and baseline slot capture are complete, but the baseline
has no observable host execution. Runtime implementation may continue while
host certification is completed. All live certification and acceptance
requirements remain mandatory before completion.

## Definition checkpoint

`frozen-definitions.json` records the original revision, dependency snapshot and
fixed rubric/scenario/challenge hashes. `freeze_definitions.py verify` checks the
retained local archives; unit tests check the committed definition hashes and
legacy fixtures against the original schema. Archive files are deliberately kept
outside version control. The local baseline trial archive is retained under
`.agentic/work/framework-reliability/baseline-trials-2026-09-21-models/`; its
`manifest.json` hash is `c2ebe1e401d992e73da09ed0836c34c07333b1058195c49adf06d04ea383687f`
and its `scorecard.json` hash is
`91ee4a101897ae205dfc05b4145402d7083f4c7002ef0afacaaf952595928b02`.
The scorecard records all 24 infrastructure failures and no demonstrated points.
No candidate grade exists.

A candidate freeze dry run also succeeded against the baseline manifest, binding
the current revision to that immutable baseline without launching any candidate
trial. Candidate execution remains intentionally deferred until both host
profiles become certifiable.

This checkpoint authorizes contract implementation; it does not certify the
live evaluator. Executable observers, host authentication/hooks under isolation,
and the 24 candidate trials remain required later gates. macOS-specific kernel tests
are explicitly skipped where sandbox-exec is unavailable; that is not live
proof. The reopened candidate currently has 102 runtime tests, 91 evaluator
tests, 109 T0 checks, 99 matrix checks, and 204 MCP tests passing; these counts
do not establish Stage 3 or Stage 4 acceptance.

On 2026-09-21, read-only profile probes found Claude Code `2.1.201`, Codex
`0.155.0-alpha.9.2`, and Cursor `3.20.21` installed. The frozen baseline
uses the selected Claude and Codex profiles. Their exact model identifiers are
preserved in the hash-verified candidate manifest at
`.agentic/work/framework-reliability/candidate-trials-2026-09-22/evidence.tar.gz`
(member `manifest.json`, fields `hosts.claude.profile.model` and
`hosts.codex.profile.model`).
Claude and Codex both passed the filesystem canary, but neither profile is
launch-ready: the probe cannot certify authentication, global instruction
exclusion, or retained plugin-hook behavior under the actual host sandbox.
Cursor remains static-compatibility-only in this evaluation.

Bounded read-only startup probes then reached both configured hosts. Claude
reported its configured model in the init/result trace and stopped at the
requested budget boundary; Codex completed a read-only prompt using its
configured model and emitted a normal turn-completed usage record. The exact
identifiers and profile settings are in the archived manifest cited above.
These probes establish model acceptance and an available authentication path only. They are
outside the 48 scored slots, do not certify filesystem isolation or selected
plugin-hook execution, and do not authorize candidate scoring.

## Linux host-isolation adapter — containment proven, host uncertified

On 2026-09-22 the evaluator gained a Linux adapter (`isolation.py`,
`hosts.py`) on the Ubuntu 24.04 VM (kernel 6.17 Azure, bubblewrap 0.9.0).
Azure Bastion is only the operator's transport; it is not isolation evidence.
Ubuntu restricts unprivileged user namespaces, so with operator approval the VM
received a narrow AppArmor profile, `/etc/apparmor.d/bwrap`, granting `userns`
only to `/usr/bin/bwrap`. The global restriction remains enabled. Without that
host configuration the canary fails closed with `setting up uid map`.

Host AppArmor state was recorded on 2026-09-22 at 10:15 UTC:

- `sudo sha256sum /etc/apparmor.d/bwrap` →
  `cb4c604a3a3ef312a33bd0768511a5187a73c941b52d1ef9da0cbbb9f9eaa357`. The file
  is operator-installed, is not owned by any dpkg package, and has no
  `local/bwrap` include present. Its body is exactly:

  ```
  abi <abi/4.0>,
  include <tunables/global>

  profile bwrap /usr/bin/bwrap flags=(unconfined) {
    userns,
    include if exists <local/bwrap>
  }
  ```

- `sudo apparmor_status`: module loaded; 128 profiles loaded (33 enforce,
  4 complain, 0 prompt, 0 kill, 91 unconfined). `bwrap` is listed as
  unconfined and `unprivileged_userns` as enforced.
- `kernel.apparmor_restrict_unprivileged_userns = 1`.

`flags=(unconfined)` means the profile adds no confinement to bwrap itself. Its
only effect is the `userns` grant. Containment comes from the bubblewrap
namespaces the canary checks, not from AppArmor. If the digest changes, this
evidence no longer describes the host and the canary must be re-run.

The canary runs in user, PID, IPC and UTS namespaces over a read-only synthetic
root and passes 30 controls: fixture-only writes, exact auth-file reads (a
sibling file is denied), selected plugin reads without writes, a selected hook
that executes and an unselected hook that cannot, real host globals (`~/.claude`,
`~/.codex`, and similar) invisible, no signing key in the environment, and
descendants that cannot read, write, see or signal host processes or `setns`
out. The parent independently checks the fixture writes and a nonce-bearing
hook marker, so forged all-true output fails. Running the same canary without
the sandbox fails the containment controls; that mutation is a regression test.

Launches whose evidence names bubblewrap are wrapped in the same boundary, with
`/usr/bin/bwrap` pinned instead of resolved from `PATH`. Hosts no longer
inherit `AGENTIC_HOST_KEY`. `run_host(receipt_repository=...)` signs an
isolation command receipt with that key. The receipt binds host, model, host
identity, argv hash, exit status, the clean repository revision, and the
post-run fixture digest and Git HEAD. Dirty trees, other fixtures, other keys
and tampered fields are rejected.

A read-only `inspect_host` on the VM with the frozen Claude and Codex model
identities reports `filesystem_enforced: true` with 30 controls for both hosts,
and the final candidate profiles report `isolation_supported: true`. The
authenticated startup evidence, selected-plugin visibility, Claude hook
marker, Codex capability decision, and candidate profile freeze satisfy the
host certification gate. Remaining blockers are product and evidence outcomes
inside the workflows, recorded below.

On 2026-09-22, using the VM's transferred Codex credential without an
interactive login, a real `codex exec --json --ephemeral` startup ran inside
the same bubblewrap adapter with `CODEX_HOME` bound to an isolated writable
state directory and the credential file mounted read-only. The command exited
0, emitted a normal thread/turn/usage trace with the model recorded in the
archived suite 7 manifest cited above, and returned the sentinel `CODEX_VM_PROBE_OK`. The adapter had to expose only the resolver,
hosts, NSS, and CA bundle needed for network startup; those files are
read-only. This is non-scored startup evidence. It proves one authenticated
Codex path on this VM, but does not yet prove global-instruction exclusion,
selected hook execution or the frozen host profile required
for candidate scoring.

The same path was then exercised through `tests/reliability/hosts.py`'s
`run_host` launcher. It completed with exit code 0 and returned
`CODEX_FORMAL_PROBE_OK` inside the sandbox. Codex's JSON trace has thread,
turn, assistant-item, and usage events but no model field; the certified
adapter binds the frozen explicit model argument, whose identifier is in the
archived suite 7 manifest cited above, to a real
`thread.started` event and records that source in the execution receipt.

On 2026-09-22, the VM's declared Claude credential was copied into an
isolated `CLAUDE_CONFIG_DIR` as `.credentials.json`, with its temporary files
redirected into the same writable state directory. The real Claude Code
`2.1.278` launcher then completed inside bubblewrap, reported the model
recorded in the archived suite 7 manifest cited above, read the fixture, and
returned `CLAUDE_FORMAL_PROBE_OK` with
exit code 0. The first attempt correctly failed closed when Claude tried to
create its default temporary directory; the launcher now routes `TMPDIR` into
the declared state directory automatically. This remains non-scored startup evidence and
does not yet prove global-input exclusion or selected hook execution.

A follow-up launch mounted the repository's `agentic-sdlc` plugin directory
read-only. Claude completed the same probe, returned the sentinel, and its
initialization trace listed `agentic-sdlc` as a loaded plugin. This proves
selected-plugin visibility; hook execution and denial of unselected/global
inputs remain separate certification checks.

The selected-plugin hook boundary was then exercised with a temporary plugin
whose `PostToolUse`/`Skill` hook wrote a marker only in the fixture. Claude
invoked the selected skill, the hook marker contained `hook-ran`, and the
launcher completed with exit code 0. The trace also showed the selected plugin
and skill being loaded. This is direct hook evidence for Claude; the frozen
startup evidence records global/unselected-input denial and the corresponding
Codex capability decision for candidate execution.

The scenario oracle definition was amended to use the same Linux bubblewrap
boundary when `sandbox-exec` is unavailable. On the VM its canary reported
`sandbox_enforced: true` for all four scenarios. The untouched deterministic
fixtures correctly produced trusted failures for `fresh_feature`,
`delegation_resume`, and the seeded `qa_failure`, while `mature_escalation`
passed; these are behavior outcomes, not infrastructure gaps.

With the immutable baseline suite transferred to the VM, candidate suite 7 was
frozen against the upgraded host profiles and completed all 24 slots. Each
slot retained a fixture, independent oracle input, execution receipt and raw
host trace. Every trace contains a rejected provider rate-limit event; no model
turn was available for product evaluation. The original scorecard therefore
contained false product-failure classifications. The correction record and
derived scorecard reclassify all 24 slots as infrastructure failures, retaining
all 240 observations as unverified.

The deterministic proof after the adapter changes is 102 runtime tests (run
with `AGENTIC_HOST_KEY` unset; the VM's interactive shell exports that key,
which breaks the test that expects it) and 116 evaluator tests with 6 macOS-only
skips. The current host adapter missed Claude's structured `api_error_status`
field, which caused the nine false product-failure classifications. The neutrality and PII scan now passes with zero findings after preserving
older detailed trial records in a hash-verified archive and keeping readable
operator notes neutral. Remaining work is to close the rubric instrumentation
gap, refresh Claude authentication, fix the Codex delegation checkpoint loss,
and obtain reviewed fresh trial slots before claiming the 90-point acceptance
target.

## macOS launch boundary (2026-09-23)

The macOS offline canary now identifies `sandbox-exec` as its mechanism, and
actual host commands are wrapped in a profile generated by the same function.
The profile permits fixture and explicitly declared state-directory writes,
selected runtime/plugin reads, and exact allowlisted auth-file reads. Unknown
mechanisms fail before launch. A kernel-backed test executes a child through
the wrapper and confirms fixture/state writes while denying an outside read.
The outside-read check covers file contents: macOS currently needs global
file metadata access for installed host startup, and the canary records that
metadata remains visible. The wrapper denies signaling unrelated host processes.
Read permission is path-scoped, not inode isolation: a pre-existing hard link
inside a selected plugin/runtime root remains readable even when its other path
is denied. The coordinator must treat every selected root and its contents as
trusted input. The canary reports `inode_alias_isolation: false`; workflows
requiring that stronger capability remain unsupported on this adapter.
This closes the earlier gap where a passing offline canary could coexist with
an unwrapped macOS host launch. A blind review then found that the first
wrapper could not start the installed Claude binary. A red/green smoke test
isolated its required read to the system timezone database; wrapped
`claude --version` and `codex --version` now both exit successfully on this
Mac. macOS profiles require an explicit writable
state directory. An auth file nested inside the fixture or writable state
directory now fails preflight, and the canary checks that an allowed external
auth file cannot be written. Multiply linked auth files also fail preflight.
To prevent the sandboxed worker from creating a writable hard-link alias,
every allowed auth file must reside on a different filesystem from the fixture
and writable state directory. This does not pin the credential's path identity
against an external concurrent writer between validation and launch. The
profile therefore reports macOS auth-file launches unsupported and blocks them
from scored trials; the path rule is only a canary/preflight control. Auth files
beneath broadly readable selected plugin, runtime, or system roots also fail
preflight; the canary verifies a sibling of an allowed auth file remains
unreadable. Real Claude/Codex authentication, selected-hook execution,
and global-input exclusion under this exact launch wrapper still require
separate startup certification; the canary alone does not authorize trials.

## Startup-evidence freshness (2026-09-23)

The Linux Claude credential expired and was refreshed on the VM. Startup proof
now uses schema version 2 and must match the current credential-file hashes,
host executable hash, isolation-probe hash, and host identity. An older proof,
including the previously retained schema-1 proof, fails preflight rather than
certifying a changed authentication or host configuration. The earlier Linux
startup and hook observations remain historical evidence; they do not certify
the refreshed profile. A new no-inference startup/hook/global-input check and
reviewed profile freeze are required before more scored trials.

## Observer field inventory (2026-09-23)

`python3 tests/reliability/observations.py` exercises the actual replay path
against all four frozen pristine fixtures and compares emitted fields with the
25 frozen rubric assertions. It currently emits fields for only 3 assertions;
22 are absent. The three emitted values are not positive proof. The command
exits nonzero and lists missing assertion IDs. `suite.run_trial` now checks
this inventory before reserving a slot, so an incomplete observer surface
cannot consume another scored trial. Field presence is necessary but remains
insufficient: every assertion still needs independently reviewed positive and
negative controls before live scoring is certified.

## Evaluation ceiling and first evidence contracts (2026-09-24)

[`CEILING.md`](CEILING.md) classifies every assertion by the channel that
could observe it. Before this stage the evaluator could credit nothing; A-class
observers alone reach at most 12 points; wiring the frozen
challenges into the trials (amending scenario inputs) reaches 76 with 8 of 12
vetoes observable; only evaluator-owned approval and peer channels make all
12 vetoes observable. Acceptance is structurally unreachable until the
operator decides on those amendments; no product work changes that.

The observer layer now has schema-2 inputs with parent-held context (host,
snapshot version, pre-launch user-file inode/ctime identities). Two evidence
contracts are implemented with known-good and known-bad controls:
`contracts.preservation` (unchanged bytes and identities, no host write-tool
attempt on a user path under the fixture root, a successful host invocation of
the exact snapshot upgrade skill -- a `Read` of the exact file or the exact
plugin-namespaced `Skill` form, see Stage 7a below -- a trace without
extraction issues, and a journal stamped with the snapshot version keeping
user records) and
`contracts.inputs` (requested setup options recorded type-exactly in the
installation and both exact entrypoint files read). A Claude `Skill`-tool
invocation naming the shipped skill exactly now also counts as an invocation
alongside a `Read` of it (see Stage 7a below). The scope veto now fails only when user files were
actually touched, not when an upgrade was skipped. All 24 retained suite 9
records replay identically under the previous and new observer code. The field
inventory reports 21 of 25 assertions missing. No trial has run.

Review found a certification blocker for all trace-derived credit: host stdout
is written to a regular file and tool commands share the host's PID namespace,
so a same-user child could plausibly forge trace events through `/proc`. Host
stdout must be piped to the parent and that access removed, then certified,
before any scored trial.

## Stage 7a (2026-09-25)

Advances CEILING.md's "Recommended build order" step 1 (the A-class observer
set) with two narrow additions, both with known-good and known-bad controls in
`test_observations.py`. A blind-review round blocked the first cut of this
stage on `lifecycle.recovery` granting false credit; the fix below is the
remediated version.

- `_skill_read` now also recognises a Claude assistant `tool_use` block named
  `Skill` whose `skill` input names the shipped skill's exact
  plugin-namespaced form (`plugin:skill`, the owning plugin's own manifest
  name -- neither shipped manifest under `plugins/` declares any other
  namespace) with a `responded` result, exactly as it already did for a
  matching `Read`. The bare skill-directory name is deliberately rejected, not
  just unhandled: `hosts.py` launches Claude with
  `--setting-sources project,local`, so a bare name can resolve to a
  same-named project skill the candidate plants at `.claude/skills/<name>`
  inside the fixture, crediting a candidate-authored stand-in as the shipped
  skill. A wrong name, a similarly spelled name, the bare name, a wrong
  namespace, a prose mention, an errored result, a missing result, a
  non-string `skill` input, a non-string tool id, and the same block
  appearing under a Codex host context all still yield unverified.
  The namespaced form is not a proof of origin on its own. Review showed, on
  Claude Code 2.1.281, that a project skill at
  `.claude/skills/agentic-os:agentic-init/` present at launch overrides the
  plugin skill and produces an identical `Skill` event; only the following
  "Base directory for this skill" text differs. This is unreachable in the
  two scenarios that use the rule (single launches into harness-written
  fixtures; skills planted mid-run were not picked up), but it must be closed
  by also binding that base directory to the snapshot before the rule is
  applied to a resumed segment, where the first run could plant a skill.
- `lifecycle.recovery` (`recovery_verified`, scenario `delegation_resume`) is
  now a partial A-class observer, gated on schema 2 like the other two
  contracts, that **can only fail or withhold credit -- it never passes.** It
  compares the harness's own pre-resume boundary snapshot (`checkpoint`,
  already captured by `suite.py`) against the final replayed oracle result,
  using two fields both sides already report: `checkpoint_preserved` (byte
  identity of the frozen `.fixture/checkpoint.json` identifier) and
  `remaining_work_verified` (independent sandboxed execution of the peer-B
  function required to stay unfinished until resume). It fails on an observed
  contradiction -- the checkpoint identifier diverging at the boundary or by
  the end, the boundary already showing the pending work done, or the final
  replay showing it never finished -- and is unverified otherwise, including
  the case that looks like a clean resume (checkpoint held, boundary still
  open, final replay finished). That case is deliberately never credited: a
  boundary capture with empty `artifact_claims` (no handoff, no durable task
  state -- run 1 only dropped the interrupt sentinel) followed by a "resume"
  that reimplements both peers from scratch with no `.agentic` state at all
  produces exactly that pattern, and challenge-spec.json's `lifecycle.recovery`
  negative case requires that a silently-started replacement run which drops
  history and resets counters must never pass -- `scenarios.py` already
  documents that a preserved checkpoint does not demonstrate recovery. Neither
  retained field says anything about run/assignment identity, an event
  prefix, or consumed counters, and no post-resume snapshot of
  `.agentic`/`docs/superpowers/runs` is retained in observer inputs, so a pass
  verdict has to wait on that evidence -- explicitly future work. Gating on
  schema 2 keeps every retained suite 9 `delegation_resume` record (all schema
  1) replaying to the unchanged `None` it always produced; this is checked
  directly against the six real suite 9 `delegation_resume` traces in
  `test_observations.py` (tracked in-repo in the suite 9 evidence archive),
  which all replay byte-for-byte identically, and separately against the
  reviewer's exact false-credit repro (real fixture, real `capture_boundary`,
  real oracle, no mocks), which now replays to `None`.

The field inventory count is unchanged (`lifecycle.recovery`'s key was already
present, defaulted to `None`); what changed is that its value is now computed
instead of hardcoded. Because a pass is not yet reachable, `lifecycle.recovery`
contributes 0 of its 4 points even on a perfect run; the A-class ceiling today
is 8 points (preservation and inputs), with 12 remaining the ceiling once the
missing recovery evidence is retained. B-class choreography, the C-class
evaluator channel, and launcher trace hardening remain deferred per the
operator's 2026-09-25 direction to avoid over-engineering (see Status below).

## Stage 7b (2026-09-25): trace channel hardened

`hosts.run_host` now gives the host its stdout and stderr as `AF_UNIX`
socketpair ends and drains them into the same retained trace files, keeping
the size limit (an oversized trace is cut at `MAX_TRACE_BYTES + 1`, which
still fails the existing check). A tool descendant that reopens
`/proc/<host pid>/fd/1` gets `ENXIO`; `pidfd_getfd`, `PTRACE_ATTACH` and
`/proc/<pid>/mem` are denied by Yama `ptrace_scope` 1, which review confirmed
still holds inside bubblewrap's user namespace. A host with startup evidence
is certified only with bubblewrap and `ptrace_scope` > 0. The Linux canary now
passes 31 controls, adding `descendant_trace_forgery_denied`; with its stdout
swapped back to a plain pipe the grandchild's forged write reaches the output
and the probe fails closed. Launch profiles and signed command receipts record
the trace channel. Committed after two blind reviews passed.

This removes the forgery path found in review; it does not certify the hosts.
Retained startup evidence no longer matches the probe hash and must be
re-captured. macOS is never trace-certified (no equivalent control verified).
The fix assumes the real host does not hand its own stdout to tool commands,
hooks or MCP servers; startup re-certification must check that for both
hosts. Review follow-ups are logged in REOPENING.md, Round 33.

## Status as of 2026-09-25

- **Stage 5 (installer and setup/upgrade/uninstall):** implemented. The shared
  installer has compare-and-swap operator decisions (`d0c4f10`); the three
  agentic-os skills and the reference executors route journal and scaffold
  writes through it (`5656c4b`), and the acceptance matrix exercises the
  shipped installer. Live host runs of the skills remain uncertified.
- **Stage 6 (workflow integration):** at the skill-text level every remaining
  direct write to legacy run ledgers is scoped to unmanaged runs, and managed
  runs use runtime operations (`sdlc-runs`, QA helpers, telemetry export).
  Host-level wiring remains uncertified.
- **Stage 7 (evaluation):** CEILING.md's A-class build-order step is
  implemented but not fully creditable: two evidence contracts that can pass
  (`180ab06`), plus Claude `Skill`-tool recognition and a partial
  `lifecycle.recovery` rule that can only fail or withhold, never pass, until
  run/assignment identity and an event prefix are retained (Stage 7a, above).
  Today's A-class ceiling is 8 of a possible 12 points. Per the operator's
  2026-09-25 direction to avoid over-engineering, wiring the frozen
  challenges into scenarios and the evaluator-owned approval/peer channel
  were deferred; launcher trace hardening is done (Stage 7b, above) but the
  hosts still need re-certification. Consequently the 90-point acceptance
  cannot be claimed and no scored trial is planned.
- **Originality attestation:** the fingerprint store used to regenerate
  `tests/lib/originality-attestation.json` is not available to the operator or
  this environment. CI's `--verify-attestation` step therefore fails for files
  changed since the last attestation until someone with the store re-attests
  or the maintainer retires that check. No other check depends on it.
