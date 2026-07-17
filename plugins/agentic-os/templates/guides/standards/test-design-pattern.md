# Test Design Pattern (Binding)

<!-- Scaffolded by agentic-os to .agentic/guides/standards/test-design-pattern.md.
     Single source of truth for HOW automated tests are designed in this repo.
     Agent contracts and skills reference this file; they must not restate or fork it. -->

## 1. Canonical test layout

Every test follows one shape:

1. **Arrange via API** (or the fastest programmatic seam) in setup hooks.
   Create what you assert on; never depend on data another suite happens to
   leave behind. Test CRUD against the mutable test environment is expected
   practice — see the env write boundaries in `../policy/ai-policy.md`.
2. **Verify the precondition is observable** before acting (see §4).
3. **Act** — one user-visible flow (UI) or one endpoint contract (API).
4. **Assert ONE deterministic state, unconditionally.** If you don't know
   whether a control should be hidden or disabled — STOP and pin the UI
   contract first (§6).
5. **Clean up idempotently** in teardown hooks: every created entity is
   registered for deletion; shared-state mutations are restored with verified
   helpers, never fire-and-forget.

## 2. Layer selection

| Concern | Layer |
| --- | --- |
| Authorization / permission matrices (role × scope × endpoint) | API status-code tests |
| "The UI reflects the backend permission" | ONE thin UI smoke per area |
| User-visible lifecycle (create → activate → retire) | UI journey, ≤ ~5 logical steps; split bigger flows |
| Unit logic | NOT here — it belongs in the owning codebase's unit suite |

Don't add a UI test for something an API status code proves. E2E value comes
from testing the integrated system — avoid mocking the system under test.

## 3. The conditionals law

- **Conditional assertions in test bodies are banned** (enforce with lint
  where possible): `if (visible) expect(...)` can pass without asserting
  anything.
- **Conditional control flow inside recovery helpers is allowed** — a retry
  loop may probe state to decide the next recovery step — **but the helper
  must end with an unconditional postcondition assertion** so exhausted
  retries fail loudly. Replacing the probe with a hard assertion inside the
  loop kills the retry semantics; removing the final assertion hides failure.
- Navigation/`goto` helpers assert only that the page **loaded** — never that
  a permission-gated element is in a specific interactive state. Permission
  assertions belong in test bodies.

## 4. Waiting & propagation law

- **Never** fixed sleeps; **never** network-idle as a readiness signal
  (long-polling apps make it a lie). Wait on the element or state you
  actually need.
- **Data-readiness gates**: a button being enabled does not mean the page's
  data is loaded. Gate on an element rendered FROM the data.
- **Assign-and-verify, never assign-and-hope**: setup helpers that mutate
  state must verify persistence before returning. Persistence still does not
  guarantee propagation — callers asserting permission *effects* must probe
  the affected surface (poll a status code or a state-derived element).
- Know your framework's non-waiting probes (e.g. an "is visible?" check that
  returns immediately regardless of a timeout argument) and use the true
  waiting primitive when you mean "wait".

## 5. Data law

- Generated-unique data (faker/random suffix) for everything a test creates;
  never reuse another suite's entities.
- Typed constants/enums only — no raw string literals for roles, timeouts,
  environments, or shared fixtures.
- Self-provision static fixtures: if a test depends on a named entity, the
  suite's setup checks-and-creates it (test databases get reset).
- Tests that mutate state shared across parallel workers are marked with the
  repo's serial/no-parallel mechanism and documented as such.

## 6. UI-contract pinning

Before writing or changing a UI assertion about presence/disabled state:

1. Inspect the live DOM and/or the frontend source to pin the actual contract
   (hidden vs disabled vs absent; which attribute is the stable selector).
2. Record it in the repo's UI-contract notes (e.g. `docs/ui-contracts/`)
   with the date and evidence.
3. Assert the pinned single state; guard zero-count assertions with a
   permission-independent sibling element so they cannot pass vacuously.

## 7. Self-healing definition

Self-healing = **bounded converge-and-verify**, never failure-hiding:

- bounded retry loops with logged attempts and a final unconditional assert;
- propagation polls with explicit timeout messages;
- named, documented catch helpers only — inline empty catches are banned.
  A helper hides *retries*, not *failures*.

## 8. Never introduce

Skipped, focused, or commented-out tests (`skip`/`only`/`fixme` and
equivalents). The only permitted exception is a runtime-conditional guard on a
fact the test cannot control (project/environment routing), carrying an inline
lint-suppression directive and a one-line reason.

Red or flaky tests are handled by `flaky-protocol.md` — a test is never
weakened, deleted, or quarantined outside that protocol.
