# Complexity Scorer

Dispatches the `complexity-assessor` agent against a task description and returns a normalized score and routing decision — either go straight to planning or run brainstorming first.

## Use It For

- Scoring task complexity before the SDLC pipeline decides which phases to run.
- Determining whether a task is simple enough to skip the brainstorming phase.
- Flagging tasks that are too large and need to be split before planning.

## How To Ask

This skill is invoked automatically by `sdlc-pipeline` at Phase 3. It is not normally called directly.

If needed, it can be triggered explicitly:

- "Score the complexity of this task: add OAuth2 callback handling."

## What It Needs

- `task_description` — the full requirements text.
- `feature_area` — a short keyword summary of the feature area.
- `repo_path` — absolute path to the current checkout.
