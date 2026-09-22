# Evaluation readiness — live certification deferred by approved amendment

Baseline commit: `dabd182e049cc6fb52007da988bf03762130c459`.
Implementation branch: `codex/framework-reliability`.
Live trials consumed: **24 of 48**. The 24 baseline slots were recorded on
2026-09-21, but every trial ended as an infrastructure failure because Claude
and Codex were not certified for isolated execution. The baseline report is
therefore **F / 0.0 demonstrated points with 240 unverified observations**;
this is a coverage result, not a product-quality grade. Candidate trials remain
0 of 24 and have not started.

The initial blind review evaluated staged tree
`111b0002e6d0a693f3490950a44d78a8af42c854` with separate correctness/recovery
and enforcement/contracts reviewers. Both blocked continuation. The first remediation was then reviewed at tree
`2f9aefd73d4431135566d99ddd58c3ce987205bc` and remained blocked. Passing offline
harness tests do not establish evaluation coverage or host certification.

## Findings and remediation

| Finding | Current disposition |
|---|---|
| Only preservation can receive positive rubric credit | Open. Do not freeze or run scored trials. |
| Host defaults, model identity, global hooks/plugins not frozen | Explicit profiles, drift checks and 16 offline macOS filesystem controls added. A Linux bubblewrap adapter now passes 30 kernel-backed controls on the Ubuntu VM and wraps Linux launches in the same boundary. Actual host startup/authentication and retained hook execution remain uncertified; launch fails closed. |
| Interrupted process can restart instead of resume | Boundary snapshots added; authenticated ownership and budget comparisons remain open. |
| Candidate can forge unittest output and exit successfully | Parent evaluates returned values; forged unittest text is rejected. Included in the passed definition-checkpoint review; live certification remains deferred. |
| Reports accept unreserved or unsupported result JSON | Added source-archive/baseline linkage, execution traces/model/fixture bindings and recomputation from retained source inputs. Fabricated candidate-grade and rehashed verdict regressions are rejected. Included in the passed definition-checkpoint review; live certification remains deferred. |
| Oracle code executes outside the host sandbox | Added macOS sandbox with tested read/write/network/fork restrictions. Missing enforcement yields unverified; no unrestricted fallback. Included in the passed definition-checkpoint review; live certification remains deferred. The hash-frozen `scenarios.py` oracle still recognizes only sandbox-exec, so on Linux every oracle result is unverified until a definition amendment is approved. |

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
`0.155.0-alpha.9.2`, and Cursor `3.20.21` installed. The frozen baseline now
uses the supplied explicit identities `claude-opus-5` and `gpt-6-astra`.
Claude and Codex both passed the filesystem canary, but neither profile is
launch-ready: the probe cannot certify authentication, global instruction
exclusion, or retained plugin-hook behavior under the actual host sandbox.
Cursor remains static-compatibility-only in this evaluation.

Bounded read-only startup probes then reached both configured hosts. Claude
reported `model: claude-opus-5` in its init/result trace and stopped at the
requested budget boundary; Codex completed a read-only prompt with
`gpt-6-astra` and emitted a normal turn-completed usage record. These probes
establish model acceptance and an available authentication path only. They are
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
and `isolation_supported: false`. Remaining blockers before any candidate slot:

1. A real host startup probe under bubblewrap proving host-level exclusion of
   global inputs and execution of selected plugin hooks. Codex now has an
   explicit temporary auth-file/state configuration and a successful startup
   trace; Claude still has no declared VM credential path, and neither host
   has yet completed the global-input/hook proof.
2. The installed hosts moved after the baseline freeze (Claude Code `2.1.278`,
   Codex `0.155.1`). The candidate profile must be re-frozen; the baseline
   evidence is unchanged.
3. The Linux scenario oracle (see the findings table).

On 2026-09-22, using the VM's transferred Codex credential without an
interactive login, a real `codex exec --json --ephemeral` startup ran inside
the same bubblewrap adapter with `CODEX_HOME` bound to an isolated writable
state directory and the credential file mounted read-only. The command exited
0, emitted a normal `gpt-6-astra` thread/turn/usage trace, and returned the
sentinel `CODEX_VM_PROBE_OK`. The adapter had to expose only the resolver,
hosts, NSS, and CA bundle needed for network startup; those files are
read-only. This is non-scored startup evidence. It proves one authenticated
Codex path on this VM, but does not yet prove global-instruction exclusion,
selected hook execution, Claude startup, or the frozen host profile required
for candidate scoring.

The same path was then exercised through `tests/reliability/hosts.py`'s
`run_host` launcher with `allow_uncertified_probe` explicitly enabled for this
non-scored check. It completed with exit code 0 and returned
`CODEX_FORMAL_PROBE_OK` inside the sandbox. The retained Codex JSON trace has
thread, turn, assistant-item, and usage events but no model field, so
`observed_model` remains null by design; the evaluator does not infer a model
from the requested command. This validates launcher integration and bounded
execution while preserving the evidence gap around host-reported model
identity.

The host profile is not frozen and preflight does not pass, so candidate trials
remain 0 of 24. The deterministic proof is 102 runtime tests (run with
`AGENTIC_HOST_KEY` unset; this VM exports the key in its shell, which breaks
the CLI test that expects it to be missing) and 110 evaluator tests with 9
macOS-only skips. Tracked text changed, so the originality attestation needs a
maintainer re-attestation. The 8 existing neutrality findings are unchanged.
