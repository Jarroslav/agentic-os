# Parallelism Safety

agentic-sdlc uses parallel work only when tasks have clear ownership and can be
verified independently.

## Safe Parallelism

Parallel execution is acceptable when:

- tasks write to disjoint files or modules
- each task has an explicit owner and artifact output
- shared contracts are already defined in `plan.md`
- verification can identify which task caused a failure

Examples:

- independent implementation tasks from `superpowers:subagent-driven-development`
- monorepo guide generation by `knowledge-foundation`, one module per subagent
- separate read-only exploration questions

## Unsafe Parallelism

Do not parallelize when:

- two tasks edit the same file or generated artifact
- one task needs another task's output before it can start
- shared schema/API contracts are still undecided
- the work involves one global migration or repository-wide rewrite

## Worker Instructions

Every implementation worker must be told:

- it is not alone in the codebase
- it owns specific files or responsibilities
- it must not revert unrelated edits
- it must adapt to changes made by other workers
- it must return changed file paths and verification evidence

## Integration Rule

The parent orchestrator integrates results, reruns validation, and resolves
conflicts. Subagents do not merge, reset, or discard each other's changes.
