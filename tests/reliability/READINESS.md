# Evaluation readiness — live certification deferred by approved amendment

Baseline commit: `dabd182e049cc6fb52007da988bf03762130c459`.
Implementation branch: `codex/framework-reliability`.
Live trials consumed: **0 of 48**. No baseline or candidate grade exists.

The initial blind review evaluated staged tree
`111b0002e6d0a693f3490950a44d78a8af42c854` with separate correctness/recovery
and enforcement/contracts reviewers. Both blocked continuation. The first remediation was then reviewed at tree
`2f9aefd73d4431135566d99ddd58c3ce987205bc` and remained blocked. Passing offline
harness tests do not establish evaluation coverage or host certification.

## Findings and remediation

| Finding | Current disposition |
|---|---|
| Only preservation can receive positive rubric credit | Open. Do not freeze or run scored trials. |
| Host defaults, model identity, global hooks/plugins not frozen | Explicit profiles, drift checks and 16 passing offline filesystem controls added. Actual host startup/authentication and retained hook execution remain uncertified; launch fails closed. |
| Interrupted process can restart instead of resume | Boundary snapshots added; authenticated ownership and budget comparisons remain open. |
| Candidate can forge unittest output and exit successfully | Parent evaluates returned values; forged unittest text is rejected. Included in the passed definition-checkpoint review; live certification remains deferred. |
| Reports accept unreserved or unsupported result JSON | Added source-archive/baseline linkage, execution traces/model/fixture bindings and recomputation from retained source inputs. Fabricated candidate-grade and rehashed verdict regressions are rejected. Included in the passed definition-checkpoint review; live certification remains deferred. |
| Oracle code executes outside the host sandbox | Added macOS sandbox with tested read/write/network/fork restrictions. Missing enforcement yields unverified; no unrestricted fallback. Included in the passed definition-checkpoint review; live certification remains deferred. |

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
   reviews. Then capture and execute the 24 immutable baseline trials.

The existing runner is experimental and must not be used to publish reliability
claims. It is not an accepted Stage 0 deliverable.

The operator approved the [staging amendment](STAGING-AMENDMENT.md) on 2026-09-20.
The next gate is an independently reviewed baseline/definition freeze. Runtime
implementation may then proceed while executable observers are completed. All
live certification and acceptance requirements remain mandatory before completion.

## Definition checkpoint

`frozen-definitions.json` records the original revision, dependency snapshot and
fixed rubric/scenario/challenge hashes. `freeze_definitions.py verify` checks the
retained local archives; unit tests check the committed definition hashes and
legacy fixtures against the original schema. Archive files are deliberately kept
outside version control. No numerical grades have been established.

This checkpoint is awaiting fresh review against the approved amendment. Its
acceptance authorizes contract implementation; it does not certify the live
evaluator. Executable observers, host authentication/hooks under isolation, and
all scored trials remain required later gates. macOS-specific kernel tests are
explicitly skipped where sandbox-exec is unavailable; that is not live proof.
