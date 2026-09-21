# Runtime authority for workflow skills

When a workflow has a managed run in `.agentic/state/runtime.sqlite3`, that
database is authoritative for lifecycle state, assignments, decisions, peer
messages, evidence, budgets, and external actions.

Skills must use the versioned `runtime/run.py` operations for mutations:

- `decision.record` for gate decisions;
- `evidence.record` or `evidence.ingest` for verification receipts;
- `event.record` for coordinator-owned workflow phase events;
- `assignment.*`, `message.*`, and `dispatch.*` for delegated work;
- `run.transition`, `run.resume`, `run.cancel`, and `run.complete` for lifecycle;
- `legacy.export` to refresh `meta.json`, `events.jsonl`, and `decisions.jsonl` compatibility views.

Those JSON and JSONL files are outputs for older readers. Editing or appending
them never advances a managed run. If the required runtime operation is absent,
the workflow must block and report the missing capability. Human-authored
specifications, plans, QA documents, and review reports remain ordinary files
under their documented locations.
