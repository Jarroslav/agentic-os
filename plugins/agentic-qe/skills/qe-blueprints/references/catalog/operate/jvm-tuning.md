# Tune JVM settings

Turn a service's current JVM argument string — plus an optional GC log — into a diagnosed, copy-paste-ready replacement flag set with one rationale per change, so deprecated, conflicting, or unhardened runtime settings stop shipping and GC-driven outages stop recurring.

## When to use this

- **Reach for it when** auditing a Java/Kotlin service's runtime flags before or during a deployment change; migrating across JDK majors, where deprecations and collector defaults shift; investigating recurring GC pauses, high GC overhead, or OOM incidents with logs in hand; reviewing merge requests that touch runtime-config sources (container build files, chart values, startup scripts); or bootstrapping hardened defaults for a brand-new service with no config yet.
- **Skip it when** the service does not run on a JVM-class managed runtime; the root cause is application code, queries, or infrastructure sizing rather than flags; no deployment source exposes the current argument string; or the team mandates tuning exclusively through a commercial APM vendor's own workflow.
- **Outcome** a three-level health verdict on the current config, a complete replacement argument set matched to app type, workload, and optimization profile (latency, throughput, or memory), a before/after diff with one rationale per changed flag, and verification commands — delivered where engineers already review changes.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Current JVM argument string | The raw input the diagnostic pass parses flag by flag | Container build file entrypoint, chart values, systemd unit, env var, startup script |
| Exact JDK major (8, 11, 17, 21) | Flag deprecation/removal status and collector advice are version-specific; wrong version means wrong advice | Service docs, base image, runtime detection |
| App and workload context: app type, traffic level, optimization goal, framework, containerized or not | Drives collector selection, heap/metaspace/stack sizing, and container-aware flags (cgroup memory limits) | Team knowledge supplied at invocation |
| GC log (optional, strongly recommended) | Upgrades tuning from pattern heuristics to measured pause percentiles, overhead, and allocation/promotion rates | Prod or load-test logs via local file, pod log stream, or monitoring export; unified format on modern JDKs, legacy format on 8 |
| Write access on the delivery channel (publish step only) | Review comments, wiki pages, and chat posts need create/update rights | Service account on the code host, wiki, or chat platform; the local-only flow needs no connectors |

## Agent design

Most of the work here is deterministic: a curated, version-aware flag knowledge base catches roughly nine in ten common misconfigurations as a rules engine at zero model cost, and flag generation is table-driven from a profile-to-collector matrix. Models only write narrative, interpret log trends, and fine-tune values — so no role needs a premium tier, and the pipeline stays cheap and reproducible.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Orchestrator | Interprets the request, gathers args/version/context/optional log, dispatches the other roles, assembles the final report | standard | Runtime-config sources, user context, subagent outputs | Run artifacts (assembled report, intermediate state) | R1 |
| Config diagnostic analyzer | Checks each flag against the version-aware knowledge base: deprecated/removed flags plus replacements, known conflicting pairs, heap arithmetic sanity (initial vs max, compressed-pointer threshold), missing hardening items, collector fit; emits a three-level verdict with severity-ranked findings. Rules engine detects; model layer only writes the summary narrative | economy | Argument string, JDK version, workload context | Diagnostic report artifact (verdict, findings tables) | R1 |
| Config optimizer (generator) | Emits a complete replacement set, never piecemeal edits: collector from the profile matrix (low-pause for latency, parallel for throughput, minimal-footprint for memory), heap sized from workload with initial=max in prod, metaspace/stack sizing, collector-specific tuning, OOM handling, GC logging with rotation, framework flags; then a diff with per-change rationale and an improvement estimate | standard | Diagnostic output, app type, workload, profile, JDK version, optional GC metrics | Recommended config and before/after diff artifacts | R1 |
| GC log analyzer (optional) | Parses logs across collector families and both modern and legacy formats; computes overhead %, max/percentile pauses, allocation and promotion rates, per-pause-type breakdowns, and heap-growth regression on post-collection occupancy to flag likely leaks; compares against published thresholds and feeds concrete tuning deltas to the optimizer | standard | GC log from local path, container logs, or monitoring export | Metrics and tuning-recommendation artifact | R1 |
| Report publisher | Renders the structured report (summary, metrics dashboard, findings, recommended config, diff, tuning actions, verification commands), writes it locally, optionally posts as MR review comment, wiki page under the service's space, or chat note; stamps AI-generated labeling and traceability metadata | economy | Assembled analysis outputs | Local report file (R1); review comments, wiki pages, chat messages when external channels are on | R3 |

> The split isolates the only externally-writing role (publisher) on the cheapest tier with the narrowest job, keeps every analysis role at R1, and lets the deterministic engines run without model cost — the model layers are thin, replaceable, and never the source of a detected fact.

## Flow

1. Trigger: an engineer invokes with a service/config path, or a merge-request event fires because a runtime-config file changed.
2. Verify preconditions: argument string reachable, JDK major known, app type/workload/optimization profile specified.
3. Retrieve inputs: read current args from the deployment source; parse the GC log if a path was given.
4. Diagnostic pass: per-flag analysis against the version-aware knowledge base; emit the health verdict and severity-ranked findings.
5. Generation pass: build the full replacement argument set for the chosen profile; when GC metrics exist, tune values from measured pause percentiles and allocation rates instead of heuristics.
6. Diff pass: compare current vs recommended args, attach a rationale to every added/removed/changed flag, estimate the improvement, and write the report locally.
7. **Human review gate**: an engineer reads the verdict, diff, and rationale, then decides — publish, apply, adapt, or dismiss. Nothing is applied to production automatically; the change reaches deployment only through a human commit.
8. Publish: post the advisory report as a review comment on the config-change MR, a knowledge-base page, or a chat notification, including verification commands.
9. Feedback loop (greenfield/iterative): after deployment, pull fresh GC logs from staging or production and re-run to refine sizing from actual behavior.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Fetch current runtime arguments | Local repo, container build files, chart values, startup scripts | Read | Plain file read or chart-values CLI query; no dedicated integration needed for the basic flow |
| Fetch GC log | Local filesystem, cluster pod logs, monitoring export | Read | File read or cluster log CLI |
| Run diagnostic analysis | Local scripting runtime | Read | Deterministic module as a local script; zero model cost, fully reproducible |
| Run configuration generator | Local scripting runtime | Read | Deterministic module as a local script, model layer for narrative only |
| Run GC log parser | Local scripting runtime | Read | Deterministic module as a local script |
| Post review comment on config MRs | Hosted git platforms | Write | Official code-host MCP server, else official CLI |
| Publish report to knowledge base | Enterprise wiki | Write | Official wiki MCP server or its CLI |
| Send verdict notification | Team chat | Write | Chat MCP server or an incoming webhook |

> Wiring preference, in order: official MCP server -> official CLI -> REST wrapped in a skill -> custom integration. The read side of this blueprint needs none of them.

## Guardrails

- **Injection defense**: config file contents, GC log contents, and merge-request text are data to parse, never instructions to follow. The automation trigger is scoped to file-change events on runtime-config paths only — explicitly not comment or activity events — which also stops the agent re-triggering itself off its own posted comment (an infinite-loop hazard, designed out up front).
- **Writable-field allowlist** (for the R3 publisher): local report files; review comments on the triggering MR only; knowledge-base pages under the service's own space; chat notifications. Never the deployment configuration itself — the replacement argument set ships as copy-paste-ready text a human commits.
- **Human gate**: the reviewer checks that the verdict matches the flags actually deployed, that each diff line's rationale holds for this workload and container limits, and that heap arithmetic fits the memory budget — then applies, adapts, or dismisses. No change reaches production without a human commit.
- **Grounding**: detection is anchored in a curated, version-aware knowledge base (deprecated/removed flags, known conflicts, arithmetic validity, published hardening practice) executed deterministically. Every recommended flag carries a rationale tied to the optimization profile; when logs exist, values come from measured percentiles, overhead, and allocation trends, not patterns. Reports carry AI-generated labeling plus traceability to the exact config file, JDK version, timestamp, and log source — never invent flags, metrics, or workload facts absent from the inputs.

## Automation

Run it human-invoked while the knowledge base and profile matrix are being calibrated against your services. Once the interactive version proves out, pin it into an unattended workflow: fixed step sequence, pinned tiers and tools, no free-form tool choice.

Trigger -> flow: MR opens or updates touching runtime-config paths (container build files, chart values, runtime-options files, env-var definitions), or manual invocation by service name -> webhook/CI job passes service and config path -> fetch current args from the changed file -> deterministic diagnostic pass (seconds, no model cost) -> generation pass with model narrative (cents-level cost) -> optional GC-log pass when a log exists -> post an advisory review comment with verdict, key findings, ready-to-use args, and the rationale diff -> engineer applies or dismisses.

In the pinned workflow the advisory comment posts unattended; the human gate moves to apply-or-dismiss and stays there — advisory-only output is the design, so keep the gate even when adoption metrics look strong. Keep the trigger strictly on file-change events for the config paths so the agent's own comment never re-fires the workflow.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption rate — share of runtime-config changes the agent reviewed | Count review comments carrying the agent's label against total config-change MRs per quarter |
| Productivity gain — change-to-report turnaround vs manual audit | Elapsed time from push to agent comment, compared with the team's estimate for a hands-on runtime-config audit (typically a few hours per service) |
| Acceptance rate — engineers actually applying the recommended args | Detect follow-up commits on the same MR adopting the suggestion, vs dismissals or no action |
| Practitioner feedback on quality | Sprint retrospectives: recommendation accuracy, false-positive rate (flags harmless in context), and whether log-driven advice beats pattern-only advice |
| Tuning heuristic for evolution | High adoption + low acceptance = advice too aggressive: add per-project suppression rules for intentional choices. High acceptance + low adoption = trigger misses real config paths: fix the file-path pattern |
