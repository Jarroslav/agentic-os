# Shared runtime contracts

`agentic_runtime/registry.json` is the canonical contract source. Run
`python3 runtime/generate_bundles.py` after a source change; CI uses `--check`
to reject drift. Each plugin receives its own runtime and generated contract
reference, so it can be installed without its sibling.

Python 3.10 or newer is required. The runtime uses only the standard library.
Requests and responses are versioned JSON on standard input/output. Invalid
requests fail with exit status 2 and a structured error. Registry inspection:

```sh
printf '%s\n' '{"api_version":"1.0.0","operation":"registry.get"}' | python3 runtime/run.py
```

This stage validates definitions, inputs and policy. Durable run mutations,
host enforcement and installation operations are subsequent implementation
stages. An absent operation is an error; it must never fall back to editing
JSON state. Registry validation alone does not enforce worker permissions or
provide an operating-system sandbox.

Scored evaluation definitions remain frozen independently under
`tests/reliability/`. Passing contract tests earns no live evaluation points.

Supported operations use the same `api_version` envelope:

| Operation | Required fields beyond operation/version | Optional fields |
|---|---|---|
| `registry.get` | none | none |
| `contract.lookup` | `section`, `identifier` | none |
| `policy.resolve` | `entrypoint` | `overrides` |
| `input.normalize` | `payload` | `legacy` (boolean, default false) |
| `transition.validate` | `source`, `target` | none |
| `retry.allowed` | `loop_id`, `attempts_used` | none |

`attempts_used` includes the initial attempt. A false retry result prohibits another
attempt; it does not change the outcome of the previous attempt. Policy overrides
can reduce default budgets. Increasing a running budget requires a future recorded
user-decision operation; changing configuration must not silently reset counters.
