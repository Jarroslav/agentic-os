# product-owner

Turn a rough feature idea into a structured user story with given/when/then acceptance criteria, saved locally and ready to hand off.

## Use It For

- Drafting a user story from a half-formed idea, a problem statement, or just a feature name.
- Writing acceptance criteria in given/when/then form for a flow or behavior.
- Producing a feature requirement document (FRD) from an unstructured ask.
- Decomposing an idea into a story that is deliverable and independently testable before any code is written.

## How To Ask

- "Draft a story for `<feature>`."
- "Write acceptance criteria for this checkout flow."
- "Create an FRD for `<feature>`."
- "Spec out my idea: `<one-line description>`."

> No need to say "story" — describe the feature or fix and it gets shaped into one.

## What It Needs

- One of: a feature idea, a problem description, or a feature name. That is the floor.
- `.agentic/guides/project.md` for project settings. Required for settings; the ticket-adapter section inside it is optional.

Stories land under `docs/stories/`. Pushing to a ticket tracker is opt-in and adapter-driven through the guide file — no backend is hardcoded, and local save works with no tracker configured.
