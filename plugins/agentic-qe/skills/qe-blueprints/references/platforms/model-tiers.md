# Model Tiers: Picking the Right Tier per Block

Assign each agent block in a pipeline blueprint the cheapest model tier that meets its quality bar. This reference defines the three agentic-os tiers, the gate a block must pass to earn the premium tier, and the escalation path when a cheaper tier falls short.

Blueprints name concrete models in their block-customization tables. Treat every such name as an illustrative anchor for a tier — never a mandate or a version lock. Tier labels translate across any model family; the cost reasoning below is family-independent.

## The three tiers

| Tier | Assign to | Never assign to |
|---|---|---|
| **premium** | Reasoning-bound leaf steps only: test design, impact/dependency analysis, risk scoring, threat modeling, drift detection — judgments whose errors cascade downstream | Orchestrators, expansion, formatting, rule checks, retrieval, publishing |
| **standard** | The default for nearly everything: the orchestrator, generators, refiners, summarizers, most validators | — (step up only for a proven reasoning-bound leaf; step down for pure rule checks) |
| **economy** | Mechanical, rule-driven steps: traceability checks, schema/format validation, label application, deterministic transforms | Judgment calls, open-ended generation |

> Premium tokens cost a multiple of standard tokens. A pipeline pinned wholesale to premium multiplies the whole-run bill while producing identical output on every non-reasoning step — that is why blueprints carry a model row per block instead of one global setting.

## Default rule

Start every block on **standard**. Demote mechanical blocks to **economy**. Promote a block to **premium** only after it passes the gate below.

## The premium gate

A block earns the premium tier only if **all three** checks pass. One "no" drops it a tier.

| # | Check | Fails when |
|---|---|---|
| 1 | **Original reasoning.** The step produces judgments not derivable from upstream decisions. | The step executes or coordinates decisions already made — both stay on standard. |
| 2 | **Cascade risk.** A wrong output propagates into every downstream artifact (a missed scenario, a mis-scored risk). | The output is easy to review and cheap to regenerate. |
| 3 | **Proven shortfall.** A cheaper tier was actually run and measurably underperformed. | The upgrade is pre-emptive. Pre-emptive premium spend is disallowed. |

## Hard cap: one premium block per pipeline

At most **one** premium reasoning block per pipeline. Two or more premium pins — or a premium orchestrator — means a step has been mis-classified: either reasoning leaked into coordination, or an execution step is masquerading as a judgment.

> Deep reasoning belongs in a dedicated leaf subagent with a single responsibility. The orchestrator decomposes, delegates, and synthesizes — coordination work, not deep reasoning — so it stays on standard even when it also frames the task for its leaves. Tier choice is also orthogonal to blast-radius tags: an R3 block behind a human gate gets no tier bump for being dangerous, only for being reasoning-bound.

## Before you upgrade: cheaper levers first

When a standard-tier block underdelivers on a moderately hard step, try in order:

1. **Enable extended/visible thinking** on the standard-tier model. This often closes the quality gap at a fraction of a tier upgrade's cost.
2. **Gather evidence.** Use the blueprint's metrics section, or run a quick A/B sample of cheap-tier vs. premium-tier output on the same inputs.
3. **Upgrade only on evidence.** If the cheaper tier still measurably falls short, promote the block — and confirm it passes all three gate checks.

The same escalation applies downward: if an economy block starts making judgment calls, that is a scoping bug in the block, not a reason to upgrade it.

## Reading blueprint model rows

Each pipeline blueprint's block-customization section carries one model row per block. When porting a blueprint to your platform:

- Map each named model to its tier, then substitute your platform's equivalent in that tier.
- Keep the tier split intact — collapsing all blocks onto one model silently re-introduces the premium-everywhere cost multiplier.
- Record any tier change you make against the blueprint's metrics section so the next builder inherits your evidence.

## Scope

This reference covers tier selection only. It is not a pricing sheet, model catalog, or version-pinning guide. Prompt design and token-budget tuning are the complementary cost lever — see the agent-design token-efficiency guide. Pipeline topology is defined by the blueprints themselves.

## Rule of thumb

Premium reasoning is a scalpel, not a default: one justified reasoning leaf per pipeline at most, everything else on standard or lighter.
