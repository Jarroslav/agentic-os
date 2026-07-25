# eval-harness

Scaffold a two-layer evaluation framework for the Claude skills (and agents) in your repo — a free deterministic contract layer plus a model-graded judge layer — driven by one `evals.json` spec per skill.

## Use It For

Bootstrapping regression protection for a skill/agent repository without hand-writing a runner, provider integration, or env plumbing. The skill interviews you (only for what it cannot infer), reads every skill in the target repo, copies in a TypeScript or Python harness, writes one spec per skill, and runs the contract layer to green.

| Layer | Checks | Model calls | Cost | Cadence |
| --- | --- | --- | --- | --- |
| Contract | Structure: required files exist, load-bearing text still present, scripts byte-compile / smoke-run | None | Free, fast | Every commit + CI |
| Judge | Behavior: run a case prompt through the skill, LLM grades output against per-case assertions | Yes | Paid | On demand / optional CI |

Each spec lives at `<skill>/evals/evals.json` and holds both a `contracts` object and an `evals` array; contracts-only specs are valid. Behavioral cases run N times against a pass-rate threshold rather than pass/fail on a single run.

> The specs are where the value compounds — runners rarely change once installed. Extend the specs, not the harness.

Not for: a standalone unit test unrelated to skills/agents, or running an eval suite that already exists. It never puts the judge layer on a required CI or hook path — only the credential-free contract layer gates merges.

## How To Ask

Say things like:

- "Set up evals for the skills in this repo"
- "I want regression tests for my agents — scaffold an eval harness"
- "Add benchmark tooling for my skills, Python harness"
- "Which judge provider should I use for skill evals?"

You will be asked to pick (or confirm inferred defaults for): judge provider, model tier, harness language (TypeScript, Python, or both), spec layout, and whether to wire hooks/CI. Answer with your provider choice from:

| Provider | Reaches |
| --- | --- |
| `anthropic-native` | Anthropic messages endpoint directly, via SDK + API key |
| `anthropic-portkey` | Anthropic models behind a Portkey gateway, `@<provider>/<model>` ids |
| `openai-compatible` | Any endpoint speaking the OpenAI chat-completions protocol (OpenAI, vLLM, Ollama, LM Studio, ...) |

The skill scaffolds only what it has read: every contract and judge assertion traces to an actual skill file it inspected, with 2–4 behavioral cases per skill.

## What It Needs

- A target repo containing at least one skill definition file.
- A harness-language decision (TypeScript, Python, or both).
- A judge-provider decision from the table above.
- No credentials at setup time. Judge runs need API/gateway credentials at execution time, loaded from a git-ignored `.env`; a committed `.env.example` carries placeholders only. If credentials are absent, the skill hands you the exact run command and required env vars instead of failing.

> Never commit real secrets. If a plaintext credential has been shared, rotate it.
