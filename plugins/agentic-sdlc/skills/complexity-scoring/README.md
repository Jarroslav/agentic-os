# Complexity Scoring

Routes each incoming task through the cheapest safe path: dispatch a sizing read, then send the work to planning or to a brainstorming pass first.

## Use It For

Deciding, at the pipeline's Phase 3 gate, whether a task is ready for planning as-is or needs a brainstorming pass beforehand. The skill carries no scoring logic of its own — it dispatches the `sizing-analyst` agent against the task and normalizes whatever that agent returns into a single score-plus-routing verdict that `sdlc-pipeline` acts on.

You will rarely need to call this directly. `sdlc-pipeline` dispatches it automatically as a fixed part of its Phase 3 flow, ahead of any planning or brainstorming work.

## How To Ask

Manual invocation is the exception path — reach for it when you want a complexity read outside the pipeline's normal flow, or want to double-check a routing call before committing to a plan. Describe the task and name the area it touches:

> "Score the complexity of adding OAuth2 callback handling to the auth service."

## What It Needs

| Input | Supply this |
|---|---|
| `task_description` | The full requirement text — completeness drives score quality. |
| `feature_area` | A short keyword summary naming the affected area. |
| `repo_path` | Absolute path to the repository checkout being scored against. |

> Skip one of these and the dispatch to `sizing-analyst` has nothing solid to reason over — supply all three even for a one-off manual check.
