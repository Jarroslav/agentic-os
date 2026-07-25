# Model-Tier Routing

agentic-sdlc never ships a concrete model ID — everything runs on `inherit`
(the session's model) unless the **host project** opts in. This reference
defines the tier abstraction, which pipeline roles default to which tier, and
how a tier resolves to an actual model. It bounds the ModelPrice factor of the
cost model (`references/tokenomics.md`) without ever hardcoding a vendor.

## The three tiers

| Tier | Meant for | Examples of work |
|---|---|---|
| `economy` | Mechanical, format-bound, low-judgment | requirements mirror sync, artifact summarization for ArtifactRefs, `qa-planner --update` health refresh, work-item history rows, MR description drafting |
| `standard` | Judgment within a bounded contract | `sizing-analyst`, `codebase-scout`, `story-proxy`, `lead-proxy`, `code-review-orchestrator` (and its review lenses), qa-planner checklist/review modes |
| `premium` | Escalated judgment on flagged risk | any `standard` role when the gate context carries a risk flag in `escalate_on` (e.g. `security`, `breaking-change`) or `complexity.json.score >= 25` |

## Resolution rule

When dispatching a subagent or stand-in:

1. Determine the role's tier from the table above (escalation can promote
   `standard` → `premium` for that one dispatch; nothing ever demotes).
2. Read `config.model_tiers.<tier>` from `.agentic/agentic-sdlc/config.json`.
3. Use that value as the dispatch model. The shipped default for every tier is
   `"inherit"` — meaning today's behavior is preserved verbatim until the host
   project maps tiers to real models it has access to.

The mapping lives in host config and only there. Model IDs are user-supplied
values; the plugin repository itself must never contain one (its CI enforces
exactly that).

```json
"model_tiers": {
  "economy": "inherit",
  "standard": "inherit",
  "premium": "inherit"
}
```

A host that maps only `economy` and leaves the rest `inherit` still gets most
of the win — the mechanical roles are the volume.

## Usage sampling (spec only)

Hosts that can see token usage MAY append `usage.sampled` semantic events to
the run ledger so future reporting (the V2 `report-builder` roadmap item) has
cost data to consume. Shape:

```json
{
  "schema": 1, "ts": "<ISO>", "event": "usage.sampled",
  "run_id": "<id>", "phase": 7, "actor": "<dispatching skill>",
  "summary": "usage sample for <role>",
  "artifacts": [],
  "data": {"role": "<subagent-or-skill>", "tier": "economy|standard|premium",
            "input_tokens": 0, "output_tokens": 0}
}
```

The plugin ships no collector, no pricing table, and no dashboard — pricing is
vendor-specific and stale on arrival. An optional host-supplied
`config.pricing` map is reserved for `report-builder` to consume later.

## Review rubric hook

A change that adds a subagent dispatch must name its tier here. A change that
proposes pinning a model ID in the plugin is rejected by construction — the
tier map is the only sanctioned mechanism.
