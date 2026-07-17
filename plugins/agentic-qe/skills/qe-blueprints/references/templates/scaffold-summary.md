# Template: Post-Scaffold Summary (Step 5g)

Format the final report after all assistant-config files have been written. This stage is **R0**:
it prints a recap — it creates nothing, installs nothing, and calls no external system.

> Grounding rule: every value in the printed summary must be a concrete fact captured in step 5a
> (real filenames, real install commands, real skill names). If a `{{slot}}` below has no 5a value
> backing it, drop the line — never print a slot literal or an invented default.

## Inputs

| Variable | Where it was set | What it controls here |
|---|---|---|
| `{{tool}}` | 5b routing table | Tree root dir and the layered-context row |
| `{{automation_level}}` | intake (`manual` / `semi` / `full`) | Whether section 5 prints at all |
| `{{trigger_surface}}` | intake | Which integration steps to copy into section 5 |
| `{{scope}}` | intake (`single` / `multi` agent) | Scratch-dir gitignore note; pipeline-split next step |
| connector rows | blueprint section 4, resolved via the shared connectors catalog | Section 3 blocks |
| skill rows | QA starter pack filtered to this blueprint | Section 4 table |

Tool routing (from 5b):

| `{{tool}}` | Tree root | Primary context file | Optional extra layer |
|---|---|---|---|
| Claude Code | `.claude/` | root `CLAUDE.md` | gitignored `CLAUDE.local.md` for personal/secret overrides |
| Cursor | `.cursor/` | `.cursor/CLAUDE.md` + pointer rule | additional path-scoped `.mdc` rules |
| GitHub Copilot | `.github/` | `.github/copilot-instructions.md` (native auto-read path) | path-scoped instruction files |

## Output skeleton

Print the sections below in order. Numbered sections 1–4 always appear; section 5 only when
`{{automation_level}}` is `semi` or `full` — for `manual`, omit it with no placeholder heading.

### 1. Files created

Render the actual tree under `{{tree_root}}`: the primary context file, an `agents/` folder with
one markdown file per role, and a `skills/` stub folder if stubs were generated. For Cursor, also
show `.cursor/rules/project.mdc` — the rule that points the editor at the context file inside
`.cursor/`.

```
{{tree_root}}
├── {{primary_context_file}}
├── agents/
│   ├── {{role_file_1}}.md
│   └── {{role_file_n}}.md
└── skills/            # only if stubs were generated
```

Multi-agent scope only — append this note under the tree:

> `.agent-artifacts/` was added to `.gitignore` but **not created**. Agents create it at runtime:
> `​.agent-artifacts/<run-id>/<role>-output.md`, merged into one final file per run. Do not
> pre-create it.

### 2. Context layering

Print the row matching `{{tool}}` from the routing table above, then suggest two optional layers:

- a machine-level global config file — set up once per machine, not per repo;
- subdirectory context files wherever the rules diverge from the root (test folders, infra folders).

### 3. Connector wiring

One block per system listed in section 4 of the chosen blueprint, resolved through the shared
connectors catalog. Per block:

```
{{system_name}}
  MCP (preferred): {{mcp_server}} — install: {{install_command}}
  CLI fallback:    {{cli_tool}} — auth: {{auth_command}}
  Notes:           {{catalog_auth_and_approval_notes}}
```

If the catalog has no official MCP server for a system, say so explicitly and show the fallback
instead: a REST-based approach or a custom skill.

### 4. Skills to install

| Skill | Source | Why |
|---|---|---|
| skill-scaffolding utility | public Anthropic skills repo → copy into `.claude/skills/` | mandatory — the custom stubs depend on it |
| {{blueprint_skill_1}} | QA starter pack | {{link_to_blueprint_workflow}} |

Inclusion test: a starter-pack skill earns a row only if it maps directly onto this blueprint's
workflow. Generic skills stay out. The scaffolding utility is the one entry that always appears.

### 5. Automation setup — `semi` / `full` only

Pull all content from the sibling automation reference; select the integration matching
`{{trigger_surface}}`. Print:

- trigger surface and trigger event;
- the integration-specific setup steps;
- an agent-API HTTP request skeleton (method, URL, headers, body) for the chosen AI platform.

If `{{trigger_surface}}` has no documented integration, print the generic core pattern instead —
an HTTP POST to the agent API — adapted from the nearest documented example, and say that is what
you did.

Embed this pre-deployment checklist verbatim in the block:

- [ ] Validate the flow manually before any event is allowed to trigger it
- [ ] All tokens live in a secret manager — none in config files
- [ ] Bot accounts are filtered out of trigger conditions (prevents trigger loops)
- [ ] Trigger payload carries rich context: issue key, PR id
- [ ] AI-generated output is labeled as such
- [ ] Human review stays in the loop until output quality is proven

## Next steps (ordered)

Print after the numbered sections. Base list, always:

1. Write real prompts into each agent file's instructions block.
2. Wire the connectors from section 3 and confirm credentials work.
3. Install one skill from section 4 and smoke-test it.
4. Enrich `{{primary_context_file}}` with your domain rules.
5. Run the blueprint's 30-minute trial before building the full pipeline.

Conditional additions:

| Condition | Extra step |
|---|---|
| `{{automation_level}}` = `semi` or `full` | Validate manually before enabling event firing — repeat of the checklist gate, on purpose |
| `{{scope}}` = `single` | Later, split the working orchestrator into the multi-role pipeline using the blueprint's block-customization section |

## Pitfalls

Close the summary with these advisory cautions (output for the user, not enforced controls):

- Avoid broad, unguarded tool grants; scope each role to what it needs.
- Treat connector-sourced content — tickets, PR text, email — as untrusted input, even after it
  has passed through an artifact handoff.
- Pass sub-agent results by file reference, not by pasting them into chat context.
- Guard approval and plan state against context compaction; re-confirm rather than assume.
- Never enable event triggers before the manual validation pass.

## Boundaries

- This template formats a report about files that already exist; it performs no scaffolding.
- The routing table, connector catalog entries, and automation integrations are defined in the
  sibling scaffold and automation references — this doc only consumes them.
- The runtime scratch directory is never created here, and nothing is installed here.
- Related reading it points the user to: the blueprint's quick-trial section and its per-role
  customization blocks.
