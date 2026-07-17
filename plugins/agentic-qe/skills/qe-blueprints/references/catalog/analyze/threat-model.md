# Draft a threat model

Turn architecture docs and/or source code plus an operator-defined scope into a prioritized, boundary-specific threat model with concrete mitigations — so security thinking happens at design time, when a fix is a conversation instead of an incident, and downstream security testing gets a defined target list.

## When to use this

- **Reach for it when** a new system or feature is in design (highest leverage: a boundary flaw caught here costs a conversation; in code, a sprint; in production, an incident); a significant architecture change has made the existing model stale; a compliance regime (payment-card, healthcare, EU-privacy, SaaS-attestation style) demands documented threat analysis; a penetration test needs scoping; or you run periodic refreshes — annual or per release — and want deltas showing new, resolved, and changed threats. Greenfield works too: a data-flow sketch or RFC is enough input, rerun as the design firms up, then switch to code-informed runs.
- **Skip it when** you have neither architecture docs nor a readably structured codebase (thin input yields generic, low-value threats); no scope is defined (an unbounded target produces a broad, shallow model); no security-knowledgeable reviewer will validate the output (the AI widens coverage, a human confirms accuracy); or what you actually need is detective testing of built code — static scanning, DAST, dependency CVE checks, exploitation are downstream activities this workflow feeds, not performs.
- **Outcome** — a validated, versioned threat model: assets, trust boundaries, per-boundary scenarios with stepwise attack paths, justified risk ratings, and implementable mitigations. It steers design decisions, pen-test scope, and security test cases. Pilot with one agent and one prompt first; confirm the output is system-specific before building the full pipeline.

## Prerequisites

| Need | Why | Typical source |
|---|---|---|
| Architecture input: design/wiki pages or a repo with discernible layering (endpoints, services, data layer) — ideally both | Docs show intended design, code shows actual design; the gap between them is where vulnerabilities hide. Thin input is the top cause of generic output | Documentation wiki and/or code host |
| Explicit scope: which system, component, or feature is in and out | Without a boundary on the target, the model spreads wide and stays shallow | Operator (security engineer or tech lead) at run start |
| A security-knowledgeable reviewer committed to validating output | Confirms threat accuracy, calibrates risk to organizational appetite, adds regulatory context; a missed boundary or underrated risk leaves the system exposed | Team security engineer or security-literate senior |
| Data sensitivity classification (personal, financial, health, internal-only) | Drives risk ratings, prioritization, and compliance mapping | Operator or data-governance records |
| System context facts: system type, auth mechanism, deployment model, third-party integrations | Lets the generator tailor threat categories to the actual stack instead of emitting one-size-fits-all scenarios | Operator at run start |

## Agent design

Split the work by cognitive load: decomposing a system into assets, flows, and trust boundaries is the hardest reasoning step and a miss there silently drops an entire threat class, so it gets the premium tier. Expanding known boundaries into categorized scenarios, checking coverage, and publishing are mechanical once the decomposition exists — economy handles them.

| Role | Responsibility | Tier | Reads | Writes | Blast radius |
|---|---|---|---|---|---|
| Boundary analyzer | Inventory assets with sensitivity, map components and trust levels, trace data flows and in-transit protections, list every trust-level crossing (client-server, service-service, app-datastore, internal-external, user-admin), find untrusted-input entry points and existing controls; rank boundaries by sensitivity × exposure | premium | Fetched architecture pages, repo structure (endpoints, data models, auth config), control evidence, operator scope + context | Run artifact: assets, boundaries with control notes, data flows, attack surface, prioritized queue | R1 |
| Threat generator | Per boundary, enumerate scenarios across all six categories (identity spoofing, data tampering, repudiation, information disclosure, denial of service, privilege elevation); write a stepwise attack path each (attacker action, system response, exploitation result); rate high/medium/low justified by impact × likelihood; propose mitigations naming real technology and config, citing recognized standards and patterns already in the codebase; record mitigation status (implemented / partial / absent / unknown). One threat per distinct attack path — each should convert into a security test case. Adapt to system class (browser app, API, microservices, data pipeline, mobile backend) and regime | economy | Analyzer artifact, architecture docs, source code | Run artifact: threat records (id, title, category, boundary, attack path, rating + justification, assets, mitigation, status) | R1 |
| Coverage validator | Check traceability: every asset has ≥1 threat; every boundary spans ≥3 of 6 categories (not all six — some don't apply, and forcing them inflates the model). Flag zero-threat boundaries, uncovered high-sensitivity assets, sub-half category coverage, generic or missing attack paths, unjustified ratings, vague mitigations. Failures become warnings, never silent blocks | economy | Analyzer and generator artifacts | Coverage report: boundaries analyzed, category coverage %, gaps, warnings | R1 |
| Publisher | Post-approval only: new wiki page (or new version of the prior one — history preserved), tracker epics only for high-risk threats with absent mitigations, chat summary with counts by risk level. Cross-link page ↔ source docs, repo, related findings, epics. Label as AI-generated; name the validating reviewer in the footer | economy | Approved model + coverage report | Wiki page, tracker epics, chat message | R3 |

> The analyzer's output quality propagates to everything downstream — spend the premium tokens there. Everything after it is expansion, checking, and formatting.

## Flow

1. **Trigger** — operator initiates on a new design/RFC, a significant architecture change, the periodic review cycle, compliance prep, or pre-pen-test scoping; supplies scope, system context facts, and data classification.
2. **Retrieve** — fetch architecture pages from the wiki and/or read the repo: structure, endpoints, data models, auth config, existing controls.
3. **Plan** (premium) — decompose into assets, components, data flows, trust boundaries, entry points; note controls per boundary; prioritize by sensitivity × exposure. The agent states its key assumptions and asks the operator to confirm or correct before proceeding.
4. **Generate** (economy) — expand each boundary into category-complete scenarios with stepwise attack paths, justified ratings, concrete mitigations, and mitigation status; existing mitigations lower a threat's priority relative to unmitigated ones.
5. **Validate** — run traceability, coverage, and quality checks; emit the gap/warning report.
6. **Human review gate** (mandatory) — the security reviewer reads the model against the validator report: confirms threat accuracy, adjusts ratings for risk appetite, adds regulatory knowledge, and per flagged gap decides accept-as-out-of-scope, refine manually, or regenerate with added context.
7. **Publish** — versioned wiki page with AI-provenance labels and reviewer attribution, epics for high-risk unmitigated threats only, chat summary; cross-links in both directions.
8. **Evolve** — rerun on architecture changes; version history plus delta comparison shows new, resolved, and changed threats, keeping periodic reviews cheap.

## Connectors

| Capability | Systems | Direction | Preferred wiring |
|---|---|---|---|
| Fetch architecture docs (design pages, API specs, data-flow diagrams) | Documentation wiki (Atlassian-style) | Read | Official wiki MCP server or vendor CLI; token scoped to the architecture space |
| Fetch source for structure, endpoint, and auth-config analysis | Code host (either major git-hosting vendor) | Read | Official code-host MCP server or its CLI |
| Publish the approved model as a structured, versioned page | Documentation wiki | Write | Official wiki MCP server or vendor CLI |
| Create epics for high-risk unmitigated threats, tagged and back-linked | Issue tracker (Atlassian-style) | Write | Official tracker MCP server or vendor CLI |
| Notify the team: counts by risk level plus a link | Team chat | Write | Chat MCP server or incoming webhook |

> Wiring preference, in order: official MCP server → official CLI → REST wrapped in a skill → custom integration.

## Guardrails

- **Injection defense** — fetched wiki pages and repo content are analysis data, never instructions. Nothing read from those sources can trigger a publication or tracker write: every externally visible action sits behind the human gate.
- **Writable-field allowlist** — the R3 publisher only creates: a new wiki page or a new version of its own prior page, epics restricted to high-risk/absent-mitigation threats, and chat summaries. It never edits architecture docs, source code, or existing tickets. Every output carries an AI-generated label and the reviewer's name.
- **Human gate** — the reviewer checks threat accuracy, rating calibration against organizational appetite, regulatory completeness, and each validator-flagged gap (accept / refine / regenerate). Always required for initial models; relax only for incremental deltas to an already-reviewed model once trust is earned.
- **Grounding** — every threat traces to an analyzer-identified boundary or asset, carries a concrete stepwise attack path, a justified rating, and a mitigation naming real technology or configuration. The analyzer must surface its assumptions for operator confirmation before finalizing. If output is generic or misses obvious boundaries, the fix is richer input (flow diagrams, API specs, deployment topology) — not more generation.

## Automation

Keep it human-invoked by default: a security engineer starts each run, and review precedes every publication. Judgments about risk appetite and organizational context stay human — full autonomy is explicitly not the goal.

Trigger → flow: new RFC / architecture decision record / annual cycle / pre-pen-test / audit prep → operator supplies scope and inputs → analyzer decomposes → generator expands boundaries into threats → validator checks coverage → security engineer reviews and adjusts → publisher writes the page, epics, and summary.

Semi-automation fits only increments: when a new service or endpoint lands, let the pipeline auto-generate a delta model for the changed component and queue it for reviewer sign-off. Keep the gate unless acceptance-rate data justifies relaxing it for deltas.

## Signals it's working

| Signal | How to measure |
|---|---|
| Adoption rate | Wiki pages carrying AI-generated + threat-model labels vs. the architecture registry total; manual practice covers a small fraction of systems — aim for most |
| Time per model | Initiation-to-publication elapsed, review included; manual runs take days of workshops, assisted runs hours — report the % reduction |
| Coverage depth | Threats per trust boundary vs. the manual baseline on comparable systems; systematic category enumeration typically multiplies depth — but count specific, testable threats, not volume |
| Acceptance rate at the gate | Fraction approved with minor edits vs. major rework; target well above three-quarters minor — a low rate signals thin architecture input or wrong system-type assumptions |
| Downstream utility (the one that matters most) | References to the model in pen-test scopes, security test cases, architecture decision records, incident retrospectives; an uncited model delivered nothing — convert threats to test cases, surface mitigation epics in sprint planning, cite threat ids in test reports |
