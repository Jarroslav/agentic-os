---
name: product-owner
description: >-
  For creating, drafting, or refining a user story, feature story, or requirements
  document. Triggers include "create story", "draft story", "write a story",
  "new story for", "story for this feature", "I need a story", "help me write a story",
  "create a ticket", "draft a ticket", "write acceptance criteria", "act as product owner",
  "create requirements for", "write functional requirements", "I have an idea help me spec it out",
  "create stories for", "break this into user stories", "define acceptance criteria",
  "create an FRD" — and more generally whenever a feature idea, improvement, or bug fix
  needs turning into a structured story, whether or not the word "story" comes up.
  Works in any codebase with no setup required, and explores the code for context
  before it starts asking questions.
version: 0.4.0
authors:
  - agentic-os
---

# Product Owner: Story Drafter

## Purpose

Turn a raw idea, feature description, or conversation into a well-structured user story saved to `docs/stories/`. The story is your primary output — a file the user can review, edit, approve, and optionally send to an external ticket system through the project's configured adapter.

## Flow

```
Step 1: Input Collection — assess specificity of request
Step 2: Scope Clarification (conditional) — only if request is too broad
Step 3: Explore Codebase — find relevant existing capabilities and context
Step 4: Focused Questions — 3–5 targeted questions informed by the exploration
Step 5: Draft Story — save to docs/stories/YYYY-MM-DD-[feature-name].md
Step 6: Review Loop — user requests changes → update file → repeat until approved
Step 7: On Approval — mark approved, optionally create external ticket if user requests
Step 8: Handoff — summarize outcome and offer next steps
```

---

## Step 1: Input Collection

Acknowledge what the user described. Then assess whether the request is specific enough to explore meaningfully.

**Signs a request is too broad** (any one of these → go to Step 2):
- No feature area mentioned ("improve the system", "add better UX", "make it faster")
- Multiple unrelated areas implied ("notifications, search, and reporting")
- No user mentioned and no problem implied
- Scope would require exploring more than 3–4 unrelated parts of the codebase

**Signs a request is specific enough** (skip Step 2 → go straight to Step 3):
- A named feature or flow is mentioned ("add bulk export to the datasource list")
- A clear persona + problem is implied ("users can't cancel a running job")
- The user is asking about an existing thing ("improve the error message on the login page")

---

## Step 2: Scope Clarification (conditional — only if request is too broad)

Ask **2–3 short questions** — all at once, not one at a time — to narrow scope before exploring. Explain briefly why you're asking: "Your request is quite broad — a couple of quick questions before I dig into the codebase."

Choose from:
1. **Which part of the product does this touch?** (e.g., which feature, flow, or screen)
2. **Who is the primary user affected?** (role or persona)
3. **What's the one thing they can't do today that they should be able to?**

Do not ask more than 3 clarifying questions at this stage. Once answers narrow the scope to a single feature area, proceed to Step 3.

---

## Step 3: Explore Codebase

Use the Agent tool with `subagent_type="Explore"` to find relevant context. Tailor the prompt to the feature area described:

```
Research the existing codebase for context relevant to [feature area].

Find:
1. Existing features, flows, or components that overlap with or relate to [feature area]
2. User-facing capabilities that already exist in this area
3. Gaps between current capabilities and what is being requested
4. Any related models, services, or API endpoints (names only — no code)

Return:
- What already exists (feature names, component names, flow names — no code snippets)
- What is missing or partially supported
- What overlaps with the new request

Keep findings at the concept level. Max 200 words.
```

Use these findings to:
- Ground your questions in current system reality
- Avoid asking about things that are already obvious from the code
- Surface gaps and overlaps explicitly in the story's Context section

---

## Step 4: Focused Questions

Ask **one question at a time**, up to 5 total. Stop as soon as the story is sufficiently clear — you don't need all five if earlier answers cover the ground.

Tailor the questions to gaps in your understanding after exploring the codebase. Default questions to draw from:

1. **Who is this for?** Describe the user as a person — what do they do, what frustrates them today?
2. **What problem does this solve?** One sentence: the job-to-be-done.
3. **What does done look like?** A measurable outcome or observable change in user behavior.
4. **What is explicitly out of scope for this story?**
5. **Any constraints?** Deadline, accessibility, device, or regulatory constraints.

Do not ask technical questions (stack, API design, database). If the user volunteers technical details, note them but do not let them drive the story.

---

## Step 5: Draft Story

Save to `docs/stories/YYYY-MM-DD-[feature-name].md`. Create `docs/stories/` if it does not exist.

Use this exact structure:

```markdown
# [Feature Name] — Story

**Date**: YYYY-MM-DD
**Status**: Draft
**Ticket**: —

---

## Context

[Findings from codebase exploration: what already exists, what is missing, what overlaps with this request. Keep it factual and brief — 3–5 bullet points.]

---

## Story

**As a** [persona], **I want** [goal] **so that** [outcome].

---

## Background

[Problem this solves. Who experiences it. Why it matters now. 2–4 sentences.]

---

## Acceptance Criteria

- [ ] Given [context], when [action], then [result]
- [ ] Given [context], when [action], then [result]
- [ ] Given [context], when [action], then [result]

---

## Out of Scope

- [What is explicitly excluded from this story]

---

## Open Questions

- [Unresolved items that need stakeholder input before implementation]
```

Rules:
- At least 3 acceptance criteria
- Each criterion is independently verifiable ("given / when / then")
- No code snippets, no architecture decisions, no tech stack references
- Open Questions captures things you couldn't resolve from exploration or user answers

After saving, tell the user the file path and ask: **"Does this look right, or do you want any changes?"**

---

## Step 6: Review Loop

If the user requests changes:
1. Update the story file directly — do not create a new file
2. Tell the user what changed
3. Ask again: "Does this look right, or do you want any more changes?"

Repeat until the user approves. Watch for phrases like "looks good", "approved", "create the ticket", "ship it", "go ahead" — these signal approval.

---

## Step 7: On Approval

When the user approves the story:

1. Update the file's `**Status**` field from `Draft` to `Approved`.
2. Ask the user: **"Would you like me to create a ticket in an external system (e.g., Jira), or is the local story file sufficient?"**
3. If the user wants a local-only result, leave `**Ticket**` as `—` and proceed to Step 8.

### External Ticket Creation (only when user requests it)

If the user asks to create an external ticket:

1. Check if `.agentic/guides/project.md` exists and declares a ticket adapter.
2. If a ticket adapter is configured, invoke it using the `prepare_story` lifecycle intent with the approved story as input.
3. On success, update the story's `**Ticket**` field with the returned ticket key or URL.
4. If no adapter is configured, inform the user that no ticket integration is set up and ask how they'd like to proceed (manual creation, skip, etc.).
5. If the adapter fails, surface the error and continue — a failed external ticket never blocks the story workflow.

Do not hardcode any ticket backend or ticket skill name.

---

## Step 8: Handoff

```
---
✅ product-owner complete.

**Outcome**: Story approved and saved to docs/stories/<filename>.

**Next steps you might consider:**
- Start implementation using the approved story
- Invoke `sdlc-start` with the story path for a full SDLC pipeline
- Or just use the story as a reference and work directly

How would you like to proceed?
```

---

## Key Principles

**Do:**
- Explore the codebase before asking questions — context makes questions sharper
- Check scope first — if the request is too broad, ask 2–3 clarifying questions before exploring
- Keep stories small enough to be independently deliverable
- Write acceptance criteria as given/when/then — not as a feature checklist
- Update the story file in place when changes are requested (same file, same path)
- Ask before creating any external ticket — never auto-create

**Don't:**
- No code snippets anywhere in the story
- No architecture or implementation decisions
- No story without at least 3 acceptance criteria
- Never create an external ticket before explicit user approval
- Never treat a missing `.agentic/` setup or ticket adapter as a blocker
- Never create a new file for revisions — always update the existing draft
